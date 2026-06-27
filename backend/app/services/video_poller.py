import asyncio
import threading
from app.database import get_db
from app.services.agnes_client import agnes_client
from app.services.error_utils import format_agnes_error, is_transient_http_error
from app.services.qiniu_service import upload_from_url


def _upload_qiniu_background(task_id: int, video_url: str):
    """Upload completed video to Qiniu without blocking the poller."""
    try:
        uploaded = upload_from_url(video_url, "video")
        with get_db() as conn:
            conn.execute(
                "UPDATE video_tasks SET qiniu_url = ? WHERE id = ?",
                (uploaded["url"], task_id),
            )
    except Exception as e:
        with get_db() as conn:
            conn.execute(
                "UPDATE video_tasks SET error_message = ? WHERE id = ? AND qiniu_url IS NULL",
                (f"七牛上传失败: {e}", task_id),
            )


async def refresh_task_from_agnes(task_id: int, video_id: str, model: str, *, current_qiniu_url=None) -> bool:
    """Pull latest status from Agnes and persist it. Returns True if updated."""
    result = await agnes_client.get_video_status(video_id, model)
    status = result.get("status", "queued")
    progress = result.get("progress", 0)

    update_fields = {
        "status": status,
        "progress": progress,
        "seconds": result.get("seconds"),
        "size": result.get("size"),
    }

    if status == "completed":
        video_url = result.get("remixed_from_video_id")
        update_fields["output_url"] = video_url
        update_fields["error_message"] = None
        if video_url and not current_qiniu_url:
            threading.Thread(
                target=_upload_qiniu_background,
                args=(task_id, video_url),
                daemon=True,
            ).start()
    elif status == "failed":
        err = result.get("error")
        update_fields["error_message"] = format_agnes_error(err) or "生成失败"

    with get_db() as conn:
        sets = ", ".join(f"{k} = ?" for k in update_fields)
        vals = list(update_fields.values())
        sql = f"UPDATE video_tasks SET {sets}"
        if status in ("completed", "failed"):
            sql += ", completed_at = datetime('now', 'localtime')"
        sql += " WHERE id = ?"
        vals.append(task_id)
        conn.execute(sql, vals)
    return True


async def _poll_one(row):
    await refresh_task_from_agnes(
        row["id"],
        row["video_id"],
        row["model"],
        current_qiniu_url=row["qiniu_url"] if "qiniu_url" in row.keys() else None,
    )


async def poll_pending_videos():
    """Poll in-progress video tasks and update status."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, video_id, model, qiniu_url FROM video_tasks
               WHERE status IN ('queued', 'in_progress') AND video_id IS NOT NULL
               ORDER BY created_at ASC"""
        ).fetchall()

    if not rows:
        return

    for row in rows:
        try:
            await _poll_one(row)
        except Exception as e:
            if is_transient_http_error(e):
                continue
            # Non-transient polling errors should not fail the task either.
            continue
        await asyncio.sleep(0.5)
