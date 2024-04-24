import streamlit as st
import time
from helper import (
    scan_vectorstore_for_repos, 
    DataHandler, 
    project_dir,
    save_session, 
    load_session,
    update_repo_urls,
    load_repo_urls, 
    remove_directory, 
    remove_repo_from_json,
    update_selected_provider,
    update_selected_model,
)
import os
import zipfile
import lzma
import tarfile
import configparser
from dotenv import load_dotenv

# select the llm model
# define the config path
config_path = os.path.join('config', 'config.ini')

# read the model list from config.ini
config = configparser.ConfigParser()
config.read(config_path)
selected_provider = config.get('model_providers', 'selected_provider')
model_section = f"{selected_provider}_llm_models"
selected_model = config.get(model_section, 'selected_model')

# update the provider
provider_list = config.get('model_providers', 'provider_list').split(', ')
user_selected_provider = st.sidebar.selectbox('Select a model provider:', provider_list, index=provider_list.index(selected_provider))
# check openai key exist
if user_selected_provider == 'openai':
    load_dotenv()
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        st.warning("OPENAI_API_KEY is missing in the env variable file. Please add it to use OpenAI services.")

if user_selected_provider != selected_provider:
    update_selected_provider(user_selected_provider)
    st.rerun()

# update the model
model_list = config.get(model_section, 'model_list').split(', ')
user_selected_model = st.sidebar.selectbox('Select a LLM model:', model_list, index=model_list.index(selected_model))
if user_selected_model != selected_model:
    update_selected_model(user_selected_model)

# scan the repos from repo_info.json
existing_repos = scan_vectorstore_for_repos()

# show the title, info, warning
st.title("QA-Pilot")
st.info("Analyze the GitHub repository or compressed file(e.g  sosreport) with offline LLM.")
st.warning("NOTE: Do not use url or upload at the same time!")

# reset the initial state
if 'init' not in st.session_state:
    st.session_state.update({
        'init': True,  
        'git_repo_url': "",
        'messages': [],
        'file_uploaded': False,  
    })

# reset the state when click New Source
if st.sidebar.button("New Source Button"):
    st.session_state.update({
        'file_uploaded': False,
        'git_repo_url': "",
        'messages': [],
        'init': True,
    })


# initial git_repo_url if not in session_state
if 'git_repo_url' not in st.session_state:
    st.session_state['git_repo_url'] = ""

# show the repos in the left bar
if 'repos' not in st.session_state:
    st.session_state['repos'] = existing_repos

if 'repo_urls' not in st.session_state:
    st.session_state['repo_urls'] = load_repo_urls()


