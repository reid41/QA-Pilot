import os
import configparser
from dotenv import load_dotenv
from langchain_core.callbacks import StreamingStdOutCallbackHandler
import multiprocessing

# read from the config.ini
from utils.runtime_config import get_config_path

config_path = get_config_path()
config = configparser.ConfigParser()
config.read(config_path)
ollama_base_url = config.get('ollama_llm_models', 'base_url')
# llmman (https://github.com/llmmanorg/llmman) serves the Ollama API on port 17434
llmman_base_url = config.get('llmman_llm_models', 'base_url')
localai_base_url = config.get('localai_llm_models', 'base_url')


# get the chat model from config
def get_chat_model(provider, model_name=''):    
    config.read(config_path)
    load_dotenv()
    if provider in ('ollama', 'llmman'):
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=config.get(f'{provider}_llm_models', 'base_url'),
            model=model_name,
            num_ctx=config.getint(f'{provider}_llm_models', 'num_ctx', fallback=8192),
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
    elif provider == 'openai':
        from langchain_openai import ChatOpenAI
        load_dotenv()
        return ChatOpenAI(model_name=model_name)
    elif provider == 'mistralai':
        from langchain_mistralai import ChatMistralAI
        load_dotenv()
        return ChatMistralAI(model_name=model_name)
    elif provider == 'localai':
        from llama_index.llms.openai_like import OpenAILike
        return OpenAILike(  
            api_base=config.get('localai_llm_models', 'base_url'),
            api_key="qa_pilot",  
            is_chat_model=True,  
            context_window=32768,  
            model=model_name
        )
    elif provider == 'zhipuai':
        from langchain_community.chat_models import ChatZhipuAI
        load_dotenv()
        return ChatZhipuAI(
            model=model_name,
            temperature=0.5,
        )
    elif provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        load_dotenv()
        return ChatAnthropic(
            model=model_name
        )
    elif provider == 'llamacpp':
        from langchain_community.chat_models import ChatLlamaCpp
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
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        load_dotenv()
        return ChatNVIDIA(
            model=model_name
        )
    elif provider == 'tongyi':
        from langchain_community.chat_models.tongyi import ChatTongyi
        load_dotenv()
        return ChatTongyi(
            model=model_name
        ) 
    elif provider == 'moonshot':
        from langchain_community.chat_models.moonshot import MoonshotChat
        load_dotenv()
        return MoonshotChat(
            model=model_name
        ) 
    else:
        raise ValueError(f"Unsupported model provider: {provider}")
    

def get_embedding_model(eb_provider, model_name='', model_kwargs='', encode_kwargs=''):
     config.read(config_path)
     if eb_provider == 'huggingface': 
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs,
                cache_folder="./cache_embeddings/"
            )
     elif eb_provider == 'ollama':
         from langchain_ollama import OllamaEmbeddings
         return OllamaEmbeddings(
                model=model_name,
                base_url=config.get('ollama_embedding_models', 'base_url',
                                    fallback=config.get('ollama_llm_models', 'base_url')),
         )
     else:
        raise ValueError(f"Unsupported embedding model provider: {eb_provider}")
