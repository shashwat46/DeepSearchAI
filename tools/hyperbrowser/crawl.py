import os
import asyncio
import time
from typing import Dict, Any, List, Optional

from ..base import BaseTool
from .client import HyperbrowserClient


class HyperbrowserCrawlTool(BaseTool):
    @property
    def name(self) -> str:
        return "hyperbrowser_crawl"

    @property
    def stage(self) -> str:
        return "deep"

    def _enabled(self) -> bool:
        return os.getenv("HYPERBROWSER_ENABLE_CRAWL", "true").lower() == "true"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        if not self._enabled():
            return False
        hb: Optional[Dict[str, Any]] = params.get("hyperbrowser")
        if not hb or not isinstance(hb, dict):
            return False
        crawl = hb.get("crawl") or {}
        url: Optional[str] = crawl.get("url")
        return bool(url)

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        client = HyperbrowserClient()
        if not client.is_configured():
            return {"source": "Hyperbrowser-Crawl", "raw_data": {"error": "API key not configured"}}

        hb: Dict[str, Any] = params.get("hyperbrowser") or {}
        p: Dict[str, Any] = hb.get("crawl") or {}

        url: str = p.get("url")
        max_pages: Optional[int] = p.get("max_pages")
        include_patterns: Optional[List[str]] = p.get("include_patterns")
        exclude_patterns: Optional[List[str]] = p.get("exclude_patterns")
        formats: Optional[List[str]] = p.get("formats")
        only_main_content: Optional[bool] = p.get("only_main_content")
        timeout_opt: Optional[int] = p.get("timeout_ms")
        session_options: Dict[str, Any] = (hb.get("session_options") or p.get("session_options") or {})

        overall_timeout_ms = int(os.getenv("HYPERBROWSER_CRAWL_TIMEOUT_MS", os.getenv("HYPERBROWSER_TIMEOUT_MS", "90000")))

        async def _call():
            from hyperbrowser import Hyperbrowser
            from hyperbrowser.models import StartCrawlJobParams
            from hyperbrowser.models import ScrapeOptions

            hb_client = Hyperbrowser(api_key=os.getenv("HYPERBROWSER_API_KEY"))
            kwargs: Dict[str, Any] = {
                "url": url,
            }
            if max_pages is not None:
                kwargs["max_pages"] = max_pages
            if include_patterns:
                kwargs["include_patterns"] = include_patterns
            if exclude_patterns:
                kwargs["exclude_patterns"] = exclude_patterns
            if formats or only_main_content is not None or timeout_opt is not None:
                sopts: Dict[str, Any] = {}
                if formats:
                    sopts["formats"] = formats
                if only_main_content is not None:
                    sopts["only_main_content"] = only_main_content
                if timeout_opt is not None:
                    sopts["timeout"] = timeout_opt
                kwargs["scrape_options"] = ScrapeOptions(**sopts)
            if session_options:
                kwargs["session_options"] = session_options

            return hb_client.crawl.start_and_wait(StartCrawlJobParams(**kwargs))

        start_ts = time.monotonic()
        try:
            result = await client._with_limits(_call, overall_timeout_ms)
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            payload = {
                "source": "Hyperbrowser-Crawl",
                "raw_data": getattr(result, "model_dump", lambda: getattr(result, "__dict__", {}))(),
                "meta": {
                    "urls": [url],
                    "duration_ms": duration_ms,
                },
            }
            job_id = getattr(result, "job_id", None) or getattr(result, "jobId", None)
            status = getattr(result, "status", None)
            if job_id:
                payload["meta"]["jobId"] = job_id
            if status:
                payload["meta"]["status"] = status
            return payload
        except asyncio.TimeoutError:
            return {
                "source": "Hyperbrowser-Crawl",
                "raw_data": {"error": "timeout"},
                "meta": {"urls": [url]},
            }
        except Exception as e:
            return {
                "source": "Hyperbrowser-Crawl",
                "raw_data": {"error": str(e)},
                "meta": {"urls": [url]},
            }


