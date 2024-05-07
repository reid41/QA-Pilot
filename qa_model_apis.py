from langchain_community.chat_models import ChatOllama
from langchain_community.chat_models import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import configparser
from dotenv import load_dotenv
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# read from the config.ini
config_path = os.path.join('config', 'config.ini')
config = configparser.ConfigParser()
config.read(config_path)
base_url = config.get('ollama_llm_models', 'base_url')


# get the chat model from config
def get_chat_model(provider, model_name):
    if provider == 'ollama':
        return ChatOllama(
            base_url=base_url,
            model=model_name,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
    elif provider == 'openai':
        load_dotenv()
        return ChatOpenAI(model_name=model_name)
    else:
        raise ValueError(f"Unsupported model provider: {provider}")
    

def get_embedding_model(eb_provider, model_name, model_kwargs, encode_kwargs):
     if eb_provider == 'huggingface': 
        return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
     else:
        raise ValueError(f"Unsupported embedding model provider: {eb_provider}")
