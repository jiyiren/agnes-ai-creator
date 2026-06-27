import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.database import get_db, row_to_dict
from app.schemas import ConversationCreate, ConversationUpdate, ChatRequest, RegenerateRequest
from app.services.agnes_client import agnes_client
from app.services.token_utils import estimate_tokens

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _chat_kwargs(body) -> dict:
    kwargs = {}
    if body.temperature is not None:
        kwargs["temperature"] = body.temperature
    if body.top_p is not None:
        kwargs["top_p"] = body.top_p
    if body.max_tokens is not None:
        kwargs["max_tokens"] = body.max_tokens
    if body.enable_thinking:
        kwargs["chat_template_kwargs"] = {"enable_thinking": True}
    return kwargs


def _assistant_stream(conv_id: int, model: str, messages: list, kwargs: dict):
    async def event_stream():
        full_content = ""
        usage = {}
        duration_ms = 0
        try:
            async for chunk in agnes_client.chat_completion_stream(model, messages, **kwargs):
                if chunk["type"] == "content":
                    full_content += chunk["content"]
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk['content']}, ensure_ascii=False)}\n\n"
                elif chunk["type"] == "done":
                    usage = chunk.get("usage", {})
                    duration_ms = chunk.get("duration_ms", 0)
                    with get_db() as conn:
                        conn.execute(
                            """INSERT INTO messages (conversation_id, role, content, prompt_tokens, completion_tokens, total_tokens, duration_ms, model)
                               VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?)""",
                            (conv_id, full_content, usage.get("prompt_tokens", 0),
                             usage.get("completion_tokens", 0), usage.get("total_tokens", 0), duration_ms, model),
                        )
                        conn.execute(
                            "UPDATE conversations SET updated_at = datetime('now','localtime') WHERE id = ?",
                            (conv_id,),
                        )
                    yield f"data: {json.dumps({'type': 'done', 'usage': usage, 'duration_ms': duration_ms}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sync_conv_model(conv_id: int, model: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE conversations SET model = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (model, conv_id),
        )


@router.get("/models")
def list_models():
    return {
        "models": [
            {"id": "agnes-2.0-flash", "name": "Agnes 2.0 Flash", "deprecated": False},
            {"id": "agnes-1.5-flash", "name": "Agnes 1.5 Flash", "deprecated": True},
        ]
    }


@router.get("/conversations")
def list_conversations():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("/conversations")
def create_conversation(body: ConversationCreate):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title, model) VALUES (?, ?)",
            (body.title, body.model),
        )
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return row_to_dict(row)


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: int):
    with get_db() as conn:
        conv = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        if not conv:
            raise HTTPException(404, "对话不存在")
        messages = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        ).fetchall()
    return {"conversation": row_to_dict(conv), "messages": [row_to_dict(m) for m in messages]}


@router.patch("/conversations/{conv_id}")
def update_conversation(conv_id: int, body: ConversationUpdate):
    with get_db() as conn:
        conv = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        if not conv:
            raise HTTPException(404, "对话不存在")
        if body.title:
            conn.execute("UPDATE conversations SET title = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                         (body.title, conv_id))
        if body.model:
            conn.execute("UPDATE conversations SET model = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                         (body.model, conv_id))
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    return row_to_dict(row)


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    return {"ok": True}


@router.delete("/conversations/{conv_id}/messages/{msg_id}")
def delete_message(conv_id: int, msg_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, role FROM messages WHERE id = ? AND conversation_id = ?",
            (msg_id, conv_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "消息不存在")
        if row["role"] == "assistant":
            conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        elif row["role"] == "user":
            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ? AND id >= ?",
                (conv_id, msg_id),
            )
        else:
            raise HTTPException(400, "不支持删除此类型消息")
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now','localtime') WHERE id = ?",
            (conv_id,),
        )
    return {"ok": True}


@router.post("/conversations/{conv_id}/messages/{msg_id}/regenerate")
async def regenerate_message(conv_id: int, msg_id: int, body: RegenerateRequest):
    with get_db() as conn:
        conv = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        if not conv:
            raise HTTPException(404, "对话不存在")
        msg = conn.execute(
            "SELECT id, role FROM messages WHERE id = ? AND conversation_id = ?",
            (msg_id, conv_id),
        ).fetchone()
        if not msg:
            raise HTTPException(404, "消息不存在")
        if msg["role"] != "assistant":
            raise HTTPException(400, "只能重新生成助手回复")
        prev = conn.execute(
            """SELECT id, role FROM messages
               WHERE conversation_id = ? AND id < ? ORDER BY id DESC LIMIT 1""",
            (conv_id, msg_id),
        ).fetchone()
        if not prev or prev["role"] != "user":
            raise HTTPException(400, "找不到对应的用户提问")
        conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        history = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        ).fetchall()
        messages = [{"role": r["role"], "content": r["content"]} for r in history]

    model = body.model or conv["model"]
    _sync_conv_model(conv_id, model)
    kwargs = _chat_kwargs(body)
    if not body.stream:
        result = await agnes_client.chat_completion(model, messages, **kwargs)
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        duration_ms = result.get("duration_ms", 0)
        with get_db() as conn:
            conn.execute(
                """INSERT INTO messages (conversation_id, role, content, prompt_tokens, completion_tokens, total_tokens, duration_ms, model)
                   VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?)""",
                (conv_id, content, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                 usage.get("total_tokens", 0), duration_ms, model),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = datetime('now','localtime') WHERE id = ?",
                (conv_id,),
            )
        return {"content": content, "usage": usage, "duration_ms": duration_ms}

    return _assistant_stream(conv_id, model, messages, kwargs)


@router.post("/conversations/{conv_id}/send")
async def send_message(conv_id: int, body: ChatRequest):
    with get_db() as conn:
        conv = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        if not conv:
            raise HTTPException(404, "对话不存在")

        content_str = body.content if isinstance(body.content, str) else json.dumps(body.content, ensure_ascii=False)
        user_tokens = estimate_tokens(content_str)
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, total_tokens) VALUES (?, 'user', ?, ?)",
            (conv_id, content_str, user_tokens),
        )
        history = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        ).fetchall()
        messages = [{"role": r["role"], "content": r["content"]} for r in history]

    model = body.model or conv["model"]
    _sync_conv_model(conv_id, model)
    kwargs = _chat_kwargs(body)

    if not body.stream:
        result = await agnes_client.chat_completion(model, messages, **kwargs)
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        duration_ms = result.get("duration_ms", 0)
        with get_db() as conn:
            conn.execute(
                """INSERT INTO messages (conversation_id, role, content, prompt_tokens, completion_tokens, total_tokens, duration_ms, model)
                   VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?)""",
                (conv_id, content, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                 usage.get("total_tokens", 0), duration_ms, model),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = datetime('now','localtime') WHERE id = ?",
                (conv_id,),
            )
        return {"content": content, "usage": usage, "duration_ms": duration_ms}

    return _assistant_stream(conv_id, model, messages, kwargs)
