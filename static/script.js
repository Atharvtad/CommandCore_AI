const messagesDiv = document.getElementById('messages');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const clearBtn = document.getElementById('clearBtn');
const statusDiv = document.getElementById('status');

function addMessage(sender, text) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);
    messageDiv.textContent = text;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function updateStatus(text) {
    statusDiv.textContent = text;
}

async function startListening() {
    try {
        updateStatus("Starting...");
        const response = await fetch('/api/start_listening', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
        const data = await response.json();
        if (response.ok) {
            addMessage('ai', 'Listening...');
            updateStatus("Recording");
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            addMessage('ai', data.error || 'Failed to start');
            updateStatus("Error");
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    } catch (error) {
        console.error('Start error:', error);
        addMessage('ai', 'Error: ' + error.message);
        updateStatus("Error");
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

async function stopListening() {
    try {
        updateStatus("Processing...");
        const response = await fetch('/api/stop_listening', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
        const data = await response.json();
        if (response.ok) {
            if (data.transcript) {
                addMessage('user', data.transcript);
                addMessage('ai', data.response);
                updateStatus("Ready");
            } else {
                addMessage('ai', data.response || 'No speech detected');
                updateStatus("No speech");
            }
            startBtn.disabled = false;
            stopBtn.disabled = true;
        } else {
            addMessage('ai', data.error || 'Failed to stop');
            updateStatus("Error");
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    } catch (error) {
        console.error('Stop error:', error);
        addMessage('ai', 'Error: ' + error.message);
        updateStatus("Error");
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

startBtn.addEventListener('click', startListening);
stopBtn.addEventListener('click', stopListening);
clearBtn.addEventListener('click', () => {
    messagesDiv.innerHTML = '';
    updateStatus("Chat cleared");
});

window.addEventListener('resize', () => {
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
});