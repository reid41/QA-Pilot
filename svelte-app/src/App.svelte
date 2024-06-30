<script>
    import { onMount } from 'svelte';
    import ConfigEditor from './ConfigEditor.svelte';
    import Chat from './Chat.svelte';
    import { marked } from 'marked';
    import NewSourceModal from './NewSourceModal.svelte';
    import ApiKeyModal from './ApiKeyModal.svelte';
    import DeleteConfirmationModal from './DeleteConfirmationModal.svelte';
    import LlamaCppModelsModal from './LlamaCppModelsModal.svelte';
    import PromptTemplatesModal from './PromptTemplatesModal.svelte';
    import { API_BASE_URL } from './config.js';

    let showConfigEditor = false;
    let showNewSourceModal = false;
    let showApiKeyModal = false;
    let showDeleteModal = false;
    let configData = {};
    let configOrder = [];
    let currentRepo = '';
    let sessions = [];
    let currentSessionIndex = -1;
    let messages = [];
    let providerList = [];
    let selectedProvider = '';
    let modelList = [];
    let selectedModel = '';
    let showDefaultMessage = true;
    let sessionToDelete = null;
    let sessionToDeleteName = '';
    let searchKeyword = '';
    let filteredSessions = [];
    let showSettings = false; // control the Settings hide or show
    let showLlamaCppModelsModal = false;
    let showPromptTemplatesModal = false;
    let showCodeGraphOptions = false;

    async function fetchConfig() {
        try {
            const response = await fetch(`${API_BASE_URL}/get_config`);
            if (response.ok) {
                const data = await response.json();
                configData = data;
                configOrder = Object.keys(data);
                providerList = data['model_providers']['provider_list'].split(', ');
                selectedProvider = data['model_providers']['selected_provider'];
                updateModelList();
            } else {
                console.error('Failed to fetch config');
            }
        } catch (error) {
            console.error('Error fetching config:', error);
        }
    }

    async function saveConfig() {
        const response = await fetch(`${API_BASE_URL}/save_config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });

        if (!response.ok) {
            alert('Failed to save configuration');
        } else {
            console.log('Configuration saved successfully!');
        }
    }

    function updateModelList() {
        modelList = configData[`${selectedProvider}_llm_models`]['model_list'].split(', ');
        selectedModel = configData[`${selectedProvider}_llm_models`]['selected_model'];
    }

    function handleProviderChange(event) {
        selectedProvider = event.target.value;
        configData['model_providers']['selected_provider'] = selectedProvider;
        updateModelList();
        saveConfig();
    }

    function handleModelChange(event) {
        selectedModel = event.target.value;
        configData[`${selectedProvider}_llm_models`]['selected_model'] = selectedModel;
        saveConfig();
    }

    async function toggleConfigEditor() {
        showConfigEditor = !showConfigEditor;
        if (showConfigEditor) {
            await fetchConfig();
        }
    }

    async function createNewSession(gitUrl) {
        let repoName = gitUrl.split('/').pop().replace('.git', '');
        let newSession = { id: Date.now(), name: repoName, url: gitUrl, messages: [{ sender: 'QA-Pilot', text: `url:${gitUrl}` }, { sender: 'loader', text: 'Thinking...' }] };
        sessions.push(newSession);
        currentSessionIndex = sessions.length - 1;
        currentRepo = gitUrl;
        messages = newSession.messages;
        showDefaultMessage = false;
        await saveSessions();
        await loadRepo(gitUrl);
        await updateCurrentSession(newSession);
    }

    async function switchSession(sessionId) {
        const index = sessions.findIndex(session => session.id === sessionId);
        currentSessionIndex = index;
        currentRepo = sessions[index].url;
        await updateCurrentSession(sessions[index]);
        loadMessages(sessions[index].id);
    }

    async function updateCurrentSession(session) {
        try {
            const response = await fetch(`${API_BASE_URL}/update_current_session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(session)
            });

            if (!response.ok) {
                console.error('Failed to update current session');
            }
        } catch (error) {
            console.error('Error updating current session:', error);
        }
    }

    function openNewSourceModal() {
        showNewSourceModal = true;
    }

    function closeNewSourceModal() {
        showNewSourceModal = false;
    }

    function openApiKeyModal() {
        showApiKeyModal = true;
    }

    function closeApiKeyModal() {
        showApiKeyModal = false;
    }

    async function handleNewSource(event) {
        const gitUrl = event.detail;
        closeNewSourceModal();
        if (gitUrl) {
            await createNewSession(gitUrl);
        }
    }

    async function loadRepo(gitUrl) {
        try {
            const response = await fetch(`${API_BASE_URL}/load_repo`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ git_url: gitUrl })
            });

            if (response.ok) {
                const data = await response.json();
                let currentMessages = sessions[currentSessionIndex].messages;
                currentMessages = currentMessages.filter(message => message.sender !== 'loader');
                currentMessages.push({ sender: 'QA-Pilot', text: `Repository ${gitUrl} loaded successfully!` });
                sessions[currentSessionIndex].messages = currentMessages;
                messages = currentMessages;
                await saveSessions();
            } else {
                throw new Error('Failed to load repository');
            }
        } catch (error) {
            console.error('Error loading repository:', error);
        }
    }

    async function loadSessions() {
        try {
            const response = await fetch(`${API_BASE_URL}/sessions`);
            if (response.ok) {
                const data = await response.json();
                sessions = data;
                if (sessions.length > 0) {
                    currentSessionIndex = 0;
                    currentRepo = sessions[0].url;
                    loadMessages(sessions[0].id);
                    showDefaultMessage = false;
                }

                // initial filter session
                filterSessions();
            } else {
                console.error('Failed to load sessions');
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    async function loadMessages(sessionId) {
        try {
            const response = await fetch(`${API_BASE_URL}/messages/${sessionId}`);
            if (response.ok) {
                const data = await response.json();
                messages = data;
            } else {
                console.error('Failed to load messages');
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    async function saveSessions() {
        try {
            const response = await fetch(`${API_BASE_URL}/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(sessions)
            });
            if (!response.ok) {
                console.error('Failed to save sessions');
            }
        } catch (error) {
            console.error('Error saving sessions:', error);
        }
    }

    async function deleteSession(index) {
        const sessionId = sessions[index].id;
        try {
            const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                sessions.splice(index, 1);
                currentSessionIndex = sessions.length > 0 ? 0 : -1;
                if (currentSessionIndex !== -1) {
                    currentRepo = sessions[0].url;
                    await updateCurrentSession(sessions[0]);
                    loadMessages(sessions[0].id);
                } else {
                    messages = [];
                    currentRepo = '';
                }
                await loadSessions();
            } else {
                console.error('Failed to delete session');
            }
        } catch (error) {
            console.error('Error deleting session:', error);
        }
    }

    function toggleCodeGraphOptions() {
        showCodeGraphOptions = !showCodeGraphOptions;
    }

    function openPythonCodeGraph() {
        window.open(`${API_BASE_URL}/codegraph`, '_blank');
    }

    function openGoCodeGraph() {
        window.open(`${API_BASE_URL}/go_codegraph`, '_blank');
    }

    function confirmDeleteSession(sessionId) {
        sessionToDelete = sessionId;
        const session = sessions.find(s => s.id === sessionId);
        sessionToDeleteName = session ? session.name : '';
        showDeleteModal = true;
    }

    async function handleConfirmDelete() {
        const index = sessions.findIndex(session => session.id === sessionToDelete);
        if (index !== -1) {
            deleteSession(index);
        }
        showDeleteModal = false;
    }

    function handleCancelDelete() {
        showDeleteModal = false;
    }

    function handleSearch(event) {
        searchKeyword = event.target.value.toLowerCase();
        filterSessions();
    }

    function filterSessions() {
        if (searchKeyword) {
            filteredSessions = sessions.filter(session => session.name.toLowerCase().includes(searchKeyword));
        } else {
            filteredSessions = sessions;
        }
    }

    function toggleSettings() {
        showSettings = !showSettings;
    }

    function openLlamaCppModelsModal() {
        showLlamaCppModelsModal = true;
    }

    function closeLlamaCppModelsModal() {
        showLlamaCppModelsModal = false;
    }

    function openPromptTemplatesModal() {
        showPromptTemplatesModal = true;
    }

    function closePromptTemplatesModal() {
        showPromptTemplatesModal = false;
    }

    onMount(async () => {
        await loadSessions();
        await fetchConfig();
        filterSessions(); //initial filter session
    });
</script>

<style>
    .container {
        display: flex;
        height: 100vh;
        background-color: #1e1e1e;
    }

    .sidebar {
        width: 200px;
        background-color: #2d2d2d;
        color: #fff;
        display: flex;
        flex-direction: column;
        padding: 10px;
    }

    .sidebar input {
        background-color: #3a3a3a;
        border: none;
        color: white;
        padding: 10px;
        font-size: 16px;
        margin: 5px 0;
    }

    .sidebar button {
        background-color: #3a3a3a;
        border: none;
        color: white;
        padding: 10px;
        text-align: left;
        text-decoration: none;
        display: block;
        font-size: 16px;
        margin: 5px 0;
        cursor: pointer;
        position: relative;
    }

    .sidebar button:hover {
        background-color: #555;
    }

    .content {
        flex: 1;
        background-color: #1e1e1e;
        color: #fff;
        display: flex;
        flex-direction: column;
        font-size: 18px;
        position: relative;
        padding: 10px;
    }

    .header {
        text-align: center;
        font-size: 24px;
        margin-bottom: 10px;
    }

    .active {
        background-color: #555;
    }

    .session-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-right: 1px;
        margin-bottom: 5px;
        background-color: #3a3a3a;
    }

    .delete-button {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 16px;
    }

    .delete-button:hover {
        color: red;
    }

    .submenu {
        display: none;
        flex-direction: column;
        margin-left: 10px;
    }

    .submenu.visible {
        display: flex;
    }

    .arrow {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 12px;
    }

    .rotate {
        transform: translateY(-50%) rotate(90deg);
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

    .submenu-codegraph {
        display: none;
        flex-direction: column;
        margin-left: 10px;
    }

    .submenu-codegraph.visible {
        display: flex;
    }
</style>

<div class="container">
    <div class="sidebar">
        <label for="provider-select">Select Provider:</label>
        <select id="provider-select" on:change={handleProviderChange} bind:value={selectedProvider}>
            {#each providerList as provider}
                <option value={provider}>{provider}</option>
            {/each}
        </select>

        <label for="model-select">Select Model:</label>
        <select id="model-select" on:change={handleModelChange} bind:value={selectedModel}>
            {#each modelList as model}
                <option value={model}>{model}</option>
            {/each}
        </select>

        <button on:click={toggleCodeGraphOptions}>
            Open Code Graph
            <span class="arrow {showCodeGraphOptions ? 'rotate' : ''}">&#9654;</span>
        </button>
        <div class="submenu-codegraph {showCodeGraphOptions ? 'visible' : ''}">
            <button on:click={openPythonCodeGraph}>Python Codegraph</button>
            <button on:click={openGoCodeGraph}>Go Codegraph</button>
        </div>

        <button on:click={toggleSettings}>
            Settings
            <span class="arrow {showSettings ? 'rotate' : ''}">&#9654;</span>
        </button>
        <div class="submenu {showSettings ? 'visible' : ''}">
            <button on:click={toggleConfigEditor}>Edit QA-Pilot Settings</button>
            <button on:click={openApiKeyModal}>AI Vendor API Key</button>
            <button on:click={openLlamaCppModelsModal}>Llamacpp models</button>
            <button on:click={openPromptTemplatesModal}>Prompt Templates</button>
        </div>

        <button on:click={openNewSourceModal}>New Source Button</button>

        <input type="text" placeholder="Search sessions" on:input={handleSearch} bind:value={searchKeyword} />

        {#each filteredSessions as session}
        <div class="session-item">
            <button on:click={() => switchSession(session.id)} class:active={session.id === sessions[currentSessionIndex]?.id}>
                {session.name}
            </button>
            <button class="delete-button" on:click={() => confirmDeleteSession(session.id)}>🗑️</button>
        </div>
        {/each}
    </div>
    <div class="content">
        <div class="header">{currentSessionIndex !== -1 ? sessions[currentSessionIndex].name : 'QA-Pilot'}</div>
        {#if currentSessionIndex !== -1}
            <Chat {currentRepo} bind:messages={messages} bind:sessionId={sessions[currentSessionIndex].id} sessionName={sessions[currentSessionIndex].name} />
        {:else}
            <div style="color: white; font-size: 23px; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
                <img src="/qa-pilot1.png" alt="Placeholder Image" style="width: 200px; height: auto; margin-bottom: 20px;">
                <p>1. Please check your config with "Edit QA-Pilot Settings" button.</p>
                <p>2. Click "New Source Button" to input the github URL.</p>
            </div>
        {/if}
    </div>
</div>

{#if showConfigEditor}
    <ConfigEditor
        {configData}
        {configOrder}
        {saveConfig}
        {toggleConfigEditor} />
{/if}

{#if showNewSourceModal}
    <NewSourceModal
        isOpen={showNewSourceModal}
        on:confirm={handleNewSource}
        on:cancel={closeNewSourceModal} />
{/if}

{#if showApiKeyModal}
    <ApiKeyModal
        isOpen={showApiKeyModal}
        on:cancel={closeApiKeyModal} />
{/if}

{#if showLlamaCppModelsModal}
    <LlamaCppModelsModal
        isOpen={showLlamaCppModelsModal}
        on:cancel={closeLlamaCppModelsModal} />
{/if}

{#if showPromptTemplatesModal}
    <PromptTemplatesModal
        isOpen={showPromptTemplatesModal}
        on:cancel={closePromptTemplatesModal} />
{/if}

{#if showDeleteModal}
    <DeleteConfirmationModal
        isOpen={showDeleteModal}
        sessionName={sessionToDeleteName}
        on:confirm={handleConfirmDelete}
        on:cancel={handleCancelDelete} />
{/if}
