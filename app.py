from flask import Flask, request, jsonify, render_template
import sounddevice as sd
import wavio
from transformers import pipeline
import threading
import queue
import os
import pyttsx3
import logging
import requests
import numpy as np
import time
from datetime import datetime
# import os

# Set the ffmpeg path manually (update this path to where your ffmpeg.exe or binary is)
os.environ["PATH"] += os.pathsep + r"D:\ffmpeg-master-latest-win64-gpl-shared\bin"

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Whisper pipeline
try:
    whisper_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-base.en", device=0)
    logger.info("Whisper pipeline loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Whisper pipeline: {str(e)}")
    raise

# LM Studio API
LM_STUDIO_API = "http://localhost:1234/v1/chat/completions"

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
audio_queue = queue.Queue()
is_recording = False
audio_file = "audio.wav"
recording_thread = None

# Conversation state
conversation = {
    "chat_log": [{"role": "user", "content": """You are a calling agent assisting a user in reporting a scam. Your task is to:
1. Greet the user and ask what kind of scam they encountered.
2. Collect the following details through natural conversation:
   - Full name
   - Age
   - Gender
   - Full address
   - Pincode
   - Nearest police station
   - Aadhar card or PAN card number
   - Email address
   - Bank name involved in the scam
   - Transaction details (for each transaction: transaction ID, time, date)
3. Ask about additional transactions until the user says 'no more', 'that’s all', or 'done'.
4. Once all details are collected and no more transactions are reported, say 'Thank you, I have all the details. Goodbye.' to end the conversation.
5. Be patient, polite, and ask one question at a time. If the user’s response is unclear, ask for clarification.
6. Do not repeat the entire list of questions in each response; focus on the next piece of information needed."""}],
    "ended": False
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start_listening', methods=['POST'])
def start_listening():
    global is_recording, recording_thread
    if is_recording:
        logger.warning("Already listening")
        return jsonify({'error': 'Already listening'}), 400
    
    while not audio_queue.empty():
        audio_queue.get()
    
    is_recording = True
    logger.info("Starting audio recording")
    recording_thread = threading.Thread(target=record_audio, daemon=True)
    recording_thread.start()
    return jsonify({'status': 'Listening started'})

@app.route('/api/stop_listening', methods=['POST'])
def stop_listening():
    global is_recording, recording_thread, conversation
    if not is_recording:
        logger.warning("Not listening")
        return jsonify({'error': 'Not listening'}), 400
    
    is_recording = False
    if recording_thread:
        recording_thread.join(timeout=2)
        recording_thread = None
    
    try:
        logger.info("Processing audio")
        audio_chunks = []
        timeout = 2
        start_time = time.time()
        while time.time() - start_time < timeout or not audio_queue.empty():
            try:
                audio_chunks.append(audio_queue.get(timeout=timeout))
            except queue.Empty:
                break
        
        if not audio_chunks:
            logger.warning("No audio recorded")
            response = "I didn’t hear anything. Please try again."
            synthesize_speech(response)
            return jsonify({'transcript': '', 'response': response})
        
        audio_data = b''.join(audio_chunks)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        logger.info(f"Audio array length: {len(audio_array)} samples")
        
        wavio.write(audio_file, audio_array, SAMPLE_RATE, sampwidth=2)
        file_size = os.path.getsize(audio_file)
        logger.info(f"Audio file saved: {audio_file}, size: {file_size} bytes")
        
        # if file_size < 1000:
        #     os.remove(audio_file)
        #     response = "Your audio was too short. Please speak for at least 2 seconds."
        #     synthesize_speech(response)
        #     return jsonify({'transcript': '', 'response': response})
        
        logger.info("Transcribing with Whisper")
        result = whisper_pipeline(audio_file)
        transcript = result["text"].strip().lower()
        logger.info(f"Transcription: '{transcript}'")
        os.remove(audio_file)
        
        if transcript:
            conversation["chat_log"].append({"role": "user", "content": transcript})
            logger.info(f"Updated chat log: {conversation['chat_log']}")
            response = get_ai_response(conversation["chat_log"])
            conversation["chat_log"].append({"role": "assistant", "content": response})
            synthesize_speech(response)
            
            if "goodbye" in response.lower():
                conversation["ended"] = True
                save_conversation()  # Save the conversation to a .txt file
                reset_conversation()
            
            return jsonify({'transcript': transcript, 'response': response})
        else:
            response = "I couldn’t understand you. Please try again."
            synthesize_speech(response)
            return jsonify({'transcript': '', 'response': response})
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        if os.path.exists(audio_file):
            os.remove(audio_file)
        response = "An error occurred. Please try again."
        synthesize_speech(response)
        return jsonify({'error': str(e)}), 500

def record_audio():
    global is_recording
    try:
        logger.info("Recording thread started")
        with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16') as stream:
            logger.info(f"Recording with device: {sd.default.device}")
            while is_recording:
                data, overflowed = stream.read(1024)
                if overflowed:
                    logger.warning("Audio buffer overflow")
                audio_queue.put(bytes(data))
        logger.info("Recording stopped")
    except Exception as e:
        logger.error(f"Recording error: {str(e)}")
        is_recording = False

def format_prompt(chat_history):
    prompt = ""
    for message in chat_history:
        if message["role"] == "user":
            prompt += f"[INST] {message['content']} [/INST]\n"
        elif message["role"] == "assistant":
            prompt += f"{message['content']}\n"
    return prompt.strip()

def get_ai_response(chat_history):
    # prompt = format_prompt(chat_history)
    logger.info(f"AI prompt: {chat_history}")
    try:
        payload = {
            "model": "mistral-7b",
            "messages": chat_history,
            "temperature": 0.7,
            "max_tokens": 500,
            "stream": False
        }
        response = requests.post(LM_STUDIO_API, json=payload, headers={'Content-Type': 'application/json'}, timeout=200)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"AI response error: {str(e)}")
        return "I couldn’t process that. Please try again."