# set the left sidebar format(st.sidebar.button(repo))
def local_css(file_name):
    # with open(file_name) as f:
    with open(file_name, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Load the style for the sidebar
local_css("style.css")


# specify the repo when switch the sidebar
def select_repo(repo):
    print("Entering select_repo with:", repo)  
    # save the session if there is a history and selected the repo
    if 'current_repo' in st.session_state and 'messages' in st.session_state:
        if st.session_state['messages']:  # check the message 
            save_session(st.session_state['messages'], st.session_state['current_repo'])

            print("Saved session for", st.session_state['current_repo'])
    
    # load the mapping from the file
    repo_urls = load_repo_urls()
    
    # get the repo url and update the url in the input
    repo_url = repo_urls.get(repo, '')
    st.session_state['git_repo_url'] = repo_url

    print("Setting current_repo as:", repo)  # debug
    print("Updated git_repo_url:", st.session_state['git_repo_url'])
    # update the current repo
    st.session_state['current_repo'] = repo
    
    # load the repo message hsitory
    st.session_state['messages'] = load_session(repo)
    # st.session_state['messages'] = db_helper.load_session(repo)
    print("Loaded session for", repo)
    print("Exiting select_repo") 


# design the sidebar for two columns, repo button and remove button
for repo in st.session_state.get('repos', []):
    # set the width ratio
    col1, col2 = st.sidebar.columns([0.8, 0.2])  
    with col1:  # left side for repo project
        if st.button(repo):
            st.session_state['init'] = False
            select_repo(repo)
    with col2:  # right side for the remove button
        if st.button('❌', key=f'delete_{repo}'):
            remove_repo_from_json(repo)
            session_dir =  os.path.join('sessions', f'{repo}.json')
            try:
                os.remove(session_dir)  # remove .json file
            except OSError as e:
                print(f"Error: {e.strerror}")  

            if repo in st.session_state['repos']:
                st.session_state['repos'].remove(repo)
                # reset and del the related session state
                if 'current_repo' in st.session_state and st.session_state['current_repo'] == repo:
                    del st.session_state['current_repo']
                # reset the data
                st.session_state['git_repo_url'] = ""
                st.session_state['messages'] = []    
            # del the repo url state
            if repo in st.session_state['repo_urls']:
                del st.session_state['repo_urls'][repo]

            # remove the project directory
            remove_project = os.path.join(project_dir, repo)
            remove_directory(remove_project)
            update_repo_urls(repo, action="delete")
            st.rerun()  # update the UI


# generate the words one by one on the UI
def response_generator(response_text):
    for char in response_text:
        yield char 
        time.sleep(0.01)


def init_or_load_db(data_handler):
    # init state will not load the db
    if st.session_state.get('init', True):
        return  
    if data_handler.db_exists():
        # db exist, means load it before
        try:
            data_handler.git_clone_repo()  # check for the load project
            st.write("===> Loading the existing repo db data...")
            data_handler.load_into_db()
            st.success("Repo data loaded. Ready to take your questions.")
            # update repo_urls mapping
            st.session_state['repo_urls'][data_handler.repo_name] = data_handler.git_url
        except Exception as e:
            st.error(f"Failed to load existing repo data: {e}")
    else:
        try:
            st.write("===> Processing the repo...")
            data_handler.git_clone_repo()
            st.write("===> Repo has been cloned...")
            st.write("===> Loading the repo db data...")
            data_handler.load_into_db()
            st.success("Repo data processed and loaded. Ready to take your questions.")
            st.session_state['repos'] = scan_vectorstore_for_repos()
            # update repo_urls
            st.session_state['repo_urls'][data_handler.repo_name] = data_handler.git_url
        except Exception as e:
            st.error(f"Failed to process the repo: {e}")

    st.session_state['current_repo'] = data_handler.repo_name
    st.session_state['repos'] = scan_vectorstore_for_repos()
    st.session_state['data_loaded'] = True


def chat_message_func():
    if st.session_state.get('init', True):
        return  # not load if init state for startup and New Source
     # Ensure 'messages' is initialized in session state
    if "messages" not in st.session_state:
        st.session_state['messages'] = []

    # Display chat messages from history on app rerun
    for message in st.session_state.get('messages', []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # set the prompt
    if prompt := st.chat_input("Enter the question here."):
        # update to chat message history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # show the message in the chat
        with st.chat_message("user"):
            st.markdown(prompt)
        # get the answer from the chain
        qa_answer = data_handler.retrieval_qa(prompt)
        with st.chat_message("assistant"):
            # streaming output
            st.write_stream(response_generator(qa_answer))
        # update to chat message history again with the answer
        st.session_state.messages.append({"role": "assistant", "content": qa_answer})

        st.write("Current Repo:", st.session_state.get('current_repo', 'Not set'))
        if 'current_repo' in st.session_state:
            # save the session history
            save_session(st.session_state['messages'], st.session_state['current_repo'])


# handle the file path format issue, almost in Windows
def safe_extract_tar(tar_ref, path):
    for member in tar_ref.getmembers():
        # check and modify the file name to avoid the Windows issue
        safe_name = member.name.replace(":", "_").replace("?", "_").replace("*", "_")
        if safe_name != member.name:
            member.name = safe_name
        # extract from the modification
        tar_ref.extract(member, path=path)


# show the upload file input, when file_uploaded is False
if not st.session_state.get('file_uploaded', False):
    uploaded_file = st.file_uploader("Upload a zip or xz(e.g. sosreport) file of the repository", type=['zip', 'xz'])
    # set the process button after upload
    if uploaded_file is not None and st.button('Process uploaded file'):
        st.session_state['file_uploaded'] = True  # already uploaded
        file_extension = uploaded_file.name.split('.')[-1]
        uploaded_repo_name = uploaded_file.name.rsplit('.', 1)[0]
        uploaded_repo_path = os.path.join(project_dir, uploaded_repo_name)

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        if os.path.exists(uploaded_repo_path):
            remove_directory(uploaded_repo_path)

        # create the directory to store the project
        os.makedirs(uploaded_repo_path)

        # uncompress the different file type
        if file_extension == 'zip':
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(uploaded_repo_path)
        elif file_extension == 'xz':
            # .xz file with tarfile
            with lzma.open(uploaded_file) as f:
                with tarfile.open(fileobj=f) as tar_ref:
                    safe_extract_tar(tar_ref, uploaded_repo_path)
        else:
            st.error("Unsupported file type.")

        # pseudo URL，use qa_pilot.app for the uploaded file
        # it can easy to use the same handle procedure with git url
        pseudo_git_url = f"https://qa_pilot.app/UploadedRepo/{uploaded_repo_name}.git"
        
        # update session_state git_repo_url to pseudo URL
        st.session_state['git_repo_url'] = pseudo_git_url

        st.success("File processed successfully!")
else:
    st.success("File uploaded successfully!")

# git url input
git_repo = st.text_input("Enter the public GitHub repository url[It might show the fake url for uploaded file, please ignore it!]:", value=st.session_state['git_repo_url'], key='git_repo_url')

# check whether empty url
if git_repo.strip():
    # if a url, set the init to be False, need to load the db
    print("url---> ", st.session_state['git_repo_url'])
    st.session_state['init'] = False

# input the url and select the repo session
if 'current_repo' in st.session_state or git_repo:
    data_handler = DataHandler(git_repo or st.session_state['current_repo'])
    init_or_load_db(data_handler)
    chat_message_func()
