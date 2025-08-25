import asyncio
import importlib
import os
import time
from typing import Dict, Any, List, Callable, Optional
from .base import BaseTool
from services.config import load_resolver_config

def _resolve_module(path: str) -> Optional[Callable]:
    try:
        mod_path, fn_name = path.rsplit(".", 1)
        mod = importlib.import_module(mod_path)
        return getattr(mod, fn_name)
    except Exception:
        return None

def _run_trio(email: str, funcs: List[Callable], timeout_ms: int, retries: int) -> List[Dict[str, Any]]:
    import trio
    import httpx
    import random

    async def _call_with_guards(fn, client, out):
        attempts = retries + 1
        for attempt in range(1, attempts + 1):
            t0 = time.time()
            try:
                with trio.move_on_after(timeout_ms / 1000.0):
                    await fn(email, client, out)
                    return {"ok": True, "module": f"{fn.__module__}.{fn.__name__}", "runtime_ms": int((time.time() - t0) * 1000)}
                return {"ok": False, "module": f"{fn.__module__}.{fn.__name__}", "error": "timeout", "runtime_ms": int((time.time() - t0) * 1000)}
            except Exception as e:
                if attempt >= attempts:
                    return {"ok": False, "module": f"{fn.__module__}.{fn.__name__}", "error": str(e), "runtime_ms": int((time.time() - t0) * 1000)}
                await trio.sleep(0.2 + random.random() * 0.3)

    async def _main():
        results: List[Dict[str, Any]] = []
        out: List[dict] = []
        async with httpx.AsyncClient() as client:
            for fn in funcs:
                r = await _call_with_guards(fn, client, out)
                results.append(r)
        return {"statuses": results, "modules": out}

    return trio.run(_main)

class HoleheResolverTool(BaseTool):
    @property
    def name(self) -> str:
        return "holehe_resolver"

    @property
    def stage(self) -> str:
        return "deep"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("email"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        email: str = params["email"]
        used_ids: List[str] = params.get("used_service_ids") or params.get("used_services") or []
        timeout_ms = int(os.getenv("HOLEHE_RESOLVER_TIMEOUT_MS", "10000"))
        retries = int(os.getenv("HOLEHE_RESOLVER_RETRIES", "1"))

        config = load_resolver_config()
        funcs: List[Callable] = []
        coverage: List[Dict[str, str]] = []
        by_service = {c.get("service"): c for c in config if c.get("module_path")}
        for sid in used_ids or ["twitter.com", "instagram.com", "snapchat.com"]:
            entry = by_service.get(sid)
            if not entry:
                continue
            fn = _resolve_module(entry["module_path"])
            if fn:
                funcs.append(fn)
                coverage.append({"service": sid, "module_path": entry["module_path"]})

        if not funcs:
            return {"source": "Holehe-Modules", "raw_data": {"schema_version": "1.0", "email": email, "modules": [], "note": "no resolvers available"}}

        result = await asyncio.to_thread(_run_trio, email, funcs, timeout_ms, retries)

        return {
            "source": "Holehe-Modules",
            "raw_data": {
                "schema_version": "1.0",
                "email": email,
                "coverage": coverage,
                "statuses": result.get("statuses", []),
                "modules": result.get("modules", []),
            },
        }


