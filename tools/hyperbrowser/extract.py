import os
import asyncio
import time
from typing import Dict, Any, List, Optional

from ..base import BaseTool
from .client import HyperbrowserClient
from schemas import HyperbrowserParams


class HyperbrowserExtractTool(BaseTool):
    @property
    def name(self) -> str:
        return "hyperbrowser_extract"

    @property
    def stage(self) -> str:
        return "deep"

    def _enabled(self) -> bool:
        return os.getenv("HYPERBROWSER_ENABLE_EXTRACT", "true").lower() == "true"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        if not self._enabled():
            return False
        hb: Optional[Dict[str, Any]] = params.get("hyperbrowser")
        if not hb or not isinstance(hb, dict):
            return False
        extract = hb.get("extract") or {}
        urls: Optional[List[str]] = extract.get("urls")
        schema = extract.get("schema")
        prompt = extract.get("prompt")
        return bool(urls and (schema or prompt))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        client = HyperbrowserClient()
        if not client.is_configured():
            return {"source": "Hyperbrowser-Extract", "raw_data": {"error": "API key not configured"}}

        hb: Dict[str, Any] = params.get("hyperbrowser") or {}
        p: Dict[str, Any] = hb.get("extract") or {}

        urls: List[str] = p.get("urls") or []
        schema = p.get("schema")
        prompt = p.get("prompt")
        max_links: Optional[int] = p.get("max_links")
        session_options: Dict[str, Any] = (hb.get("session_options") or p.get("session_options") or {})

        timeout_ms = int(os.getenv("HYPERBROWSER_EXTRACT_TIMEOUT_MS", os.getenv("HYPERBROWSER_TIMEOUT_MS", "90000")))

        start_ts = time.monotonic()

        async def _call():
            # Lazy import to avoid hard dependency at import-time
            from hyperbrowser import Hyperbrowser
            from hyperbrowser.models import StartExtractJobParams

            hb_client = Hyperbrowser(api_key=os.getenv("HYPERBROWSER_API_KEY"))

            kwargs: Dict[str, Any] = {
                "urls": urls,
            }
            if prompt:
                kwargs["prompt"] = prompt
            if schema:
                kwargs["schema"] = schema
            if max_links is not None:
                kwargs["max_links"] = max_links
            if session_options:
                kwargs["session_options"] = session_options

            result = hb_client.extract.start_and_wait(
                params=StartExtractJobParams(**kwargs)
            )
            return result

        try:
            result = await client._with_limits(_call, timeout_ms=timeout_ms)
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            payload = {
                "source": "Hyperbrowser-Extract",
                "raw_data": getattr(result, "model_dump", lambda: getattr(result, "__dict__", {}))(),
                "meta": {
                    "urls": urls,
                    "duration_ms": duration_ms,
                },
            }
            # If SDK has .data/.job_id/.status attributes, attach them
            job_id = getattr(result, "job_id", None) or getattr(result, "jobId", None)
            status = getattr(result, "status", None)
            if job_id:
                payload["meta"]["jobId"] = job_id
            if status:
                payload["meta"]["status"] = status
            return payload
        except asyncio.TimeoutError:
            return {
                "source": "Hyperbrowser-Extract",
                "raw_data": {"error": "timeout"},
                "meta": {"urls": urls},
            }
        except Exception as e:
            return {
                "source": "Hyperbrowser-Extract",
                "raw_data": {"error": str(e)},
                "meta": {"urls": urls},
            }


