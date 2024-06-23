from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import configparser
import os
from dotenv import load_dotenv, set_key
from utils.helper import (
    DataHandler,
    remove_directory,
    encode_kwargs,
    model_kwargs,
)
import psycopg2
from psycopg2 import sql
import ast 
from qa_model_apis import (
    get_chat_model,
    get_embedding_model,
)
from utils.codegraph import (
    parse_python_code,
    read_current_repo_path,
    build_file_tree,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config_path = os.path.join('config', 'config.ini')
config = configparser.ConfigParser()
config.read(config_path)

templates = Jinja2Templates(directory="templates")

DB_NAME = config['database']['db_name']
DB_USER = config['database']['db_user']
DB_PASSWORD = config['database']['db_password']
DB_HOST = config['database']['db_host']
DB_PORT = config['database']['db_port']

# for analyse code
current_session = None

current_model_info = {
    "provider": None,
    "model": None,
    "eb_provider": None,
    "eb_model": None,
    "chat_model": None,
    "embedding_model": None
}

def init_db():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id BIGINT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL
        )
    ''')
    conn.commit()
    # fix the first time to set the session
    cursor.execute('SELECT id, name, url FROM sessions LIMIT 1')
    session = cursor.fetchone()
    if session:
        global current_session
        current_session = {'id': session[0], 'name': session[1], 'url': session[2]}
        print("Default session set to:", current_session)
    conn.close()

def load_models_if_needed():
    selected_provider = config.get('model_providers', 'selected_provider')
    selected_model = config.get(f"{selected_provider}_llm_models", 'selected_model')
    eb_selected_provider = config.get('embedding_model_providers', 'selected_provider')
    eb_selected_model = config.get(f"{eb_selected_provider}_embedding_models", 'selected_model')
    
    if (current_model_info["provider"] != selected_provider or 
        current_model_info["model"] != selected_model or 
        current_model_info["eb_provider"] != eb_selected_provider or 
        current_model_info["eb_model"] != eb_selected_model):

        current_model_info["provider"] = selected_provider
        current_model_info["model"] = selected_model
        current_model_info["eb_provider"] = eb_selected_provider
        current_model_info["eb_model"] = eb_selected_model
        current_model_info["chat_model"] = get_chat_model(selected_provider, selected_model)
        current_model_info["embedding_model"] = get_embedding_model(eb_selected_provider, eb_selected_model, model_kwargs, encode_kwargs)
        print(f"Loaded new models: provider={selected_provider}, model={selected_model}")
    
    print(f"Loaded models: provider={selected_provider}, model={selected_model}")

def create_message_table(session_id):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()
    table_name = sql.Identifier(f'session_{session_id}')
    cursor.execute(sql.SQL('''
        CREATE TABLE IF NOT EXISTS {} (
            id BIGSERIAL PRIMARY KEY,
            sender TEXT NOT NULL,
            text TEXT NOT NULL
        )
    ''').format(table_name))
    conn.commit()
    conn.close()

init_db()

def load_config():
    config.read(config_path)
    return config

@app.get('/get_config')
async def get_config():
    config = load_config()
    config_dict = {section: dict(config.items(section)) for section in config.sections()}
    return JSONResponse(content=config_dict)

@app.post('/save_config')
async def save_config(request: Request):
    new_config = await request.json()
    config = load_config()
    for section, section_values in new_config.items():
        if not config.has_section(section):
            config.add_section(section)
        for key, value in section_values.items():
            config.set(section, key, value)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    return JSONResponse(content={"message": "Configuration saved successfully!"})

@app.post('/update_provider')
async def update_provider(request: Request):
    data = await request.json()
    selected_provider = data.get('selected_provider')
    config.set('model_providers', 'selected_provider', selected_provider)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    return JSONResponse(content={"message": "Provider updated successfully!"})

@app.post('/update_model')
async def update_model(request: Request):
    data = await request.json()
    selected_provider = data.get('selected_provider')
    selected_model = data.get('selected_model')
    config.set(f'{selected_provider}_llm_models', 'selected_model', selected_model)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    return JSONResponse(content={"message": "Model updated successfully!"})

@app.post('/load_repo')
async def load_repo(request: Request):
    data = await request.json()
    git_url = data.get('git_url')
    if not git_url:
        raise HTTPException(status_code=400, detail="Git URL is required")

    load_models_if_needed()
    chat_model = current_model_info["chat_model"]
    embedding_model = current_model_info["embedding_model"]
    data_handler = DataHandler(git_url, chat_model, embedding_model)
    try:
        data_handler.git_clone_repo()
        data_handler.load_into_db()
        return JSONResponse(content={"message": f"Repository {git_url} loaded successfully!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/chat')
async def chat(request: Request):
    data = await request.json()
    load_models_if_needed()
    chat_model = current_model_info["chat_model"]
    embedding_model = current_model_info["embedding_model"]

    user_message = data.get('message')
    current_repo = data.get('current_repo')
    session_id = data.get('session_id')
    if not user_message or not current_repo or not session_id:
        raise HTTPException(status_code=400, detail="Message, current_repo and session_id are required")

    try:
        data_handler = DataHandler(current_repo, chat_model, embedding_model)
        data_handler.load_into_db()
        rsd = False
        rr = False

        # return source documents
        if user_message.startswith('rsd:'):
            user_message = user_message[4:].strip()
            rsd = True
        # use reranker
        elif user_message.startswith('rr:'):
            user_message = user_message[3:].strip()
            rr = True
        bot_response = data_handler.retrieval_qa(user_message, rsd=rsd, rr=rr)

        # Save user message and bot response to the session table
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        table_name = sql.Identifier(f'session_{session_id}')
        cursor.execute(sql.SQL('INSERT INTO {} (sender, text) VALUES (%s, %s)').format(table_name), ('You', user_message))
        cursor.execute(sql.SQL('INSERT INTO {} (sender, text) VALUES (%s, %s)').format(table_name), ('QA-Pilot', bot_response))
        conn.commit()
        conn.close()

        return JSONResponse(content={"response": bot_response})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/sessions')
async def get_sessions():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, url FROM sessions')
    sessions = [{'id': row[0], 'name': row[1], 'url': row[2]} for row in cursor.fetchall()]
    conn.close()
    print(f"Fetched sessions from DB: {sessions}")
    return JSONResponse(content=sessions)

@app.post('/sessions')
async def save_sessions(request: Request):
    sessions = await request.json()
    print(f"Received sessions to save: {sessions}")
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()
    for session in sessions:
        cursor.execute('INSERT INTO sessions (id, name, url) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, url = EXCLUDED.url',
                       (session['id'], session['name'], session['url']))
        create_message_table(session['id'])
    conn.commit()
    conn.close()
    print("Saved sessions to DB")
    return JSONResponse(content={"message": "Sessions saved successfully!"})

@app.get('/messages/{session_id}')
async def get_messages(session_id: int):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()
    table_name = sql.Identifier(f'session_{session_id}')
    cursor.execute(sql.SQL('SELECT sender, text FROM {}').format(table_name))
    messages = [{'sender': row[0], 'text': row[1]} for row in cursor.fetchall()]
    conn.close()
    print(f"Fetched messages from session {session_id}")
    return JSONResponse(content=messages)

@app.post('/update_current_session')
async def update_current_session(request: Request):
    global current_session
    current_session = await request.json()
    return JSONResponse(content={"message": "Current session updated successfully!"})

@app.delete('/sessions/{session_id}')
async def delete_session(session_id: int):
    print(f"Deleting session with ID: {session_id}")

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT name FROM sessions WHERE id = %s', (session_id,))
        session = cursor.fetchone()
        if session:
            session_name = session[0]
            print("anem", session_name)
        cursor.execute('DELETE FROM sessions WHERE id = %s', (session_id,))
        conn.commit()
        cursor.execute(sql.SQL('DROP TABLE IF EXISTS {}').format(sql.Identifier(f'session_{session_id}')))
        conn.commit()
        # remove the git clone project
        remove_project_path = os.path.join("projects", session_name)
        remove_directory(remove_project_path)
        print("Session deleted successfully")
        return JSONResponse(content={"message": "Session deleted successfully!"})
    except Exception as e:
        print(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# api key handling functions
@app.post('/check_api_key')
async def check_api_key(request: Request):
    data = await request.json()
    provider = data.get('provider')
    key_var = f"{provider.upper()}_API_KEY"
    
    load_dotenv()
    api_key = os.getenv(key_var)
    
    return JSONResponse(content={'exists': bool(api_key)})

@app.post('/save_api_key')
async def save_api_key(request: Request):
    data = await request.json()
    provider = data.get('provider')
    api_key = data.get('api_key')
    key_var = f"{provider.upper()}_API_KEY"
    
    dotenv_path = '.env'
    set_key(dotenv_path, key_var, api_key)
    load_dotenv()
    
    return JSONResponse(content={'message': 'API Key saved successfully!'})


# hanlde llamacpp models(list/upload/delete)
@app.get('/llamacpp_models')
async def list_llamacpp_models():
    upload_dir = "llamacpp_models"
    if not os.path.exists(upload_dir):
        return JSONResponse(content=[])
    models = os.listdir(upload_dir)
    return JSONResponse(content=models)


@app.post('/llamacpp_models', status_code=201)
async def upload_llamacpp_model(file: UploadFile = File(...), chunk: int = Form(...), totalChunks: int = Form(...)):
    try:
        upload_dir = "llamacpp_models"
        os.makedirs(upload_dir, exist_ok=True)
        chunk_dir = os.path.join(upload_dir, "chunks")
        os.makedirs(chunk_dir, exist_ok=True)
        chunk_file_path = os.path.join(chunk_dir, f"{file.filename}.part{chunk}")

        with open(chunk_file_path, "wb") as f:
            f.write(await file.read())

        # Check if all chunks are uploaded
        if len(os.listdir(chunk_dir)) == totalChunks:
            final_file_path = os.path.join(upload_dir, file.filename)
            with open(final_file_path, "wb") as final_file:
                for i in range(totalChunks):
                    chunk_file_path = os.path.join(chunk_dir, f"{file.filename}.part{i}")
                    with open(chunk_file_path, "rb") as chunk_file:
                        final_file.write(chunk_file.read())
                    os.remove(chunk_file_path)
            os.rmdir(chunk_dir)  # Remove the chunks directory

        return JSONResponse(content={"message": "Chunk uploaded successfully!"})
    except Exception as e:
        print(f"Error uploading model: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload chunk")
    

@app.delete('/llamacpp_models/{model_name}')
async def delete_llamacpp_model(model_name: str):
    file_path = os.path.join("llamacpp_models", model_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        return JSONResponse(content={"message": "Model deleted successfully!"})
    else:
        raise HTTPException(status_code=404, detail="Model not found")

# handle prompt templates
@app.get('/get_prompt_templates')
async def get_prompt_templates():
    prompt_templates_path = os.path.join('config', 'prompt_templates.ini')
    templates_config = configparser.ConfigParser()

    if not os.path.exists(prompt_templates_path):
        return JSONResponse(content={})

    with open(prompt_templates_path, 'r', encoding='utf-8') as file:
        file_content = file.read()
        # Ensure the content has a section header
        if '[qa_prompt_templates]' not in file_content:
            file_content = '[qa_prompt_templates]\n' + file_content

    try:
        templates_config.read_string(file_content)
    except configparser.ParsingError as e:
        print(f"Error parsing config: {e}")
        raise HTTPException(status_code=500, detail="Error parsing prompt templates")

    templates = {k: v.replace('\\n', '\n') for k, v in templates_config.items('qa_prompt_templates')}
    return JSONResponse(content=templates)


@app.post('/delete_prompt_template')
async def delete_prompt_template(request: Request):
    data = await request.json()
    template_name = data.get('template_name')

    prompt_templates_path = os.path.join('config', 'prompt_templates.ini')
    templates_config = configparser.ConfigParser()
    templates_config.read(prompt_templates_path)

    if template_name in templates_config['qa_prompt_templates']:
        templates_config.remove_option('qa_prompt_templates', template_name)
        with open(prompt_templates_path, 'w', encoding='utf-8') as configfile:
            templates_config.write(configfile)
        return JSONResponse(content={"message": "Template deleted successfully!"})
    else:
        raise HTTPException(status_code=404, detail="Template not found")


@app.post('/save_prompt_templates')
async def save_prompt_templates(request: Request):
    new_templates = await request.json()
    prompt_templates_path = os.path.join('config', 'prompt_templates.ini')
    templates_config = configparser.ConfigParser()
    templates_config['qa_prompt_templates'] = {k: v.replace('\n', '\\n') for k, v in new_templates.items()}

    with open(prompt_templates_path, 'w', encoding='utf-8') as configfile:
        templates_config.write(configfile)
    return JSONResponse(content={"message": "Templates saved successfully!"})

#############################codegraph############################
@app.get('/codegraph')
async def codegraph_home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.get('/data')
async def data(filepath: str):
    code_data = parse_python_code(filepath)  # Ensure the path points to your Python code file
    return JSONResponse(content=code_data)

@app.get('/directory')
async def directory():
    current_repo_path = read_current_repo_path(current_session)
    if current_repo_path is None:
        raise HTTPException(status_code=404, detail="Repository path not set or not found")
    dir_tree = build_file_tree(current_repo_path)  # Ensure the path points to your code directory
    return JSONResponse(content=dir_tree)

@app.post('/analyze')
async def analyze(request: Request):
    data = await request.json()
    load_models_if_needed()
    chat_model = current_model_info["chat_model"]
    embedding_model = current_model_info["embedding_model"]
    code = data.get('code', '')
    # send the code to LLM
    data_handler = DataHandler(git_url='', chat_model=chat_model, embedding_model=embedding_model)
    code_analysis = data_handler.restrieval_qa_for_code(code)
    return JSONResponse(content={'analysis': code_analysis})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="debug")
