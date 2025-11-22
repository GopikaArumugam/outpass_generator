// chatbot.js
let step = 0;
let reason = "";
let leave_time = "";

// Function to display options only once
function selectOption(option) {
  appendMessage('user', option);
  document.getElementById('options').style.display = 'none';  // Hide options after selection
  if (option === 'Generate Outpass') {
    step = 1;
    askQuestion("Please enter the reason for your outpass.");
  } else if (option === 'Check Status') {
    fetch('/check_status')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          appendMessage('bot', `Your outpass status is: ${data.outpass_status}`);
        } else {
          appendMessage('bot', 'Unable to fetch status. Please login again.');
        }
      });
  } else {
    appendMessage('bot', 'This feature is coming soon!');
  }
}

function askQuestion(question) {
  appendMessage('bot', question);
  addInputBox();
}

function appendMessage(sender, message) {
  const div = document.createElement('div');
  div.className = `message ${sender}`;
  div.textContent = message;
  document.getElementById('chat-body').appendChild(div);
  document.getElementById('chat-body').scrollTop = document.getElementById('chat-body').scrollHeight;
}

// Add input box for user response
function addInputBox() {
  const inputBox = document.createElement('input');
  inputBox.id = 'user-input';
  inputBox.type = 'text';
  inputBox.placeholder = 'Type your answer here...';
  inputBox.className = 'chat-input';
  document.body.appendChild(inputBox);
  inputBox.focus();

  // Listen for Enter key press
  inputBox.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      const message = inputBox.value.trim();
      if (message) {
        handleResponse(message);
        inputBox.remove();
      }
    }
  });
}

// Handle user input
function handleResponse(message) {
  appendMessage('user', message);

  if (message.toLowerCase() === 'stop') {
    resetChat();
  } else if (step === 1) {
    reason = message;
    step = 2;
    askQuestion("When do you plan to leave? (e.g., 5:00 PM)");
  } else if (step === 2) {
    leave_time = message;
    step = 3;
    askQuestion("Analyzing your request...");
    
    fetch('/finalize_outpass', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason, leave_time: leave_time })
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        appendMessage('bot', `Outpass generated successfully! ID: ${data.outpass_id}`);
      } else {
        appendMessage('bot', `Failed: ${data.message}`);
      }
    });
  }
}

// Reset the chat to initial state
function resetChat() {
  step = 0;
  reason = "";
  leave_time = "";
  document.getElementById('chat-body').innerHTML = '';  // Clear chat history
  document.getElementById('options').style.display = 'block';  // Show options again
  appendMessage('bot', 'Hi {{ name }}! What would you like to do today?');  // Reset bot message
}
