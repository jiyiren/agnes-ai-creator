# Agnes AI Creator

[中文文档](README.md)

A self-hosted multimodal web client for [Agnes AI](https://agnes-ai.com/), supporting **AI chat**, **text-to-image / image-to-image**, and **text-to-video / image-to-video**. Generated media can be automatically uploaded to Qiniu Cloud object storage.

> Free Agnes AI models · Vue 3 + FastAPI full stack · Modern glassmorphism UI · Web-based configuration

## Features

| Module | Capabilities |
|--------|--------------|
| **Chat** | Create / switch conversations, streaming responses, Thinking mode, token & latency stats |
| **Image generation** | Text-to-image, single-image edit, multi-image composition; supports `agnes-image-2.0-flash` / `agnes-image-2.1-flash` |
| **Video generation** | Text-to-video, image-to-video, multi-image video, keyframe animation; async background polling |
| **Media storage** | Images / videos auto-uploaded to Qiniu Cloud with persistent history |
| **Web settings** | Configure API Base URL and manage multiple API Keys in the UI — no code edits or restarts |

### Supported models

| Type | Models |
|------|--------|
| Text | `agnes-2.0-flash`, `agnes-1.5-flash` (deprecated) |
| Image | `agnes-image-2.0-flash`, `agnes-image-2.1-flash` |
| Video | `agnes-video-v2.0` |

## Tech stack

- **Frontend**: Vue 3 · Vite · Vue Router · Tailwind CSS
- **Backend**: Python 3 · FastAPI · httpx · APScheduler
- **Database**: SQLite (zero-config, auto-init on first startup)
- **Object storage**: Qiniu Cloud (optional)
- **AI API**: [Agnes AI OpenAI-compatible API](https://agnes-ai.com/doc/overview)

## Requirements

- Python 3.10+
- Node.js 18+
- [Agnes AI API Key](https://platform.agnes-ai.com/) (free to apply; configure in the web **Settings** page)
- Qiniu Cloud object storage (optional, for persisting generated media)

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/agnes-ai-creator.git
cd agnes-ai-creator
```

### 2. Configure backend environment variables (optional)

Qiniu Cloud and database paths are configured via `backend/.env`. **Agnes AI API Keys and Base URL are managed in the web Settings UI** — no need to put them in `.env`.

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `QINIU_ACCESS_KEY` | No | Qiniu Cloud Access Key |
| `QINIU_SECRET_KEY` | No | Qiniu Cloud Secret Key |
| `QINIU_BUCKET` | No | Bucket name |
| `QINIU_DOMAIN` | No | CDN domain, e.g. `https://xxx.example.com` |
| `QINIU_REGION` | No | Storage region, default East China `z0` |
| `DATABASE_PATH` | No | SQLite path, default `./database/aimodel.db` |

> Without Qiniu Cloud, AI generation still works; media may not be persisted to object storage.

### 3. Start the backend

Use a virtual environment to avoid conflicts with system Python packages:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. First-time setup: configure Agnes AI

Open [http://localhost:5173](http://localhost:5173) and go to **Settings** in the sidebar:

1. **API Base URL**: defaults to `https://apihub.agnes-ai.com`; usually no change needed
2. **Add API Key**: enter a label and your key; check “Enable immediately after adding”
3. Add multiple keys and switch the active one anytime

You can then use chat, image, and video generation.

The dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Web settings

| Setting | Count | Description |
|---------|-------|-------------|
| API Base URL | 1 | Global Agnes API endpoint; default `https://apihub.agnes-ai.com` |
| API Key | Multiple | Add, edit, delete; only one key is active at a time |

- Keys are shown masked in the list (e.g. `****5678`)
- Settings are stored in SQLite and take effect immediately — no restart required
- If no key is active, AI requests prompt you to configure one in Settings

## Production deployment

```bash
# Build frontend static assets
cd frontend && npm run build

# Run backend in production mode (preferably inside venv)
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Serve `frontend/dist` with Nginx or another static file server, and reverse-proxy `/api` to the FastAPI service.

## API documentation

After the backend starts, visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger docs.

### Settings endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings/status` | Config status (active key, Base URL, etc.) |
| GET | `/api/settings/base-url` | Get API Base URL |
| PUT | `/api/settings/base-url` | Update API Base URL |
| GET | `/api/settings/api-keys` | List API Keys (masked) |
| POST | `/api/settings/api-keys` | Add API Key |
| PATCH | `/api/settings/api-keys/{id}` | Edit name or key |
| POST | `/api/settings/api-keys/{id}/activate` | Activate a key |
| DELETE | `/api/settings/api-keys/{id}` | Delete a key |

## Database

- Schema SQL: `backend/sql/schema.sql`
- Default database file: `backend/database/aimodel.db`
- Auto-initialized on first startup

Main tables:

| Table | Purpose |
|-------|---------|
| `conversations` / `messages` | Chat history |
| `image_tasks` / `video_tasks` | Image / video generation tasks |
| `uploads` | Upload records |
| `api_keys` | Agnes AI API Key configuration |
| `app_settings` | App-level settings (e.g. Base URL) |

## Qiniu Cloud storage paths

| Type | Path |
|------|------|
| Images | `data/img/` |
| Videos | `data/video/` |
| Documents | `data/document/` |
| Other | `data/other/` |

## Project structure

```
agnes-ai-creator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry & scheduled tasks
│   │   ├── config.py            # Env vars & model config
│   │   ├── database.py          # SQLite connection & init
│   │   ├── schemas.py           # Request / response models
│   │   ├── routers/             # chat / images / videos / settings
│   │   └── services/            # Agnes API, key management, Qiniu, video polling
│   ├── sql/schema.sql           # Database schema SQL
│   ├── database/                # SQLite DB files (gitignored)
│   ├── .env.example             # Environment variable template
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── views/               # Chat, image, video, settings pages
│       ├── api/                 # API client
│       ├── components/          # Shared UI components
│       └── composables/         # Reusable logic
└── _needs/                      # Requirements & design notes
```

## FAQ

### `ModuleNotFoundError: No module named 'apscheduler'`

Backend dependencies are not installed, or you are not using the virtual environment. Run:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

### “Agnes AI API Key not configured”

Open **Settings** in the web UI, add at least one API Key, and click **Enable**.

### Qiniu Cloud errors

Check Qiniu settings in `backend/.env`. If you do not need persistent storage yet, you can ignore these errors — AI generation itself is unaffected.

## Links

- [Agnes AI](https://agnes-ai.com/)
- [Agnes AI Developer Docs](https://agnes-ai.com/doc/overview)
- [Agnes AI Platform (get API Key)](https://platform.agnes-ai.com/)
