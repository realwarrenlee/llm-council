# LLM Council

LLM Council is a local-first web app for asking multiple language models to answer the same prompt, review each other's answers, score the results, and optionally synthesize a final chairman response.

It is intentionally localhost-only. There is no domain setup, deployment config, Docker image, Railway config, or public hosting layer. The browser runs the Next.js UI on `127.0.0.1:3000`; the Python API runs on `127.0.0.1:8000`.

The app still needs outbound internet access when you actually ask models to deliberate, because the current provider is OpenRouter.

## Quick Start

From the project root:

```bash
./start.sh
```

Then open:

```text
http://localhost:3000
```

The startup script:

- starts the backend on port `8000`
- starts the frontend on port `3000`
- installs frontend packages with `npm install` on first run if `node_modules` is missing
- binds the frontend to `127.0.0.1`

Stop both services with `Ctrl+C` in the terminal running `start.sh`.

## First Use

When the app says:

```text
No models available. Add model IDs in Settings.
```

do this:

1. Click **Settings** in the left sidebar.
2. In **API Key**, enter a label such as `Personal` and paste your OpenRouter API key.
3. In **Models**, add the exact OpenRouter model IDs you want to use.
4. Close Settings.
5. Select at least two **Council Members**.
6. Select one **Chairman Model**.
7. Type your question and submit.

Example model IDs:

```text
openai/gpt-4o-mini
anthropic/claude-3.5-sonnet
google/gemini-flash-1.5
meta-llama/llama-3.1-70b-instruct
```

Use model IDs exactly as OpenRouter names them. The app does not fetch the model list anymore; that was removed to keep the UI lean and localhost-focused.

## What It Does

For each deliberation:

1. The frontend sends your task, selected council models, chairman model, and API key to the local backend.
2. The backend creates one role per selected model.
3. Each model answers the task in parallel.
4. If peer review is enabled, models compare each other's answers.
5. The backend computes aggregation scores, including Borda, Bradley-Terry, and ELO where available.
6. If synthesis is enabled, the chairman model writes a final synthesis from the perspectives and reviews.
7. The result is saved to the local SQLite database.

## Architecture

```text
Browser
  |
  | http://localhost:3000
  v
Next.js frontend
  |
  | http://localhost:8000/api/...
  v
FastAPI backend
  |
  | outbound API calls
  v
OpenRouter

SQLite database: ./llm_council.db
```

## Project Structure

```text
.
├── backend/
│   ├── main.py                  # FastAPI app, localhost CORS, route mounting
│   ├── database.py              # SQLite persistence
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── requirements.txt         # Backend Python dependencies
│   └── api/
│       ├── routes.py            # Council roles/templates/run endpoints
│       ├── conversation_routes.py
│       └── websocket.py
├── frontend/
│   ├── app/                     # Next.js app router pages/layout
│   ├── components/              # Sidebar, settings, council controls, UI pieces
│   ├── lib/api.ts               # Frontend API client for the local backend
│   ├── package.json
│   └── tsconfig.json
├── src/llm_council/
│   ├── council.py               # Core orchestration engine
│   ├── config.py                # Council configuration
│   ├── peer_review_orchestrator.py
│   ├── analysis/                # Aggregation/scoring methods
│   ├── roles/                   # Role model and registry
│   └── providers/               # Provider abstractions
├── start.sh                     # Local startup script
├── pyproject.toml               # Python package metadata
└── README.md
```

## Frontend

The frontend is a Next.js app. Important files:

- `frontend/app/page.tsx`: main deliberation screen
- `frontend/app/client-layout.tsx`: app shell and sidebar wiring
- `frontend/components/settings-popover.tsx`: API key and model ID setup
- `frontend/components/council/model-selector.tsx`: council member selector
- `frontend/components/council/chairman-selector.tsx`: chairman selector
- `frontend/lib/api.ts`: typed client for backend calls

Settings are stored in browser `localStorage`:

- `llm-council-api-keys`
- `llm-council-available-models`
- `llm-council-theme`
- `llm-council-notifications`

That means keys and model lists are per-browser, not stored in the SQLite database.

## Backend

The backend is FastAPI.

Important routes:

```text
GET  /health
GET  /api/council/roles
GET  /api/council/templates
POST /api/council/run
GET  /api/conversations
GET  /api/conversations/{id}
PATCH /api/conversations/{id}
DELETE /api/conversations/{id}
POST /api/conversations/save-council-output
```

FastAPI docs and OpenAPI routes are disabled in this localhost cleanup.

The active deliberation endpoint is:

```text
POST /api/council/run?api_key=...
```

The request body contains the task, selected model-backed roles, and options. The API key is passed from the browser at run time and used for OpenRouter calls.

## Local Data

Saved conversations live in:

```text
./llm_council.db
```

This is a local SQLite database. Delete it if you want to clear saved conversations.

Generated files ignored by git include:

- `node_modules/`
- `.next/`
- `__pycache__/`
- `*.tsbuildinfo`
- `.env`
- `llm_council.db`

## Manual Commands

Backend:

```bash
pip install -e .
pip install -r backend/requirements.txt
python3 backend/main.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Type checks:

```bash
cd frontend
npx tsc --noEmit
```

Lint:

```bash
cd frontend
npm run lint
```

Python compile check:

```bash
python3 -m py_compile backend/main.py backend/api/routes.py backend/api/conversation_routes.py backend/api/websocket.py
```

## Requirements

- Python 3.10+
- Node 18+
- npm
- `lsof` for the startup script's port checks
- OpenRouter API key for real model calls

The frontend currently uses Next.js 15 so it works with Node 18. Newer Next.js releases may require Node 20+.

## Troubleshooting

### `next: not found`

Install frontend dependencies:

```bash
cd frontend
npm install
```

Then rerun:

```bash
cd ..
./start.sh
```

### No Models Available

Add model IDs manually in **Settings > Models**. The app no longer fetches OpenRouter's model catalog from the browser.

### No API Key Configured

Add a key in **Settings > API Key**. The first saved key is used when running a deliberation.

### Port Already Running

If port `3000` or `8000` is already in use, stop the existing process or change the relevant script/config.

Useful checks:

```bash
lsof -i :3000
lsof -i :8000
```

### Backend Starts But Model Calls Fail

Check:

- the OpenRouter API key is valid
- the model ID is valid
- the machine has outbound internet access
- the OpenRouter account has access or credits for that model

## Design Notes

This app now favors a small local workflow:

- no hosted deployment files
- no public domain assumptions
- no browser-side OpenRouter model catalog page
- model IDs are explicit user configuration
- conversations are local SQLite records

The only external network dependency during normal use is the outbound request to OpenRouter when a deliberation runs.
