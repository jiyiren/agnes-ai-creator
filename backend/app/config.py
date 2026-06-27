import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR / ".env")

QINIU_ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY", "").strip()
QINIU_SECRET_KEY = os.getenv("QINIU_SECRET_KEY", "").strip()
QINIU_BUCKET = os.getenv("QINIU_BUCKET", "").strip()
QINIU_DOMAIN = os.getenv("QINIU_DOMAIN", "").strip().rstrip("/")
QINIU_REGION = os.getenv("QINIU_REGION", "z0").strip()

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "aimodel.db"))

TEXT_MODELS = ["agnes-2.0-flash", "agnes-1.5-flash"]
IMAGE_MODELS = ["agnes-image-2.0-flash", "agnes-image-2.1-flash"]
VIDEO_MODELS = ["agnes-video-v2.0"]

IMAGE_SIZES = ["1024x768", "1024x1024", "768x1024", "768x768", "1280x720", "720x1280"]


def is_qiniu_configured() -> bool:
    return bool(
        QINIU_ACCESS_KEY
        and QINIU_SECRET_KEY
        and QINIU_BUCKET
        and QINIU_DOMAIN
    )


def validate_config():
    pass
