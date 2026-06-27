import os

from app.database import get_db

DEFAULT_AGNES_BASE_URL = "https://apihub.agnes-ai.com"
AGNES_BASE_URL_KEY = "agnes_base_url"


def normalize_base_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        raise ValueError("Base URL 必须以 http:// 或 https:// 开头")
    return url


def get_agnes_base_url() -> str:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (AGNES_BASE_URL_KEY,),
        ).fetchone()
        if row and row[0]:
            return row[0]
    return DEFAULT_AGNES_BASE_URL


def set_agnes_base_url(url: str) -> str:
    url = normalize_base_url(url)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO app_settings (key, value, updated_at)
               VALUES (?, ?, datetime('now', 'localtime'))
               ON CONFLICT(key) DO UPDATE SET
                 value = excluded.value,
                 updated_at = excluded.updated_at""",
            (AGNES_BASE_URL_KEY, url),
        )
    return url


def ensure_default_settings() -> None:
    env_url = os.getenv("AGNES_BASE_URL", "").strip()
    if env_url:
        try:
            initial = normalize_base_url(env_url)
        except ValueError:
            initial = DEFAULT_AGNES_BASE_URL
    else:
        initial = DEFAULT_AGNES_BASE_URL
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (AGNES_BASE_URL_KEY,),
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?)",
                (AGNES_BASE_URL_KEY, initial),
            )
