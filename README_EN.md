# Agnes AI Creator

[中文文档](README.md)

A self-hosted multimodal web client for [Agnes AI](https://agnes-ai.com/), supporting **AI chat**, **text-to-image / image-to-image**, and **text-to-video / image-to-video**. Generated media is automatically uploaded to Qiniu Cloud object storage.

> Free Agnes AI models · Vue 3 + FastAPI full stack · Modern glassmorphism UI

## Features

| Module | Capabilities |
|--------|--------------|
| **Chat** | Create / switch conversations, streaming responses, Thinking mode, token & latency stats |
| **Image generation** | Text-to-image, single-image edit, multi-image composition; supports `agnes-image-2.0-flash` / `agnes-image-2.1-flash` |
| **Video generation** | Text-to-video, image-to-video, multi-image video, keyframe animation; async background polling |
| **Media storage** | Images / videos auto-uploaded to Qiniu Cloud with persistent history |

### Supported models

| Type | Models |
|------|--------|
| Text | `agnes-2.0-flash` |
| Image | `agnes-image-2.0-flash`, `agnes-image-2.1-flash` |
| Video | `agnes-video-v2.0` |

## Tech stack

- **Frontend**: Vue 3 · Vite · Vue Router · Tailwind CSS
- **Backend**: Python 3 · FastAPI · httpx · APScheduler
- **Database**: SQLite (zero-config, auto-init on first startup)
- **Object storage**: Qiniu Cloud
- **AI API**: [Agnes AI OpenAI-compatible API](https://agnes-ai.com/doc/overview)

## Requirements

- Python 3.10+
- Node.js 18+
- [Agnes AI API Key](https://platform.agnes-ai.com/) (free to apply)
- Qiniu Cloud object storage (optional but recommended for saving generated media)

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/agnes-ai-creator.git
cd agnes-ai-creator
```

### 2. Configure environment variables

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

| Variable | Description |
|----------|-------------|
| `AGNES_API_KEY` | Agnes AI API Key (required) |
| `AGNES_BASE_URL` | API base URL, default `https://apihub.agnes-ai.com` |
| `QINIU_ACCESS_KEY` | Qiniu Cloud Access Key |
| `QINIU_SECRET_KEY` | Qiniu Cloud Secret Key |
| `QINIU_BUCKET` | Bucket name |
| `QINIU_DOMAIN` | CDN domain, e.g. `https://xxx.example.com` |
| `QINIU_REGION` | Storage region, e.g. East China `z0` |
| `DATABASE_PATH` | SQLite path, default `./database/aimodel.db` |

### 3. Start the backend

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

Open [http://localhost:5173](http://localhost:5173) in your browser.

The dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Production deployment

```bash
# Build frontend static assets
cd frontend && npm run build

# Run backend in production mode (example)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Serve `frontend/dist` with Nginx or another static file server, and reverse-proxy `/api` to the FastAPI service.

## API documentation

After the backend starts, visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger docs.

## Database

- Schema SQL: `backend/sql/schema.sql`
- Default database file: `backend/database/aimodel.db`
- Auto-initialized on first startup; includes tables for conversations, messages, image tasks, video tasks, uploads, etc.

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
│   │   ├── routers/             # chat / images / videos routes
│   │   └── services/            # Agnes API, Qiniu, video polling
│   ├── sql/schema.sql           # Database schema SQL
│   ├── database/                # SQLite DB files (gitignored)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── views/               # Chat, image, video pages
│       ├── api/                 # API client
│       └── components/          # Shared UI components
└── _needs/                      # Requirements & design notes
```

## Links

- [Agnes AI](https://agnes-ai.com/)
- [Agnes AI Developer Docs](https://agnes-ai.com/doc/overview)
- [Agnes AI Platform (get API Key)](https://platform.agnes-ai.com/)
