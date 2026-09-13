# Running QA-Pilot

The runtime has been refreshed for Python 3.13 and LangChain 1.x. The existing
retrieval chains use `langchain-classic`; Ollama and Chroma use their dedicated
integration packages. The built Svelte UI is served by FastAPI on the same port.

## Runtime configuration

Use `config/config.local.ini` for database credentials, model selection and
Ollama endpoints. This file is ignored by Git. On first startup, the application
copies the tracked defaults from `config/config.ini` if no local config exists.
Settings changes are saved only to the local config.

For a local installation, the UI is available at `http://localhost:5000` and
Ollama typically listens at `http://localhost:11434`. Configure the endpoints
for your own environment. Pull a chat model and `nomic-embed-text` on the chosen
Ollama host, then select Ollama for both chat and embeddings in the local config.
The Ollama host must remain available for repository imports and answers.

After installing the optional systemd service:

```bash
sudo systemctl status qa-pilot --no-pager
sudo systemctl restart qa-pilot
sudo journalctl -u qa-pilot -n 100 --no-pager
curl http://127.0.0.1:5000/healthz
```

PostgreSQL stores sessions and messages;
`projects/` stores source checkouts and `VectorStore/` stores repository indexes.

## Rebuild after editing

```bash
# Run from the repository root
.venv/bin/python -m pip install -r requirements.lock.txt
cd svelte-app
npm ci
npm run build
cd ..
go build -o parser parser.go
sudo systemctl restart qa-pilot
```

`requirements.lock.txt` and `svelte-app/package-lock.json` record the tested
dependency versions. `requirements.txt` declares direct runtime dependencies.
Optional model integrations are listed in `requirements-models.txt`: install
only the integrations you intend to use. FlashRank is optional for `rr:` queries.
Hugging Face embeddings default to CPU; set `QA_PILOT_EMBEDDING_DEVICE` to change it.

## First installation elsewhere

Install Python 3.11 or later (tested on 3.13), Node.js 20, Go and PostgreSQL.
Create a database owned by the configured application user. Copy
`config/config.ini` to `config/config.local.ini`, restrict its permissions with
`chmod 600 config/config.local.ini`, and edit the local copy with your database
connection settings and Ollama endpoint. Never put real credentials in the
tracked defaults.
Select Ollama as the embedding provider if no local embedding SDK is installed.
Pull `nomic-embed-text` on the chosen Ollama host if it is not already installed.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
cd svelte-app
npm ci
npm run build
cd ..
go build -o parser parser.go
.venv/bin/python qa_pilot_run.py
```

For a persistent deployment, adjust the user and absolute paths in
`deploy/qa-pilot.service`, install it under `/etc/systemd/system/`, then run
`sudo systemctl daemon-reload` and `sudo systemctl enable --now qa-pilot`.

For frontend development, `npm run dev` serves port 5001 and automatically uses
port 5000 on the browser's current host for API requests.

## Scope

This update restores the original application. Anchored discussion threads have
not been implemented. Existing retrieval, conversation-memory and codegraph
accuracy limitations still need their own follow-up work. The app retains its
original unauthenticated, single-user design.
