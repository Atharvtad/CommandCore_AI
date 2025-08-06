# AI Calling Agent

This project is an AI-powered calling agent built using Flask, Whisper ASR, and LM Studio's Mistral-7B model. The agent assists users in reporting scams through natural conversation, collecting essential details, and saving the conversation to a file.

## Features

- Real-time audio recording and transcription using Whisper ASR.
- Conversational AI using Mistral-7B for collecting scam details.
- Text-to-speech feedback for a seamless user experience.
- Conversation logging and saving to a text file.
- Flask-based API endpoints for audio handling and conversation flow.

## Prerequisites

- Python 3.8+
- Flask
- Transformers
- Sounddevice
- Wavio
- Pyttsx3
- Requests
- NumPy

## Installation

1. Clone the repository:

```bash
git clone https://github.com/your-repo/ai-calling-agent.git
cd ai-calling-agent
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run LM Studio and make sure the Mistral-7B model is available at `http://localhost:1234/v1/chat/completions`.

## Usage

1. Start the Flask server:

```bash
python app.py
```

2. Access the web interface at `http://localhost:5000`.

3. Start and stop audio recording via API:

- Start Listening: `POST /api/start_listening`
- Stop Listening: `POST /api/stop_listening`

4. The agent will collect scam-related details and save the conversation as a text file when the conversation ends.

## API Endpoints

### `POST /api/start_listening`
Starts the audio recording.

### `POST /api/stop_listening`
Stops the recording, transcribes the audio, and responds to the user.

## Conversation Flow

The agent will follow this flow:

1. Greet the user and ask about the scam.
2. Collect details like name, age, address, bank details, and transaction info.
3. Continue until the user confirms no more details.
4. Save the conversation and end the session.

## File Structure

```
.
├── app.py
├── templates/
│   └── index.html
├── static/
│   └── styles.css
    └── script.js  
├── requirements.txt
└── README.md
```

## Logging and Error Handling
- Logs are saved for debugging purposes.
- Errors during audio recording and AI response are handled gracefully.

## Future Enhancements
- Multi-language support
- Enhanced security for sensitive data
- Deployment on cloud platforms


