import json
import time
import asyncio
import httpx
from typing import AsyncGenerator, Optional
from app.config import AGNES_API_KEY, AGNES_BASE_URL
from app.services.error_utils import format_agnes_error


class AgnesClient:
    def __init__(self):
        self.base_url = AGNES_BASE_URL

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {AGNES_API_KEY}",
            "Content-Type": "application/json",
        }

    async def chat_completion_stream(
        self, model: str, messages: list, **kwargs
    ) -> AsyncGenerator[dict, None]:
        payload = {"model": model, "messages": messages, "stream": True, **kwargs}
        start = time.time()
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        async with httpx.AsyncClient(timeout=300, trust_env=False) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content") or delta.get("reasoning_content") or ""
                    if content:
                        yield {"type": "content", "content": content}
                duration_ms = int((time.time() - start) * 1000)
                yield {"type": "done", "usage": usage, "duration_ms": duration_ms}

    async def chat_completion(self, model: str, messages: list, **kwargs) -> dict:
        payload = {"model": model, "messages": messages, **kwargs}
        start = time.time()
        async with httpx.AsyncClient(timeout=300, trust_env=False) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            duration_ms = int((time.time() - start) * 1000)
            data["duration_ms"] = duration_ms
            return data

    async def generate_image(self, payload: dict) -> dict:
        start = time.time()
        url = f"{self.base_url}/v1/images/generations"
        async with httpx.AsyncClient(timeout=360, trust_env=False) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"Agnes API {resp.status_code}: {resp.text}")
            data = resp.json()
            data["duration_ms"] = int((time.time() - start) * 1000)
            return data

    async def create_video(self, payload: dict) -> dict:
        start = time.time()
        async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
            resp = await client.post(
                f"{self.base_url}/v1/videos",
                headers=self.headers,
                json=payload,
            )
            if resp.status_code >= 400:
                detail = None
                try:
                    body = resp.json()
                    detail = format_agnes_error(body.get("error") or body)
                except Exception:
                    detail = resp.text.strip() or None
                raise RuntimeError(
                    detail or f"Agnes API {resp.status_code}: {resp.text or '请求失败'}"
                )
            data = resp.json()
            data["duration_ms"] = int((time.time() - start) * 1000)
            return data

    async def get_video_status(self, video_id: str, model_name: Optional[str] = None) -> dict:
        params = {"video_id": video_id}
        if model_name:
            params["model_name"] = model_name

        delays = (0, 2, 5, 10)
        last_error = None
        for attempt, delay in enumerate(delays):
            if delay:
                await asyncio.sleep(delay)
            try:
                async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
                    resp = await client.get(
                        f"{self.base_url}/agnesapi",
                        headers=self.headers,
                        params=params,
                    )
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 and attempt < len(delays) - 1:
                    continue
                raise
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_error = e
                if attempt < len(delays) - 1:
                    continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError("查询视频状态失败")

    async def get_video_status_by_task(self, task_id: str) -> dict:
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            resp = await client.get(
                f"{self.base_url}/v1/videos/{task_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()


agnes_client = AgnesClient()
