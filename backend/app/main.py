import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import init_db
from app.config import validate_config
from app.routers import chat, images, videos, settings
from app.services.video_poller import poll_pending_videos

scheduler = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1})


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_config()
    init_db()
    scheduler.add_job(
        lambda: asyncio.run(poll_pending_videos()),
        "interval",
        seconds=15,
        id="video_poller",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Agnes AI Creator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(images.router)
app.include_router(videos.router)
app.include_router(settings.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
