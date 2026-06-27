import os
from typing import Optional

from app.database import get_db, row_to_dict


def mask_api_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return f"****{key[-4:]}"


def get_active_api_key() -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT api_key FROM api_keys WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        return row[0] if row else None


def list_api_keys() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, name, api_key, is_active, created_at, updated_at
               FROM api_keys ORDER BY is_active DESC, created_at DESC"""
        ).fetchall()
        result = []
        for row in rows:
            item = row_to_dict(row)
            item["key_masked"] = mask_api_key(item.pop("api_key"))
            item["is_active"] = bool(item["is_active"])
            result.append(item)
        return result


def create_api_key(name: str, api_key: str, *, activate: bool = True) -> dict:
    name = name.strip()
    api_key = api_key.strip()
    if not name:
        raise ValueError("名称不能为空")
    if not api_key:
        raise ValueError("API Key 不能为空")

    with get_db() as conn:
        if activate:
            conn.execute("UPDATE api_keys SET is_active = 0")
        cur = conn.execute(
            """INSERT INTO api_keys (name, api_key, is_active)
               VALUES (?, ?, ?)""",
            (name, api_key, 1 if activate else 0),
        )
        row = conn.execute(
            "SELECT id, name, api_key, is_active, created_at, updated_at FROM api_keys WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        item = row_to_dict(row)
        item["key_masked"] = mask_api_key(item.pop("api_key"))
        item["is_active"] = bool(item["is_active"])
        return item


def update_api_key(key_id: int, *, name: Optional[str] = None, api_key: Optional[str] = None) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        if not row:
            raise ValueError("API Key 不存在")

        updates = []
        params = []
        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("名称不能为空")
            updates.append("name = ?")
            params.append(name)
        if api_key is not None:
            api_key = api_key.strip()
            if not api_key:
                raise ValueError("API Key 不能为空")
            updates.append("api_key = ?")
            params.append(api_key)
        if not updates:
            raise ValueError("没有可更新的字段")

        updates.append("updated_at = datetime('now', 'localtime')")
        params.append(key_id)
        conn.execute(
            f"UPDATE api_keys SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        row = conn.execute(
            "SELECT id, name, api_key, is_active, created_at, updated_at FROM api_keys WHERE id = ?",
            (key_id,),
        ).fetchone()
        item = row_to_dict(row)
        item["key_masked"] = mask_api_key(item.pop("api_key"))
        item["is_active"] = bool(item["is_active"])
        return item


def activate_api_key(key_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        if not row:
            raise ValueError("API Key 不存在")
        conn.execute("UPDATE api_keys SET is_active = 0")
        conn.execute(
            """UPDATE api_keys
               SET is_active = 1, updated_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (key_id,),
        )
        row = conn.execute(
            "SELECT id, name, api_key, is_active, created_at, updated_at FROM api_keys WHERE id = ?",
            (key_id,),
        ).fetchone()
        item = row_to_dict(row)
        item["key_masked"] = mask_api_key(item.pop("api_key"))
        item["is_active"] = bool(item["is_active"])
        return item


def delete_api_key(key_id: int) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, is_active FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        if not row:
            raise ValueError("API Key 不存在")
        was_active = bool(row["is_active"])
        conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        if was_active:
            next_row = conn.execute(
                "SELECT id FROM api_keys ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if next_row:
                conn.execute(
                    """UPDATE api_keys
                       SET is_active = 1, updated_at = datetime('now', 'localtime')
                       WHERE id = ?""",
                    (next_row["id"],),
                )


def import_env_api_key_if_empty() -> None:
    env_key = os.getenv("AGNES_API_KEY", "").strip()
    if not env_key:
        return
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM api_keys").fetchone()[0]
        if count == 0:
            conn.execute(
                "INSERT INTO api_keys (name, api_key, is_active) VALUES (?, ?, 1)",
                ("环境变量导入", env_key),
            )
