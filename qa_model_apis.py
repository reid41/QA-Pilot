from langchain_community.chat_models import ChatOllama
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_openai import ChatOpenAI
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
import os
import configparser
from dotenv import load_dotenv
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from llama_index.llms.openai_like import OpenAILike
from langchain_community.chat_models import ChatZhipuAI
from langchain_anthropic import ChatAnthropic
import multiprocessing
from langchain_community.chat_models import ChatLlamaCpp
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.chat_models.moonshot import MoonshotChat

# read from the config.ini
config_path = os.path.join('config', 'config.ini')
config = configparser.ConfigParser()
config.read(config_path)
ollama_base_url = config.get('ollama_llm_models', 'base_url')
localai_base_url = config.get('localai_llm_models', 'base_url')


# get the chat model from config
def get_chat_model(provider, model_name=''):    
    if provider == 'ollama':
        return ChatOllama(
            base_url=ollama_base_url,
            model=model_name,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
    elif provider == 'openai':
        load_dotenv()
        return ChatOpenAI(model_name=model_name)
    elif provider == 'mistralai':
        load_dotenv()
        return ChatMistralAI(model_name=model_name)
    elif provider == 'localai':
        return OpenAILike(  
            api_base=localai_base_url,  
            api_key="qa_pilot",  
            is_chat_model=True,  
            context_window=32768,  
            model=model_name
        )
    elif provider == 'zhipuai':
        load_dotenv()
        return ChatZhipuAI(
            model=model_name,
            temperature=0.5,
        )
    elif provider == 'anthropic':
        load_dotenv()
        return ChatAnthropic(
            model=model_name
        )
    elif provider == 'llamacpp':
        local_model = os.path.join("llamacpp_models", model_name)
        return ChatLlamaCpp(
            temperature=0.5,
            model_path=local_model,
            n_ctx=10000,
            n_gpu_layers=8,
            n_batch=300,  # Should be between 1 and n_ctx, consider the amount of VRAM in your GPU.
            max_tokens=512,
            n_threads=multiprocessing.cpu_count() - 1,
            repeat_penalty=1.5,
            top_p=0.5,
            verbose=True,
        )
    elif provider == 'nvidia':
        load_dotenv()
        return ChatNVIDIA(
            model=model_name
        )
    elif provider == 'tongyi':
        load_dotenv()
        return ChatTongyi(
            model=model_name
        ) 
    elif provider == 'moonshot':
        load_dotenv()
        return MoonshotChat(
            model=model_name
        ) 
    else:
        raise ValueError(f"Unsupported model provider: {provider}")
    

def get_embedding_model(eb_provider, model_name='', model_kwargs='', encode_kwargs=''):
     if eb_provider == 'huggingface': 
        return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
     elif eb_provider == 'ollama':
         return OllamaEmbeddings(
                model=model_name,
                model_kwargs=model_kwargs
         )
     else:
        raise ValueError(f"Unsupported embedding model provider: {eb_provider}")