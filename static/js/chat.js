class ChatSystem {
    constructor() {
        this.setupEventListeners();
        this.pollMessages();
    }

    setupEventListeners() {
        const input = document.querySelector('.chat-input');
        const sendBtn = document.querySelector('.send-btn');

        if (input && sendBtn) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            sendBtn.addEventListener('click', () => this.sendMessage());
        }
    }

    async sendMessage() {
        const input = document.querySelector('.chat-input');
        const content = input.value.trim();
        if (!content) return;

        try {
            const response = await fetch('/api/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    room_id: 'global'
                })
            });

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }

            this.displayMessage(data);
            input.value = '';
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }

    displayMessage(message) {
        // Check if message already exists
        if (document.querySelector(`[data-message-id="${message.id}"]`)) {
            return;
        }

        const messagesContainer = document.getElementById('global-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-container ${message.sender_id === currentUserId ? 'sent' : 'received'}`;
        messageDiv.setAttribute('data-message-id', message.id);

        messageDiv.innerHTML = `
            <img src="${message.avatar_url || '/static/images/default-avatar.png'}" class="message-avatar" alt="Profile Picture">
            <div class="message-content">
                <div class="message-sender">${message.sender}</div>
                <div class="message-text">${message.content}</div>
                <div class="message-time">${new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async pollMessages() {
        let lastMessageId = 0;
        const displayedMessages = new Set();

        setInterval(async () => {
            try {
                const response = await fetch(`/api/chat/messages?room_id=global&last_id=${lastMessageId}`);
                const messages = await response.json();

                if (messages.length > 0) {
                    messages.forEach(message => {
                        if (!displayedMessages.has(message.id)) {
                            this.displayMessage(message);
                            displayedMessages.add(message.id);
                        }
                    });
                    lastMessageId = Math.max(...messages.map(m => m.id));
                }
            } catch (error) {
                console.error('Error polling messages:', error);
            }
        }, 3000);
    }
}

// Initialize chat when document is loaded
document.addEventListener('DOMContentLoaded', () => {
    const chat = new ChatSystem();
});

async function handleAISubmit(event) {
    event.preventDefault();
    const input = document.getElementById('ai-input');
    const message = input.value.trim();
    
    if (!message) return;

    try {
        const response = await fetch('/api/chat/bot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();
        
        if (data.error) {
            console.error('Error:', data.error);
            return;
        }

        const messagesContainer = document.getElementById('ai-messages');
        
        // Add user message
        const userDiv = document.createElement('div');
        userDiv.className = 'message-container sent';
        userDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${message}</div>
            </div>
        `;
        messagesContainer.appendChild(userDiv);

        // Add AI response
        const aiDiv = document.createElement('div');
        aiDiv.className = 'message-container received';
        aiDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${data.response}</div>
            </div>
        `;
        messagesContainer.appendChild(aiDiv);

        // Clear input and scroll to bottom
        input.value = '';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        console.error('Error sending message:', error);
    }
}
