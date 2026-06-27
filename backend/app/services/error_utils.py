import json
from typing import Any, Optional


def format_agnes_error(err: Any) -> Optional[str]:
    """Normalize Agnes API error payloads into a human-readable string."""
    if err is None:
        return None
    if isinstance(err, str):
        text = err.strip()
        return text or None
    if isinstance(err, dict):
        for key in ("message", "msg", "detail", "error", "code", "type"):
            val = err.get(key)
            if val is None or val == "":
                continue
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                nested = format_agnes_error(val)
                if nested:
                    return nested
            return str(val)
        return json.dumps(err, ensure_ascii=False)
    return str(err)


def is_transient_http_error(err: BaseException) -> bool:
    """Return True for rate limits / temporary upstream failures."""
    text = str(err).lower()
    markers = (
        "429",
        "too many requests",
        "503",
        "502",
        "504",
        "timeout",
        "timed out",
        "connection reset",
        "connection refused",
        "temporarily unavailable",
    )
    return any(marker in text for marker in markers)


def is_rate_limit_error(err: BaseException) -> bool:
    text = str(err).lower()
    return "429" in text or "too many requests" in text
