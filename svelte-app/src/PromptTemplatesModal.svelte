<script>
    import { createEventDispatcher, onMount } from 'svelte';
    import { API_BASE_URL } from './config.js';
    import DeleteTemplateModal from './DeleteTemplateModal.svelte';

    export let isOpen = false;
    const dispatch = createEventDispatcher();

    let templates = {};
    let selectedTemplate = '';
    let selectedTemplateContent = '';
    let newTemplateName = '';
    let newTemplateContent = '';
    let showMessage = false;
    let messageText = '';
    let messageType = '';
    let showDeleteModal = false;

    async function fetchTemplates() {
        try {
            const response = await fetch(`${API_BASE_URL}/get_prompt_templates`);
            if (!response.ok) {
                throw new Error('Failed to fetch templates');
            }
            templates = await response.json();
            if (Object.keys(templates).length > 0) {
                selectedTemplate = Object.keys(templates)[0];
                selectedTemplateContent = templates[selectedTemplate];
            }
        } catch (error) {
            console.error('Error fetching templates:', error);
            showMessage = true;
            messageText = 'Error fetching templates';
            messageType = 'error';
            setTimeout(() => showMessage = false, 3000);
        }
    }

    function handleTemplateChange(event) {
        selectedTemplate = event.target.value;
        selectedTemplateContent = templates[selectedTemplate];
    }

    function handleContentChange(event) {
        selectedTemplateContent = event.target.value;
    }

    async function saveTemplates() {
        templates[selectedTemplate] = selectedTemplateContent;
        try {
            const response = await fetch(`${API_BASE_URL}/save_prompt_templates`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(templates)
            });
            if (!response.ok) {
                throw new Error('Failed to save templates');
            }
            showMessage = true;
            messageText = 'Templates saved successfully!';
            messageType = 'success';
        } catch (error) {
            console.error('Error saving templates:', error);
            showMessage = true;
            messageText = 'Failed to save templates';
            messageType = 'error';
        }
        setTimeout(() => showMessage = false, 3000);
    }

    function addTemplate() {
        if (newTemplateName && newTemplateContent) {
            templates[newTemplateName] = newTemplateContent;
            selectedTemplate = newTemplateName;
            selectedTemplateContent = newTemplateContent;
            newTemplateName = '';
            newTemplateContent = '';
            saveTemplates(); // Save new template to backend
        }
    }

    function openDeleteModal() {
        if (selectedTemplate) {
            showDeleteModal = true;
        }
    }

    async function deleteTemplate() {
        if (selectedTemplate) {
            try {
                const response = await fetch(`${API_BASE_URL}/delete_prompt_template`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ template_name: selectedTemplate })
                });

                if (!response.ok) {
                    throw new Error('Failed to delete template');
                }

                delete templates[selectedTemplate];
                if (Object.keys(templates).length > 0) {
                    selectedTemplate = Object.keys(templates)[0];
                    selectedTemplateContent = templates[selectedTemplate];
                } else {
                    selectedTemplate = '';
                    selectedTemplateContent = '';
                }
                showMessage = true;
                messageText = 'Template deleted successfully!';
                messageType = 'success';
                showDeleteModal = false;
                
                // Fetch templates again to update the dropdown
                await fetchTemplates();

            } catch (error) {
                console.error('Error deleting template:', error);
                showMessage = true;
                messageText = 'Failed to delete template';
                messageType = 'error';
                showDeleteModal = false;
            }
            setTimeout(() => showMessage = false, 3000);
        }
    }

    function handleClose() {
        dispatch('cancel');
    }

    onMount(fetchTemplates);
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
        <h2>Prompt Templates</h2>
        <select on:change={handleTemplateChange} bind:value={selectedTemplate}>
            {#each Object.keys(templates) as key}
                <option value={key}>{key}</option>
            {/each}
        </select>
        <textarea rows="10" cols="50" bind:value={selectedTemplateContent} on:input={handleContentChange}></textarea>
        <div class="modal-buttons">
            <button on:click={saveTemplates}>Save Templates</button>
            <button on:click={openDeleteModal}>Delete Template</button>
            <button on:click={handleClose}>Close</button>
        </div>
        <input type="text" placeholder="New Template Name" bind:value={newTemplateName} />
        <textarea placeholder="New Template Content" rows="4" cols="50" bind:value={newTemplateContent}></textarea>
        <button on:click={addTemplate}>Add Template</button>
        {#if showMessage}
            <div class="message {messageType}">{messageText}</div>
        {/if}
    </div>
{/if}

<DeleteTemplateModal 
    isOpen={showDeleteModal} 
    templateName={selectedTemplate} 
    on:confirm={deleteTemplate} 
    on:cancel={() => showDeleteModal = false} 
/>
