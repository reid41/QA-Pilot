<p align="center">
  <img src="https://github.com/reid41/QA-Pilot/assets/25558653/4b45b525-5fac-4a3c-94e9-46364bdb36c3" alt="qa-pilot">
</p>

QA-Pilot is an interactive chat project that leverages online/local LLM for rapid understanding and navigation of GitHub code repository or compressed file resource(e.g. xz, zip).

### Features

* Chat with github public repository with git clone way
* Chat with compressed file(directories, e.g. xz, zip) with upload way
* Store the chat history 
* Easy to set the configuration
* Multiple chat sessions
* Search the source documents
* Integrate with `codegraph` to view the python file
* Support the different LLM models
    * ollama
    * openai
    * mistralai

### Disclaimer

* This is a test project to validate the feasibility of a fully local solution for question answering using LLMs and Vector embeddings. It is not production ready, and it is not meant to be used in production. 
* `Do not use models for analyzing your critical or production data!!`
* `Do not use models for analyzing customer data to ensure data privacy and security!!`
* `Do not use models for analyzing you private/sensitivity code respository!!`

#### QA-Pilot
![Image Alt text](/images/qa_pilot1.jpg)

#### CodeGraph
![codegraph](https://github.com/reid41/QA-Pilot/assets/25558653/d06b8946-12be-46f3-b137-a1a237192b4a)


To deploy QA-Pilot, you can follow the below steps:

1. Clone the QA-Pilot repository:

```shell
git clone https://github.com/reid41/QA-Pilot.git
```

2. Install [conda](https://www.anaconda.com/download) for virtual environment management. Create and activate a new virtual environment.

```shell
conda create -n QA-Pilot python=3.10.14
conda activate QA-Pilot
```


3. Install the required dependencies:

```shell
pip install -r requirements.txt
```

4. Install the pytorch with cuda [pytorch](https://pytorch.org/get-started/locally/)


5. Setup [ollama website](https://ollama.com/) and [ollama github](https://github.com/ollama/ollama) to manage the local LLM model. 
e.g.

```shell
ollama pull <model_name>

ollama list
```

6. Setup [OpenAI](https://platform.openai.com/docs/overview) or [MistralAI](https://docs.mistral.ai/), add the key in `.env`

7. Set the related parameters in `config/config.ini`, e.g. `model provider`, `model`, `variable`, `Ollama API url`

8. Run the QA-Pilot:

```shell
streamlit run qa_pilot.py
```

9. Enable `codegraph` in `config/config.ini` and set the `host ip`(localhost by default)

```shell
[codegraph]
enabled = True
codegraph_host = http://localhost:5001
```

10. Open another terminal to run:

```shell
python codegraph/codegraph.py
```

### Tips
* Do not use url and upload at the same time.
* The remove button cannot really remove the local chromadb, need to remove it manually when stop it.
* Switch to `New Source Button` to add a new project
* To return source documents and start with `rsd:` input
* Click `Open Code Graph` in `QA-Pilot` to view the code(make sure the the already in the project session and loaded before click)