def synthesize_speech(text):
    try:
        tts_engine = pyttsx3.init('sapi5', debug=True)
        tts_engine.setProperty('rate', 130)
        tts_engine.setProperty('volume', 0.85)
        voices = tts_engine.getProperty('voices')
        selected_voice = None
        for voice in voices:
            logger.info(f"Voice available: {voice.name}, ID: {voice.id}")
            if "zira" in voice.name.lower():
                selected_voice = voice.id
                break
            elif "female" in voice.name.lower():
                selected_voice = voice.id
        if not selected_voice:
            selected_voice = voices[0].id
        tts_engine.setProperty('voice', selected_voice)
        text_with_prosody = text.replace(". ", ". , ").replace("? ", "? , ").replace("thank you", "*Thank you*")
        logger.info(f"Speaking: '{text_with_prosody}' with voice: {selected_voice}")
        tts_engine.say(text_with_prosody)
        tts_engine.runAndWait()
        logger.info("Speech completed")
        tts_engine.stop()
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")

def save_conversation():
    global conversation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scam_report_{timestamp}.txt"
    with open(filename, 'w') as f:
        f.write("Scam Report Conversation\n")
        f.write("=======================\n")
        for entry in conversation["chat_log"]:
            if entry["role"] != "system":  # Skip system prompt
                role = "User" if entry["role"] == "user" else "Agent"
                content = entry["content"]
                f.write(f"{role}: {content}\n")
    logger.info(f"Conversation saved to {filename}")

def reset_conversation():
    global conversation
    conversation = {
        "chat_log": [{"role": "system", "content": """You are a calling agent assisting a user in reporting a scam. Your task is to:
1. Greet the user and ask what kind of scam they encountered.
2. Collect the following details through natural conversation:
   - Full name
   - Age
   - Gender
   - Full address
   - Pincode
   - Nearest police station
   - Aadhar card or PAN card number
   - Email address
   - Bank name involved in the scam
   - Transaction details (for each transaction: transaction ID, time, date)
3. Ask about additional transactions until the user says 'no more', 'that’s all', or 'done'.
4. Once all details are collected and no more transactions are reported, say 'Thank you, I have all the details. Goodbye.' to end the conversation.
5. Be patient, polite, and ask one question at a time. If the user’s response is unclear, ask for clarification.
6. Do not repeat the entire list of questions in each response; focus on the next piece of information needed."""}],
        "ended": False
    }

if __name__ == '__main__':
    logger.info("Available audio devices:")
    for device in sd.query_devices():
        logger.info(device)
    synthesize_speech("Hello! I’m your scam reporting assistant. Let’s begin.")
    app.run(debug=True, host='0.0.0.0', port=5000)