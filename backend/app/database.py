import sqlite3
from pathlib import Path
from contextlib import contextmanager
from app.config import DATABASE_PATH, BASE_DIR


def _migrate_video_tasks_status():
    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='video_tasks'"
        ).fetchone()
        if not row or "'submitting'" in row[0]:
            return

        conn.executescript("""
            CREATE TABLE video_tasks_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL DEFAULT 'agnes-video-v2.0',
                mode TEXT NOT NULL CHECK(mode IN ('text2video', 'img2video', 'multi_img', 'keyframes')),
                prompt TEXT NOT NULL,
                negative_prompt TEXT,
                task_id TEXT,
                video_id TEXT,
                width INTEGER DEFAULT 1152,
                height INTEGER DEFAULT 768,
                num_frames INTEGER DEFAULT 121,
                frame_rate REAL DEFAULT 24,
                num_inference_steps INTEGER,
                seed INTEGER,
                input_images TEXT,
                output_url TEXT,
                qiniu_url TEXT,
                status TEXT NOT NULL DEFAULT 'queued'
                    CHECK(status IN ('submitting', 'queued', 'in_progress', 'completed', 'failed')),
                progress INTEGER DEFAULT 0,
                seconds TEXT,
                size TEXT,
                duration_ms INTEGER DEFAULT 0,
                error_message TEXT,
                request_params TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                completed_at TEXT
            );
            INSERT INTO video_tasks_new SELECT * FROM video_tasks;
            DROP TABLE video_tasks;
            ALTER TABLE video_tasks_new RENAME TO video_tasks;
            CREATE INDEX IF NOT EXISTS idx_video_tasks_status ON video_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_video_tasks_video_id ON video_tasks(video_id);
            CREATE INDEX IF NOT EXISTS idx_video_tasks_created_at ON video_tasks(created_at DESC);
        """)
        conn.commit()


def init_db():
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = BASE_DIR / "sql" / "schema.sql"
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
        if "model" not in cols:
            conn.execute("ALTER TABLE messages ADD COLUMN model TEXT")
        conn.commit()
    _migrate_video_tasks_status()


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)
