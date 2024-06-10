from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
import git
import os
from queue import Queue
import shutil
from urllib.parse import urlparse
import configparser
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.chains import ConversationChain
from cachetools import cached, TTLCache
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import FlashrankRerank


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


def document_to_string(document):
    # Get the document content
    content = document.page_content
    # Get the metadata
    metadata = document.metadata
    # Convert the metadata dictionary to a string
    metadata_str = ', '.join(f'{key}: {value}' for key, value in metadata.items())
    # Combine the content and metadata into a single string
    result = f'Content: {content}\nMetadata: {metadata_str}'
    return result

def documents_to_string(documents):
    # Convert each Document object to a string and add to the list
    doc_strings = [document_to_string(doc) for doc in documents]
    # Join all strings into a single large string
    return '\n\n'.join(doc_strings)


cache = TTLCache(maxsize=100, ttl=300)

class DataHandler:
    def __init__(self, git_url, chat_model, embedding_model) -> None:
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
        self.model = chat_model
        self.embedding_model = embedding_model     
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

    # store the all file chunk into chromadb
    def store_chroma(self):  
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
        print("eb:", self.embedding_model)
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
            print("start-->chromadb")
            # Just load the DB
            self.db = Chroma(persist_directory=self.db_dir, embedding_function=self.embedding_model)
            print("end-->chromadb")
        
        self.retriever = self.db.as_retriever()
        self.retriever.search_kwargs['k'] = 3
        self.retriever.search_type = 'similarity'

    # create a chain, send the message into llm and ouput the answer
    @cached(cache)
    def retrieval_qa(self, query, rsd=False, rr=False):
        config = configparser.ConfigParser()
        config.read(config_path)
        the_selected_provider = config.get('model_providers', 'selected_provider')
        chat_history = list(self.ChatQueue.queue)
        qa_template = """I want you to act as a very senior code developer. 
        and very familar with github/gitlab community,I will provide you the code project,
        you need to provide answer which is basded on the project. 
        {context}
        """
        custom_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(qa_template), 
            HumanMessagePromptTemplate.from_template("{question}")])
        
        if the_selected_provider != 'localai':
            # add reranker
            if rr:
                compressor = FlashrankRerank()
                compression_retriever = ContextualCompressionRetriever(
                    base_compressor=compressor, base_retriever=self.retriever
                )
                the_retriever = compression_retriever
            else:
                the_retriever = self.retriever

                    
            qa = ConversationalRetrievalChain.from_llm(
                self.model, 
                chain_type="stuff", 
                retriever=the_retriever, 
                condense_question_llm = self.model,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": custom_prompt})
            
            result = qa({"question": query, "chat_history": chat_history})

            self.update_chat_queue((query, result["answer"]))

            # add the search source documents
            docs_strings = document_to_string(result['source_documents'][0])
            # docs_strings = documents_to_string(result['source_documents'])

            if rsd:
                return docs_strings
            else:
                return result['answer']
            
        elif the_selected_provider == 'localai':
            docs = self.retriever.get_relevant_documents(query)

            ds2s = documents_to_string(docs)

            the_question = """   
            the question: {question}"""  

            # build the prompt with string
            combine_strings = qa_template + the_question
            prompt = combine_strings.format(context=ds2s, question=query)
            result = self.model.complete(prompt)
            self.update_chat_queue((query, result.text))
            if rsd:
                return ds2s
            return result.text
        
        else:
            return "Wrong provider!!!"
        
    @cached(cache)
    def restrieval_qa_for_code(self, query):
        config = configparser.ConfigParser()
        config.read(config_path)
        the_selected_provider = config.get('model_providers', 'selected_provider')
        # from datetime import datetime
        code_template = """I want you to act as a Senior Python developer. 
        I will provide you the code project, you provide detailed exaplanation. 
        Human: {input}
        History: {history}
        AI:"""
        code_template_localai = """I want you to act as a Senior Python developer. 
        I will provide you the code project, you provide detailed exaplanation. 
        Human: {input}
        AI:"""
        if the_selected_provider != 'localai':
            PROMPT = PromptTemplate(input_variables=["input", "history"], template=code_template)
            # print("-->", datetime.now())
            conversation = ConversationChain(
                prompt=PROMPT,
                llm=self.model,
            )
            # print("-->", datetime.now())
            code_anaylsis = conversation.predict(input=query)
            return code_anaylsis
        elif the_selected_provider == 'localai':
            prompt = code_template_localai.format(input=query)
            result = self.model.complete(prompt)
            return result.text
        else:
            return "Wrong provider!!!"