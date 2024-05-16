from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
import git
import os
import json
from queue import Queue
import shutil
from urllib.parse import urlparse
import configparser
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts.prompt import PromptTemplate
from langchain.chains import ConversationChain
from qa_model_apis import (
    get_chat_model,
    get_embedding_model,
)

# read from the config.ini
config_path = os.path.join('config', 'config.ini')
config = configparser.ConfigParser()
config.read(config_path)
vectorstore_dir = config.get('the_project_dirs', 'vectorstore_dir')
sessions_dir = config.get('the_project_dirs', 'sessions_dir')
project_dir = config.get('the_project_dirs', 'project_dir')
max_dir_depth = config.get('for_loop_dirs_depth', 'max_dir_depth')
chunk_size = config.get('chunk_setting', 'chunk_size')
chunk_overlap = config.get('chunk_setting', 'chunk_overlap')
base_url = config.get('ollama_llm_models', 'base_url')
encode_kwargs = {"normalize_embeddings": False}
model_kwargs = {"device": "cuda:0"}  
allowed_extensions = ['.py', '.md', '.log']
        

# update the selected provider
def update_selected_provider(new_provider):
    config.set('model_providers', 'selected_provider', new_provider)
    with open(config_path, 'w') as configfile:
        config.write(configfile)


# update the selected model
def update_selected_model(new_model):
    selected_provider = config.get('model_providers', 'selected_provider')
    model_section = f"{selected_provider}_llm_models"
    config.set(model_section, 'selected_model', new_model)
    with open(config_path, 'w') as configfile:
        config.write(configfile)


# get the provider and the model name
def get_selected_provider_and_model():
    selected_provider = config.get('model_providers', 'selected_provider')
    model_section = f"{selected_provider}_llm_models"
    selected_model = config.get(model_section, 'selected_model')
    return selected_provider, selected_model


# get the provider and the model name
def get_embedding_selected_provider_and_model():
    eb_selected_provider = config.get('embedding_model_providers', 'selected_provider')
    eb_model_section = f"{eb_selected_provider}_embedding_models"
    eb_selected_model = config.get(eb_model_section, 'selected_model')
    return eb_selected_provider, eb_selected_model


# scan the the repo name file
def scan_vectorstore_for_repos():
    # define repo_info.json path
    repo_info_path = os.path.join(sessions_dir, 'repo_info.json')

    # load repo info from repo_info.json
    try:
        if os.path.exists(repo_info_path):
            with open(repo_info_path, 'r') as file:
                data = json.load(file)
                # get the repo list and return
                return [repo['name'] for repo in data.get('repos', [])]
        else:
            print(f"{repo_info_path} does not exist.")
            return []
    except json.JSONDecodeError as e:
        print(f"Error reading {repo_info_path}: {e}")
        return []


# remove the repo name and store path from json
def remove_repo_from_json(repo_name):
    repo_info_path = os.path.join(sessions_dir, 'repo_info.json')
    
    # load repo_info.json
    try:
        if os.path.exists(repo_info_path):
            with open(repo_info_path, 'r') as file:
                data = json.load(file)
            
            # check and remove
            repos = data.get('repos', [])
            repos = [repo for repo in repos if repo['name'] != repo_name]
            
            # update
            data['repos'] = repos
            
            # persistent the update
            with open(repo_info_path, 'w') as file:
                json.dump(data, file, indent=4)
                
            print(f"Repository {repo_name} has been removed from {repo_info_path}.")
        else:
            print(f"{repo_info_path} does not exist.")
    except json.JSONDecodeError as e:
        print(f"Error reading or writing {repo_info_path}: {e}")


# save the chat history
def save_session(session, repo_name):
    os.makedirs(sessions_dir, exist_ok=True) 
    session_file_path = os.path.join(sessions_dir, f'{repo_name}.json')
    with open(session_file_path, 'w') as f:
        json.dump(session, f)


