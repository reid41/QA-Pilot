<!-- src/ConfigEditor.svelte -->
<script>
    export let configData = {};
    export let configOrder = [];
    export let saveConfig;
    export let toggleConfigEditor;

    async function handleSaveConfig() {
        saveConfig();
        toggleConfigEditor(); // close the windows
    }
  </script>
  
  <style>
    .config-editor {
      position: absolute;
      top: 5%;
      left: 50%;
      transform: translate(-50%, 0);
      background-color: #2d2d2d;
      color: white;
      padding: 20px;
      border-radius: 10px;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
      max-height: 90vh;
      overflow-y: auto;
      width: 60vw; /* 设置宽度 */
    }
  
    .config-section {
      margin-bottom: 20px;
    }
  
    .config-editor h3 {
      margin-top: 0;
      margin-bottom: 10px;
    }
  
    .config-editor label {
      display: block;
      margin-bottom: 5px;
      color: #ccc;
    }
  
    .config-editor input {
      width: 100%;
      margin-bottom: 10px;
      background-color: #3a3a3a;
      color: white;
      border: none;
      padding: 5px;
    }
  
    .config-editor-buttons {
      display: flex;
      justify-content: space-between;
      margin-top: 20px;
    }
  </style>
  
  <div class="config-editor">
    <h2>Edit QA-Pilot Settings</h2>
    {#if Object.keys(configData).length === 0}
      <p>Loading configuration...</p>
    {:else}
      {#each configOrder as section}
        <div class="config-section">
          <h3>{section}</h3>
          {#each Object.keys(configData[section]) as key}
            <label>{key}</label>
            <input type="text" bind:value={configData[section][key]}>
          {/each}
        </div>
      {/each}
      <div class="config-editor-buttons">
        <button on:click={handleSaveConfig}>Save Changes</button>
        <button on:click={toggleConfigEditor}>Cancel</button>
      </div>
    {/if}
  </div>
  