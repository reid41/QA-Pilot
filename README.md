## QA-Pilot

QA-Pilot can chat with github repository or a compressd file(e.g. sosreport) and using the online/local LLM. 

### Features

* Chat with github public repository with git clone way
* Chat with compressed file(directories, e.g. sosreport) with upload way
* Store the chat history 
* Select the different LLM models
    * ollama
    * openai

![Image Alt text](/images/qa_pilot.jpg)

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
NOTE: you might need to re-install the pytorch with cuda [pytorch](https://pytorch.org/get-started/locally/)

```shell
pip install -r requirements.txt
```


4. Setup [ollama website](https://ollama.com/) and [ollama github](https://github.com/ollama/ollama) to manage the local LLM model. 
e.g.

```shell
ollama pull <model_name>

ollama list
```

5. Setup OpenAI, add the key in `.env`

6. Run the QA-Pilot:

```shell
streamlit run qa_pilot.py
```

### Tips
* Do not use url and upload at the same time.
* The remove button cannot really remove the local chromadb, need to remove it manually when stop it.
* Switch to `New Source Button` to add a new project

### Disclaimer

This is a test project to validate the feasibility of a fully local solution for question answering using LLMs and Vector embeddings. It is not production ready, and it is not meant to be used in production. Vicuna-7B is based on the Llama model so that has the original Llama license.
Do not use online models for analyzing your critical or production data!!
Do not use online models for analyzing customer data to ensure data privacy and
security!!

