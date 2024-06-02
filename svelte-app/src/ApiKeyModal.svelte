<script>
    import { createEventDispatcher } from 'svelte';
    import { API_BASE_URL } from './config.js';

    export let isOpen = false;
    const dispatch = createEventDispatcher();
    let selectedProvider = 'openai';
    let apiKey = '';
    let successMessage = '';
    let errorMessage = '';
    let apiMessage = '';
    let apiMessageType = ''; // success or error

    async function checkApiKey() {
        const response = await fetch(`${API_BASE_URL}/check_api_key`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ provider: selectedProvider })
        });
        const data = await response.json();
        if (data.exists) {
            showApiMessage('API Key exists in .env file', 'success');
        } else {
            console.log('API Key does not exist in .env file');
        }
    }

    async function handleSave() {
        const response = await fetch(`${API_BASE_URL}/save_api_key`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ provider: selectedProvider, api_key: apiKey })
        });

        if (response.ok) {
            successMessage = 'API Key saved successfully!';
            errorMessage = '';
            // close it
            setTimeout(() => {
                dispatch('cancel');
                apiKey = '';
                successMessage = '';
            }, 1500);
        } else {
            errorMessage = 'Failed to save API Key';
            successMessage = '';
        }
    }

    
    function showApiMessage(message, type) {
        apiMessage = message;
        apiMessageType = type;
        setTimeout(() => {
            apiMessage = '';
            apiMessageType = '';
        }, 3000);
    }

    function handleCancel() {
        dispatch('cancel');
    }
</script>

<style>
    .modal {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: #2d2d2d;
        color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
        width: 60vw;
        max-width: 500px;
        z-index: 1000;
    }

    .modal h2 {
        margin-top: 0;
        margin-bottom: 10px;
    }

    .modal input, .modal select {
        width: 100%;
        margin-bottom: 10px;
        background-color: #3a3a3a;
        color: white;
        border: none;
        padding: 10px;
        border-radius: 5px;
    }

    .modal-buttons {
        display: flex;
        justify-content: space-between;
    }

    .modal-buttons button {
        padding: 10px;
        border: none;
        border-radius: 5px;
        background-color: #3a3a3a;
        color: white;
        cursor: pointer;
    }

    .modal-buttons button:hover {
        background-color: #555;
    }

    .overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 999;
    }

    .api-message {
        position: fixed;
        top: 40px;
        left: 50%;
        transform: translateX(-50%);
        padding: 10px 20px;
        border-radius: 5px;
        z-index: 1001;
        font-size: 16px;
        font-weight: bold;
        text-align: center;
    }

    .api-message.success {
        background-color: green;
        color: white;
    }

    .api-message.error {
        background-color: yellow;
        color: rgb(218, 59, 11);
    }
</style>

{#if isOpen}
    <div class="overlay" on:click={handleCancel}></div>
    <div class="modal">
        <h2>API Key Settings</h2>
        <select bind:value={selectedProvider} on:change={checkApiKey}>
            <option value="openai">OpenAI</option>
            <option value="mistral">Mistral</option>
        </select>
        <input type="text" bind:value={apiKey} placeholder="Enter API Key" />
        {#if successMessage}
            <p style="color: green;">{successMessage}</p>
        {/if}
        {#if errorMessage}
            <p style="color: red;">{errorMessage}</p>
        {/if}
        <!-- <div class="modal-buttons">
            <button on:click={() => testApiKey(false)}>Test from Here</button>
            <button on:click={() => testApiKey(true)}>Test from Env</button>
        </div> -->
        <div class="modal-buttons">
            <button on:click={handleSave}>Submit</button>
            <button on:click={handleCancel}>Cancel</button>
        </div>
    </div>
{/if}


{#if apiMessage}
    <div class="api-message {apiMessageType}">
        {apiMessage}
    </div>
{/if}
