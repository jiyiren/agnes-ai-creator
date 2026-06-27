<h4 align="right"><strong>English</strong> | <a href="README.md">简体中文</a></h4>
<p align="center">
  <img src="docs/images/logo.jpg" width="138" alt="Agnes AI Creator" style="border-radius: 28px;"/>
</p>
<h1 align="center">Agnes AI Creator</h1>
<p align="center"><strong>A self-hosted multimodal web client powered by free Agnes AI models</strong></p>
<p align="center">AI chat · Text-to-image / image edit · Text-to-video / image-to-video · Qiniu Cloud storage (optional)</p>
<div align="center">
  <a href="./LICENSE" target="_blank">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square"></a>
  <a href="https://platform.agnes-ai.com/" target="_blank">
  <img alt="agnes ai" src="https://img.shields.io/badge/platform-Agnes%20AI-ff6b3d?style=flat-square"></a>
  <a href="https://agnes-ai.com/doc/overview" target="_blank">
  <img alt="models" src="https://img.shields.io/badge/models-text%20%7C%20image%20%7C%20video-black?style=flat-square"></a>
  <a href="https://www.python.org/" target="_blank">
  <img alt="python" src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="https://vuejs.org/" target="_blank">
  <img alt="vue" src="https://img.shields.io/badge/vue-3.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white"></a>
  <a href="https://fastapi.tiangolo.com/" target="_blank">
  <img alt="fastapi" src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white"></a>
  <a href="https://vitejs.dev/" target="_blank">
  <img alt="vite" src="https://img.shields.io/badge/vite-6.0-646CFF?style=flat-square&logo=vite&logoColor=white"></a>
  <a href="https://x.com/haiqushe" target="_blank">
  <img alt="follow" src="https://img.shields.io/badge/follow-@haiqushe-red?style=flat-square"></a>
  <a href="https://dz.haiqushe.com/" target="_blank">
  <img alt="haiqushe" src="https://img.shields.io/badge/海趣社-Site%20Nav-blueviolet?style=flat-square"></a>
</div>

> Free Agnes AI models — [sign up on the platform](https://platform.agnes-ai.com/), add your API key in Settings, and start creating.

<p align="center">
  <img src="docs/images/ai-img-gen.png" alt="Agnes AI Creator — streaming AI chat" width="920"/>
</p>

<p align="center">
  <strong>Chat · Images · Video — all in one beautiful UI</strong><br/>
  Free Agnes AI models &nbsp;·&nbsp; Vue 3 + FastAPI &nbsp;·&nbsp; Glassmorphism design &nbsp;·&nbsp; Zero-code web settings
</p>

## Screenshots

<table cellpadding="6">
  <tr>
    <td width="50%" align="center" valign="top">
      <img src="docs/images/ai-img-gen.png" alt="Image generation" width="100%" style="display:block;margin-bottom:6px;border-radius:8px;"/>
      <strong>🎨 Image generation</strong><br/>
      <span style="font-size:13px">Text-to-image · Edit · Multi-image compose · History replay</span>
    </td>
    <td width="50%" align="center" valign="top">
      <img src="docs/images/ai-video-gen.png" alt="Video generation" width="100%" style="display:block;margin-bottom:6px;border-radius:8px;"/>
      <strong>🎬 Video generation</strong><br/>
      <span style="font-size:13px">Text/image-to-video · Keyframe animation · Player · Qiniu upload</span>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <img src="docs/images/ai-chat.png" alt="AI chat" width="100%" style="display:block;margin-bottom:6px;border-radius:8px;"/>
      <strong>💬 AI chat</strong><br/>
      <span style="font-size:13px">Streaming · Thinking mode · Token stats · Multi-conversation</span>
    </td>
    <td width="50%" align="center" valign="top">
      <img src="docs/images/settings.png" alt="Web settings" width="100%" style="display:block;margin-bottom:6px;border-radius:8px;"/>
      <strong>⚙️ Web settings</strong><br/>
      <span style="font-size:13px">API Key / Base URL in browser · Multi-key · Instant effect</span>
    </td>
  </tr>
</table>

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
git clone https://github.com/jiyiren/agnes-ai-creator.git
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

<p align="left">
  <img src="docs/images/settings.png" alt="Web settings — add API Key" width="720"/>
</p>

1. **API Base URL**: defaults to `https://apihub.agnes-ai.com`; usually no change needed
2. **Add API Key**: enter a label and your key; check “Enable immediately after adding”
3. Add multiple keys and switch the active one anytime

You can then use chat, image, and video generation.

The dev server proxies `/api` requests to `http://127.0.0.1:8000`.

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

## License

This project is licensed under the [MIT License](./LICENSE).

You may use, modify, and distribute the code freely, provided the original copyright notice and license text are retained. The software is provided “as is”, without warranty of any kind.