# load the chat history
def load_session(repo_name):
    session_file_path = os.path.join(sessions_dir, f'{repo_name}.json')
    try:
        with open(session_file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []  


# update the repo and repo url mapping
def update_repo_urls(repo_name, repo_url=None, action="add"):
    os.makedirs(sessions_dir, exist_ok=True)
    repo_urls_path = os.path.join(sessions_dir, 'repo_urls.json')
    # load repo_urls
    try:
        if os.path.exists(repo_urls_path):
            with open(repo_urls_path, "r") as file:
                repo_urls = json.load(file)
        else:
            repo_urls = {}
    except json.JSONDecodeError:
        repo_urls = {}

    # update repo_urls
    if action == "add" and repo_url is not None:
        # add when update
        repo_urls[repo_name] = repo_url
    elif action == "delete":
        # remove it
        repo_urls.pop(repo_name, None)

    # save
    with open(repo_urls_path, "w") as file:
        json.dump(repo_urls, file)


# load the repo and url mapping
def load_repo_urls():
    repo_urls_path = os.path.join(sessions_dir, f'repo_urls.json')
    try:
        with open(repo_urls_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}  


# remove the directories for the download/upload projects
def remove_directory(dir_path):
    if os.path.exists(dir_path):
        # check and update file permisiion first
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for name in files:
                filepath = os.path.join(root, name)
                try:
                    os.chmod(filepath, 0o777)  # modify permission
                except PermissionError:
                    pass
            for name in dirs:
                dirpath = os.path.join(root, name)
                os.chmod(dirpath, 0o777)  
        
        # remove it
        shutil.rmtree(dir_path, ignore_errors=True)


# serialize the source data
def serialize_documents(source_documents):
    serialized_data = []
    for doc in source_documents:
        # get serialized_data
        serialized_data.append({
            'content': doc.page_content,
            'source': doc.metadata.get('source', 'Unknown source')
        })
    return serialized_data


# get the llm model and embedding model
current_selected_provider, current_selected_model = get_selected_provider_and_model()
eb_current_selected_provider, eb_current_selected_model = get_embedding_selected_provider_and_model()


class DataHandler:
    def __init__(self, git_url) -> None:
        self.git_url = git_url
        last_part = git_url.split('/')[-1]
        self.repo_name = last_part.rsplit('.', 1)[0]
        # create the store db and project dir
        if not os.path.exists(vectorstore_dir):
            os.makedirs(vectorstore_dir)
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
        # config the path
        self.db_dir = os.path.join(vectorstore_dir, self.repo_name)
        self.download_path = os.path.join(project_dir, self.repo_name) 
        self.model = get_chat_model(current_selected_provider, current_selected_model)
        self.embedding_model = get_embedding_model(eb_current_selected_provider, eb_current_selected_model, model_kwargs, encode_kwargs)
        self.ChatQueue =  Queue(maxsize=2)

    # check the db dir exist or not
    def db_exists(self):
        return os.path.exists(self.db_dir)

    # update the chat message queue
    def update_chat_queue(self, value):
        if self.ChatQueue.full():
            self.ChatQueue.get()
        self.ChatQueue.put(value)

    # download or upload the project
    def git_clone_repo(self):
        url_parts = urlparse(self.git_url)

        # Update the URL at the start of the function as required.
        update_repo_urls(self.repo_name, self.git_url if self.git_url else self.repo_name)

        # upload situation
        if not url_parts.scheme:
            print("Local repository detected, skipping cloning process.")
        else:
            # git clone
            if not os.path.exists(self.download_path):
                print(f"Cloning from Git URL: {self.git_url}")
                try:
                    git.Repo.clone_from(self.git_url, self.download_path)
                    print("Repository cloned successfully.")
                except Exception as e:
                    print(f"Failed to clone repository. Error: {e}")

    # load the projects
    def load_files(self, root_dir=None, current_depth=0, base_depth=0):
        if root_dir is None:
            root_dir = self.download_path
        self.docs = []
        
        print("Loading files from:", root_dir)
        
        # github projects
        if "UploadedRepo" not in self.git_url:
            for dirpath, _, filenames in os.walk(root_dir):
                for filename in filenames:
                    if any(filename.endswith(ext) for ext in allowed_extensions):
                        file_path = os.path.join(dirpath, filename)
                        try:
                            loader = TextLoader(file_path, encoding='utf-8')
                            self.docs.extend(loader.load_and_split())
                        except Exception as e:
                            print(f"Error loading file {file_path}: {e}")
        else:
            # sosreport project or directories upload
            if current_depth - base_depth > int(max_dir_depth):
                return  # over the dir depth, then stop
            
            for entry in os.scandir(root_dir):
                if entry.is_symlink():
                    continue  # skip the soft link(should be for windows)
                elif entry.is_dir():
                    if entry.name == 'boot':
                        base_depth = current_depth  # start from boot
                    self.load_files(entry.path, current_depth + 1, base_depth)
                elif entry.is_file():
                    # not limit for the file extension
                    try:
                        loader = TextLoader(entry.path, encoding='utf-8')
                        self.docs.extend(loader.load_and_split())
                    except Exception as e:
                        print(f"Error loading file {entry.path}: {e}")

    # split all the files
    def split_files(self):
        text_splitter = CharacterTextSplitter(chunk_size=int(chunk_size), chunk_overlap=int(chunk_overlap))
        self.texts = text_splitter.split_documents(self.docs)

    # save the repo name and path into json
    def save_repo_info_to_json(self):
        os.makedirs(sessions_dir, exist_ok=True)
        json_file = os.path.join(sessions_dir, 'repo_info.json') 

        info = {
            'repos': []
        }
        # load the repo info
        try:
            if os.path.exists(json_file):
                with open(json_file, 'r') as file:
                    info = json.load(file)
        except json.JSONDecodeError as e:
            print(f"Error reading {json_file}: {e}")
        
        # check whether in the list
        if not any(repo['name'] == self.repo_name for repo in info['repos']):
            # update the info
            info['repos'].append({
                'name': self.repo_name,
                'path': self.db_dir
            })
            # save
            try:
                with open(json_file, 'w') as file:
                    json.dump(info, file, indent=4)
                print(f"Repository info saved to {json_file}.")
            except Exception as e:
                print(f"Error writing to {json_file}: {e}")

    # store the all file chunk into chromadb
    def store_chroma(self):  
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
        db = Chroma.from_documents(self.texts, self.embedding_model, persist_directory=self.db_dir) 
        db.persist()  
        return db  
        
    # load 
    def load_into_db(self):
        if not os.path.exists(self.db_dir): 
            ## Create and load
            self.load_files()
            self.split_files()
            self.db = self.store_chroma()
        else:
            # Just load the DB
            self.db = Chroma(persist_directory=self.db_dir, embedding_function=self.embedding_model)
        
        self.retriever = self.db.as_retriever()
        self.retriever.search_kwargs['k'] = 3
        self.retriever.search_type = 'similarity'

        # save the repo name
        self.save_repo_info_to_json()

    # create a chain, send the message into llm and ouput the answer
    def retrieval_qa(self, query, rsd=False):
        chat_history = list(self.ChatQueue.queue)
        qa = ConversationalRetrievalChain.from_llm(
            self.model, 
            chain_type="stuff", 
            retriever=self.retriever, 
            condense_question_llm = self.model,
            return_source_documents=True)
        result = qa({"question": query, "chat_history": chat_history})
        self.update_chat_queue((query, result["answer"]))
        # add the search source documents
        serialized_docs = serialize_documents(result['source_documents'])
        if rsd:
            return serialized_docs
        else:
            return result['answer']
        
    def restrieval_qa_for_code(self, query):
        code_template = """I want you to act as a Senior Python developer. 
        I will provide you the code project, you provide detailed exaplanation. 
        Human: {input}
        History: {history}
        AI:"""
        PROMPT = PromptTemplate(input_variables=["input", "history"], template=code_template)
        conversation = ConversationChain(
            prompt=PROMPT,
            llm=self.model,
        )
        code_anaylsis = conversation.predict(input=query)
        return code_anaylsis