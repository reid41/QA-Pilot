<script>
    import { createEventDispatcher } from 'svelte';
    export let isOpen = false;
    export let sessionName = ''; // show the session name
    const dispatch = createEventDispatcher();

    function handleConfirm() {
        dispatch('confirm');
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
        font-size: 18px; /* 调整字体大小 */
    }

    .modal .session-name {
        font-weight: bold; /* 加粗显示会话名称 */
        color: #ff4757; /* 高亮显示为红色 */
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

    .modal-buttons .delete-button {
        background-color: #ff4757; 
    }

    .modal-buttons .delete-button:hover {
        background-color: #ff6b81; 
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
        <h2>Are you sure you want to delete the session: <span class="session-name">{sessionName}</span>?</h2>
        <div class="modal-buttons">
            <button class="delete-button" on:click={handleConfirm}>Delete</button>
            <button on:click={handleCancel}>Cancel</button>
        </div>
    </div>
{/if}
