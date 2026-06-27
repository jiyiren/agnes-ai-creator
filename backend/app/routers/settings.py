from fastapi import APIRouter, HTTPException

from app.schemas import AgnesBaseUrlUpdate, ApiKeyCreate, ApiKeyUpdate
from app.services import api_key_service
from app.config import is_qiniu_configured
from app.services.app_settings_service import (
    DEFAULT_AGNES_BASE_URL,
    get_agnes_base_url,
    set_agnes_base_url,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/status")
def get_status():
    active = api_key_service.get_active_api_key()
    return {
        "has_active_key": bool(active),
        "key_count": len(api_key_service.list_api_keys()),
        "has_qiniu_config": is_qiniu_configured(),
        "agnes_base_url": get_agnes_base_url(),
        "default_agnes_base_url": DEFAULT_AGNES_BASE_URL,
    }


@router.get("/base-url")
def get_base_url():
    return {
        "base_url": get_agnes_base_url(),
        "default_base_url": DEFAULT_AGNES_BASE_URL,
    }


@router.put("/base-url")
def update_base_url(body: AgnesBaseUrlUpdate):
    try:
        return {"base_url": set_agnes_base_url(body.base_url)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api-keys")
def list_api_keys():
    return {"items": api_key_service.list_api_keys()}


@router.post("/api-keys")
def create_api_key(body: ApiKeyCreate):
    try:
        item = api_key_service.create_api_key(
            body.name, body.api_key, activate=body.activate
        )
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/api-keys/{key_id}")
def update_api_key(key_id: int, body: ApiKeyUpdate):
    try:
        return api_key_service.update_api_key(
            key_id, name=body.name, api_key=body.api_key
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api-keys/{key_id}/activate")
def activate_api_key(key_id: int):
    try:
        return api_key_service.activate_api_key(key_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: int):
    try:
        api_key_service.delete_api_key(key_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
