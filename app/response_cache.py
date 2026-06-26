import time
from hashlib import md5
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.background import BackgroundTask


CACHE_CONFIG: dict[str, int] = {
    "/exercises": 600,
    "/meta": 600,
    "/health": 60,
    "/personal-records": 60,
}

INVALIDATE_PREFIXES: dict[str, list[str]] = {
    "/workout-sessions": ["/users/me/overview", "/personal-records"],
}

_cache: dict[str, tuple[float, int, dict[str, str], bytes]] = {}
_PREFIXES = tuple(sorted(CACHE_CONFIG.keys(), key=len, reverse=True))


def _ttl_for(path: str) -> int:
    for prefix in _PREFIXES:
        if path.startswith(prefix):
            return CACHE_CONFIG[prefix]
    return 0


def _cache_key(method: str, path: str, params: list[tuple[str, str]]) -> str:
    raw = f"{method}:{path}:{sorted(params)}"
    return md5(raw.encode()).hexdigest()


def _invalidate_related(path: str) -> None:
    targets: list[str] = []
    for prefix, related in INVALIDATE_PREFIXES.items():
        if path.startswith(prefix):
            targets.extend(related)
            break
    if not targets:
        for prefix in _PREFIXES:
            if path.startswith(prefix):
                targets.append(prefix)
                break
    if not targets:
        return

    prefix_hashes = [md5(f"GET:{t}".encode()).hexdigest()[:8] for t in targets]
    keys = list(_cache.keys())
    for key in keys:
        for ph in prefix_hashes:
            if key.startswith(ph):
                _cache.pop(key, None)
                break


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.method != "GET":
            _invalidate_related(request.url.path)
            return await call_next(request)

        ttl = _ttl_for(request.url.path)
        if ttl == 0:
            return await call_next(request)

        key = _cache_key(request.method, request.url.path, list(request.query_params.items()))
        cached = _cache.get(key)
        if cached is not None:
            ts, status, headers, body = cached
            if time.monotonic() - ts < ttl:
                return Response(content=body, status_code=status, headers=headers, media_type="application/json")

        response = await call_next(request)

        if response.status_code == 200:
            try:
                body = response.body
            except RuntimeError:
                return response
            _cache[key] = (time.monotonic(), response.status_code, dict(response.headers), body)
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response
