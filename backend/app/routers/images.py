import json
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from app.database import get_db, row_to_dict
from app.schemas import ImageGenerateRequest
from app.services.agnes_client import agnes_client
from app.services.error_utils import is_transient_http_error
from app.services.qiniu_service import upload_bytes, upload_from_url

router = APIRouter(prefix="/api/images", tags=["images"])


async def _upload_input_file(file: UploadFile) -> dict:
    content = await file.read()
    ext = (file.filename or "image.png").rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        ext = "png"
    uploaded = upload_bytes(content, "img", ext)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO uploads (filename, original_name, qiniu_key, qiniu_url, file_type, size_bytes)
               VALUES (?, ?, ?, ?, 'img', ?)""",
            (uploaded["key"], file.filename, uploaded["key"], uploaded["url"], uploaded["size"]),
        )
    return uploaded


async def _complete_image_task(task_id: int, result: dict) -> dict:
    item = result.get("data", [{}])[0]
    output_url = item.get("url")
    b64 = item.get("b64_json")
    revised = item.get("revised_prompt")
    qiniu_url = None

    if output_url:
        try:
            uploaded = upload_from_url(output_url, "img")
            qiniu_url = uploaded["url"]
        except Exception:
            pass
    elif b64:
        try:
            data = base64.b64decode(b64)
            uploaded = upload_bytes(data, "img", "png")
            qiniu_url = uploaded["url"]
            output_url = qiniu_url
        except Exception:
            pass

    with get_db() as conn:
        conn.execute(
            """UPDATE image_tasks SET status='completed', output_url=?, qiniu_url=?, revised_prompt=?,
               duration_ms=?, error_message=NULL, completed_at=datetime('now','localtime') WHERE id=?""",
            (output_url, qiniu_url, revised, result.get("duration_ms", 0), task_id),
        )
        row = conn.execute("SELECT * FROM image_tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_dict(row)


async def _run_image_generate(body: ImageGenerateRequest, task_id: int | None = None):
    payload = {
        "model": body.model,
        "prompt": body.prompt,
        "size": body.size,
    }

    if body.mode == "text2img":
        if body.return_base64:
            payload["return_base64"] = True
        else:
            payload["extra_body"] = {"response_format": body.response_format}
    else:
        images = body.images or []
        if not images:
            raise HTTPException(400, "单图编辑/多图合成模式需要提供输入图片")
        if body.mode == "img2img" and len(images) > 1:
            raise HTTPException(400, "单图编辑模式仅支持一张参考图片")
        extra = {
            "image": images,
            "response_format": "b64_json" if body.return_base64 else body.response_format,
        }
        payload["extra_body"] = extra

    with get_db() as conn:
        if task_id is None:
            cur = conn.execute(
                """INSERT INTO image_tasks (model, mode, prompt, size, input_images, status, request_params)
                   VALUES (?, ?, ?, ?, ?, 'processing', ?)""",
                (body.model, body.mode, body.prompt, body.size,
                 json.dumps(body.images) if body.images else None,
                 json.dumps(payload, ensure_ascii=False)),
            )
            task_id = cur.lastrowid
        else:
            conn.execute(
                """UPDATE image_tasks SET status='processing', error_message=NULL, completed_at=NULL
                   WHERE id=?""",
                (task_id,),
            )

    try:
        result = await agnes_client.generate_image(payload)
        return await _complete_image_task(task_id, result)

    except Exception as e:
        err_msg = str(e)
        with get_db() as conn:
            conn.execute(
                "UPDATE image_tasks SET status='failed', error_message=?, completed_at=datetime('now','localtime') WHERE id=?",
                (err_msg, task_id),
            )
        status = 502 if "Agnes API" in err_msg else 500
        if is_transient_http_error(e):
            status = 429
        raise HTTPException(status, err_msg)


@router.get("/models")
def list_models():
    return {
        "models": [
            {"id": "agnes-image-2.1-flash", "name": "Agnes Image 2.1 Flash"},
            {"id": "agnes-image-2.0-flash", "name": "Agnes Image 2.0 Flash"},
        ],
        "sizes": ["1024x768", "1024x1024", "768x1024", "768x768", "1280x720", "720x1280"],
    }


@router.get("/tasks")
def list_tasks(limit: int = 20, offset: int = 0):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM image_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM image_tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise HTTPException(404, "任务不存在")
    return row_to_dict(row)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM image_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, "任务不存在")
        conn.execute("DELETE FROM image_tasks WHERE id = ?", (task_id,))
    return {"ok": True}


@router.post("/generate")
async def generate_image(request: Request):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        files = [f for f in form.getlist("files") if isinstance(f, UploadFile)]
        mode = form.get("mode") or "text2img"
        if mode == "text2img":
            raise HTTPException(400, "文生图模式不需要上传图片")
        if not files:
            raise HTTPException(400, "请上传参考图片")
        if mode == "img2img" and len(files) != 1:
            raise HTTPException(400, "单图编辑模式仅支持一张参考图片")
        image_urls = []
        for file in files:
            image_urls.append((await _upload_input_file(file))["url"])
        body = ImageGenerateRequest(
            model=form.get("model") or "agnes-image-2.1-flash",
            prompt=form.get("prompt") or "",
            size=form.get("size") or "1024x768",
            mode=mode,
            images=image_urls,
            return_base64=(form.get("return_base64") or "false").lower() == "true",
            response_format=form.get("response_format") or "url",
        )
    else:
        body = ImageGenerateRequest(**await request.json())
        if body.mode != "text2img" and not body.images:
            raise HTTPException(400, "单图编辑/多图合成模式需要提供输入图片")
        if body.mode == "img2img" and body.images and len(body.images) != 1:
            raise HTTPException(400, "单图编辑模式仅支持一张参考图片")

    return await _run_image_generate(body)


@router.post("/tasks/{task_id}/sync")
async def sync_image_task(task_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM image_tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise HTTPException(404, "任务不存在")
    if row["status"] == "completed":
        return row_to_dict(row)
    if not row["request_params"]:
        raise HTTPException(400, "缺少请求参数，无法刷新")

    images = json.loads(row["input_images"]) if row["input_images"] else None
    body = ImageGenerateRequest(
        model=row["model"],
        mode=row["mode"],
        prompt=row["prompt"],
        size=row["size"],
        images=images,
    )
    return await _run_image_generate(body, task_id=task_id)


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """遗留接口，图片生成请使用 /generate multipart 提交，避免选图时提前上传 OSS。"""
    uploaded = await _upload_input_file(file)
    return {"url": uploaded["url"], "key": uploaded["key"]}
