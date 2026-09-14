<script>
    import { createEventDispatcher } from 'svelte';
    export let isOpen = false;
    export let uploadDirectory;
    const dispatch = createEventDispatcher();

    let gitUrl = '';
    let directoryInput;
    let uploading = false;
    let uploadError = '';
    let uploadStatus = '';

    async function handleDirectorySelection(event) {
        const selected = Array.from(event.target.files || []);
        if (!selected.length) return;
        const extensions = new Set(['py', 'md', 'js', 'html', 'css', 'ts', 'sh', 'go', 'java', 'svelte']);
        const excluded = new Set(['.git', '.venv', 'venv', 'node_modules', '__pycache__', 'VectorStore', 'cache_embeddings', '.runtime']);
        const files = selected.filter(file => {
            const parts = file.webkitRelativePath.split('/');
            return !parts.slice(0, -1).some(part => excluded.has(part))
                && extensions.has(file.name.split('.').pop());
        });
        uploadError = '';
        try {
            if (!files.length) throw new Error('No supported source files in this directory.');
            if (files.length > 2000) throw new Error('Please select a directory with at most 2,000 source files.');
            if (files.some(file => file.size > 10 * 1024 * 1024)
                || files.reduce((size, file) => size + file.size, 0) > 50 * 1024 * 1024) {
                throw new Error('Upload limit: 10 MiB per file and 50 MiB total.');
            }
            uploading = true;
            const name = files[0].webkitRelativePath.split('/')[0];
            uploadStatus = `Uploading and indexing ${name} (${files.length} source files)…`;
            await uploadDirectory(files);
        } catch (error) {
            uploadError = error.message;
        } finally {
            uploading = false;
            uploadStatus = '';
            event.target.value = '';
        }
    }

    function handleConfirm() {
        if (gitUrl.trim()) {
            dispatch('confirm', gitUrl.trim());
            gitUrl = '';
        }
    }

    function handleCancel() {
        if (!uploading) dispatch('cancel');
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

    .modal input {
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

    .modal-buttons button:disabled {
        opacity: 0.5;
        cursor: default;
    }

    .upload-hint, .upload-status, .upload-error {
        font-size: 14px;
        overflow-wrap: anywhere;
    }

    .upload-error { color: #ffaaaa; }

    .overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 999;
    }
</style>

{#if isOpen}
    <div class="overlay" on:click={handleCancel}></div>
    <div class="modal">
        <h2>Enter GitHub URL</h2>
        <input type="text" bind:value={gitUrl} disabled={uploading} placeholder="https://github.com/user/repo.git" />
        <input type="file" bind:this={directoryInput} webkitdirectory multiple hidden on:change={handleDirectorySelection} />
        <div class="modal-buttons">
            <button on:click={handleConfirm} disabled={uploading}>Confirm</button>
            <button on:click={() => directoryInput.click()} disabled={uploading}>Upload</button>
            <button on:click={handleCancel} disabled={uploading}>Cancel</button>
        </div>
        <p class="upload-hint">Confirm loads the GitHub URL. Upload selects a local folder and sends its source files to QA-Pilot.</p>
        {#if uploading}<p class="upload-status" role="status">{uploadStatus}</p>{/if}
        {#if uploadError}<p class="upload-error" role="alert">{uploadError}</p>{/if}
    </div>
{/if}
