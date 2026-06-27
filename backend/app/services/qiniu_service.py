import uuid
import httpx
from qiniu import Auth, put_data, BucketManager
from app.config import (
    QINIU_ACCESS_KEY, QINIU_SECRET_KEY, QINIU_BUCKET, QINIU_DOMAIN
)


def _get_auth():
    return Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)


def upload_bytes(data: bytes, file_type: str = "img", ext: str = "png") -> dict:
    """Upload bytes to Qiniu. file_type: img|video|document|other"""
    prefix_map = {
        "img": "data/img",
        "video": "data/video",
        "document": "data/document",
        "other": "data/other",
    }
    prefix = prefix_map.get(file_type, "data/other")
    key = f"{prefix}/{uuid.uuid4().hex}.{ext}"

    auth = _get_auth()
    token = auth.upload_token(QINIU_BUCKET, key, 3600)
    ret, info = put_data(token, key, data)
    if info.status_code != 200:
        raise RuntimeError(f"七牛上传失败: {info}")

    url = f"{QINIU_DOMAIN.rstrip('/')}/{key}"
    return {"key": key, "url": url, "size": len(data)}


def upload_from_url(source_url: str, file_type: str = "img", ext: str = None) -> dict:
    """Download from URL and upload to Qiniu."""
    with httpx.Client(timeout=120, trust_env=False) as client:
        resp = client.get(source_url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if not ext:
            if "video" in content_type or source_url.endswith(".mp4"):
                ext = "mp4"
                file_type = "video"
            elif "jpeg" in content_type or source_url.endswith(".jpg"):
                ext = "jpg"
            elif "webp" in content_type:
                ext = "webp"
            else:
                ext = "png"
        return upload_bytes(resp.content, file_type, ext)


def delete_file(key: str):
    auth = _get_auth()
    bucket = BucketManager(auth)
    bucket.delete(QINIU_BUCKET, key)
