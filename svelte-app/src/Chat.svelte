<script>
    import { onMount, afterUpdate } from 'svelte';
    import { marked } from 'marked';
    export let currentRepo;
    export let messages = [];
    export let sessionId;
    export let sessionName;
    import { API_BASE_URL } from './config.js';

    let chatInput = '';
    let isLoading = false;
    let messagesContainer;

    onMount(() => {
        scrollToBottom();
    });

    afterUpdate(() => {
        scrollToBottom();
    });

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    async function sendMessage() {
        if (chatInput.trim() === '') return;

        const userInput = chatInput;

        messages = [...messages, { sender: 'You', text: userInput }];
        chatInput = '';
        isLoading = true;
        messages = [...messages, { sender: 'loader', text: 'Thinking...' }];

        try {
            const response = await fetch(`${API_BASE_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: userInput, current_repo: currentRepo, session_id: sessionId })
            });

            if (response.ok) {
                const data = await response.json();
                messages = messages.filter(message => message.sender !== 'loader');
                messages = [...messages, { sender: 'QA-Pilot', text: data.response }];
                await saveMessages();
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
        } finally {
            isLoading = false;
        }
    }

    async function saveMessages() {
        console.log('Saving messages for current session:', messages);
        await fetch(`${API_BASE_URL}/sessions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify([{ id: sessionId, name: sessionName, url: currentRepo, messages: JSON.stringify(messages) }])
        });
    }

    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    }

    async function copyToClipboard(text) {
        if (navigator.clipboard) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (error) {
                console.error('Failed to copy with clipboard API: ', error);
            }
        }
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            const successful = document.execCommand('copy');
            return successful;
        } catch (error) {
            console.error('Failed to copy with execCommand: ', error);
            return false;
        } finally {
            document.body.removeChild(textArea);
        }
    }

    async function handleCopyClick(event, message) {
        const button = event.currentTarget;
        const textToCopy = message.text || "";
        const success = await copyToClipboard(textToCopy);

        if (success) {
            button.innerHTML = 'Copied';
            setTimeout(() => {
                button.innerHTML = 'Copy';
            }, 2000);
        }
    }
</script>

<style>
    .chat-container {
        display: flex;
        flex-direction: column;
        flex: 1;
        overflow-y: auto;
    }

    .chat-messages {
        flex: 1;
        width: 100%;
        display: flex;
        flex-direction: column;
        margin-bottom: 20px;
        overflow-y: auto;
    }

    .chat-message {
        margin: 5px 0;
        padding: 10px;
        border-radius: 5px;
        font-size: 16px;
        position: relative;
    }

    .chat-message.user {
        align-self: flex-end;
        background-color: #3a3a3a;
    }

    .chat-message.bot {
        align-self: flex-start;
        background-color: #2d2d2d;
    }

    .chat-message.loader {
        align-self: flex-start;
        background-color: #2d2d2d;
        display: flex;
        align-items: center;
    }

    .chat-message .sender {
        font-weight: bold;
        margin-bottom: 5px;
    }

    .chat-message .loader-icon {
        border: 4px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top: 4px solid #00ff00;
        width: 20px;
        height: 20px;
        animation: spin 1s linear infinite;
        margin-right: 10px;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .copy-button-container {
        display: flex;
        justify-content: flex-start;
        margin-top: 5px;
    }

    .copy-button {
        background: none;
        border: none;
        color: #fff;
        cursor: pointer;
        font-size: 16px;
    }

    .chat-input-container {
        display: flex;
        width: 100%;
        position: sticky;
        bottom: 0;
        background-color: #1e1e1e;
        padding: 10px 0;
    }

    .chat-input {
        flex: 1;
        padding: 10px;
        border: none;
        border-radius: 5px;
        margin-right: 10px;
        background-color: #2d2d2d;
        color: #fff;
        font-size: 14px;
    }

    .send-button {
        padding: 10px;
        border: none;
        border-radius: 5px;
        background-color: #3a3a3a;
        color: #fff;
        cursor: pointer;
        font-size: 14px;
    }

    .send-button:hover {
        background-color: #555;
    }

    .upload-button {
        padding: 10px;
        border: none;
        background: none;
        cursor: pointer;
        color: #fff;
        margin-right: 10px;
    }

    .upload-button:hover {
        color: #ccc;
    }
</style>

<div class="chat-container">
    <div class="chat-messages" bind:this={messagesContainer}>
        {#each messages as message}
            <div class="chat-message {message.sender === 'You' ? 'user' : message.sender === 'loader' ? 'loader' : 'bot'}">
                {#if message.sender === 'loader'}
                    <div class="loader-icon"></div>
                    <div class="sender"></div>
                    <div>Thinking...</div>
                {:else}
                    <div class="sender">{message.sender}</div>
                    <div>{@html marked(message.text || '')}</div>
                    {#if message.sender !== 'You'}
                        <div class="copy-button-container">
                            <button class="copy-button" on:click={(event) => handleCopyClick(event, message)}>Copy</button>
                        </div>
                    {/if}
                {/if}
            </div>
        {/each}
    </div>
    <div class="chat-input-container">
        <button class="upload-button">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4H1v4a4 4 0 0 0 4 4h14a4 4 0 0 0 4-4v-4h-2zM18 9.83V13a1 1 0 0 1-2 0V9.83l-2.59 2.58a1 1 0 0 1-1.41-1.42l4.29-4.29a1 1 0 0 1 1.41 0l4.29 4.29a1 1 0 0 1-1.41 1.42L18 9.83z"/>
            </svg>
        </button>
        <input class="chat-input" type="text" placeholder="Type a message..." bind:value={chatInput} on:keypress={handleKeyPress}>
        <button class="send-button" on:click={sendMessage}>Send</button>
    </div>
</div>
