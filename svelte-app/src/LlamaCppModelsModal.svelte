<script>
    import { createEventDispatcher, onMount } from 'svelte';
    import { API_BASE_URL } from './config.js';
    export let isOpen = false;
    const dispatch = createEventDispatcher();

    let models = [];
    let newModelFile = null;
    let uploadProgress = 0;
    let showProgressBar = false;
    let showMessage = false;
    let messageText = '';
    let messageType = '';

    async function fetchModels() {
        try {
            const response = await fetch(`${API_BASE_URL}/llamacpp_models`);
            if (!response.ok) {
                models = [];
            } else {
                models = await response.json();
            }
        } catch (error) {
            console.error('Failed to fetch models:', error);
            models = [];
        }
    }

    async function handleDelete(model) {
        await fetch(`${API_BASE_URL}/llamacpp_models/${model}`, { method: 'DELETE' });
        await fetchModels();
    }

    async function handleUpload() {
        if (!newModelFile) {
            showMessage = true;
            messageText = 'Please select a file to upload.';
            messageType = 'error';
            setTimeout(() => showMessage = false, 3000);
            return;
        }

        const CHUNK_SIZE = 10 * 1024 * 1024; // 10MB
        const totalChunks = Math.ceil(newModelFile.size / CHUNK_SIZE);

        showProgressBar = true;
        uploadProgress = 0;

        for (let start = 0; start < newModelFile.size; start += CHUNK_SIZE) {
            const chunk = newModelFile.slice(start, start + CHUNK_SIZE);
            const formData = new FormData();
            formData.append('file', chunk, newModelFile.name);
            formData.append('chunk', start / CHUNK_SIZE);
            formData.append('totalChunks', totalChunks);

            try {
                const response = await fetch(`${API_BASE_URL}/llamacpp_models`, {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error(`Failed to upload chunk ${start / CHUNK_SIZE}`);
                }

                // Update progress
                uploadProgress = ((start + CHUNK_SIZE) / newModelFile.size) * 100;
            } catch (error) {
                console.error('Error uploading chunk:', error);
                showMessage = true;
                messageText = `Error uploading chunk ${start / CHUNK_SIZE}`;
                messageType = 'error';
                setTimeout(() => showMessage = false, 3000);
                showProgressBar = false;
                uploadProgress = 0;
                return;
            }
        }

        showMessage = true;
        messageText = 'Upload successful';
        messageType = 'success';
        setTimeout(() => showMessage = false, 3000);

        showProgressBar = false;
        uploadProgress = 0;
        newModelFile = null; // Clear file input
        document.querySelector('input[type="file"]').value = ''; // Clear file input display
        await fetchModels();
    }

    function handleClose() {
        dispatch('cancel');
    }

    onMount(fetchModels);
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

    .modal-buttons {
        display: flex;
        justify-content: space-between;
        margin-top: 20px;
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

    .model-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .model-item button {
        padding: 5px;
        border: none;
        border-radius: 3px;
        background-color: #555;
        color: white;
        cursor: pointer;
    }

    .model-item button:hover {
        background-color: red;
    }

    .progress-bar {
        width: 100%;
        background-color: #ddd;
        border-radius: 10px;
        overflow: hidden;
        margin-top: 20px; /* Adjusted margin */
    }

    .progress-bar-inner {
        height: 20px;
        background-color: #4caf50; /* Green color */
        width: 0;
        transition: width 0.2s;
    }

    .message {
        margin-top: 10px;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }

    .message.success {
        background-color: #4caf50; /* Green */
        color: white;
    }

    .message.error {
        background-color: #f44336; /* Red */
        color: white;
    }
</style>

{#if isOpen}
    <div class="overlay" on:click={handleClose}></div>
    <div class="modal">
        <h2>LlamaCpp Models</h2>
        {#each models as model}
            <div class="model-item">
                <span>{model}</span>
                <button on:click={() => handleDelete(model)}>Delete</button>
            </div>
        {/each}
        <input type="file" on:change={e => newModelFile = e.target.files[0]} />
        {#if showProgressBar}
            <div class="progress-bar">
                <div class="progress-bar-inner" style="width: {uploadProgress}%"></div>
            </div>
        {/if}
        {#if showMessage}
            <div class="message {messageType}">{messageText}</div>
        {/if}
        <div class="modal-buttons">
            <button on:click={handleUpload}>Upload</button>
            <button on:click={handleClose}>Close</button>
        </div>
    </div>
{/if}
