<script>
    import { createEventDispatcher } from 'svelte';
    export let isOpen = false;
    const dispatch = createEventDispatcher();

    let gitUrl = '';

    function handleConfirm() {
        if (gitUrl.trim()) {
            dispatch('confirm', gitUrl);
            gitUrl = '';
        }
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
        <input type="text" bind:value={gitUrl} placeholder="https://github.com/user/repo.git" />
        <div class="modal-buttons">
            <button on:click={handleConfirm}>Confirm</button>
            <button on:click={handleCancel}>Cancel</button>
        </div>
    </div>
{/if}
