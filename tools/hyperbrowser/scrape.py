import os
import asyncio
import time
from typing import Dict, Any, List, Optional

from ..base import BaseTool
from .client import HyperbrowserClient


class HyperbrowserScrapeTool(BaseTool):
    @property
    def name(self) -> str:
        return "hyperbrowser_scrape"

    @property
    def stage(self) -> str:
        return "deep"

    def _enabled(self) -> bool:
        return os.getenv("HYPERBROWSER_ENABLE_SCRAPE", "true").lower() == "true"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        if not self._enabled():
            return False
        hb: Optional[Dict[str, Any]] = params.get("hyperbrowser")
        if not hb or not isinstance(hb, dict):
            return False
        scrape = hb.get("scrape") or {}
        urls: Optional[List[str]] = scrape.get("urls")
        return bool(urls)

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        client = HyperbrowserClient()
        if not client.is_configured():
            return {"source": "Hyperbrowser-Scrape", "raw_data": {"error": "API key not configured"}}

        hb: Dict[str, Any] = params.get("hyperbrowser") or {}
        p: Dict[str, Any] = hb.get("scrape") or {}

        urls: List[str] = p.get("urls") or []
        formats: Optional[List[str]] = p.get("formats")
        only_main_content: Optional[bool] = p.get("only_main_content")
        timeout_opt: Optional[int] = p.get("timeout_ms")
        session_options: Dict[str, Any] = (hb.get("session_options") or p.get("session_options") or {})

        overall_timeout_ms = int(os.getenv("HYPERBROWSER_SCRAPE_TIMEOUT_MS", os.getenv("HYPERBROWSER_TIMEOUT_MS", "30000")))

        async def _single(url: str):
            from hyperbrowser import Hyperbrowser
            from hyperbrowser.models import StartScrapeJobParams, ScrapeOptions

            hb_client = Hyperbrowser(api_key=os.getenv("HYPERBROWSER_API_KEY"))
            scrape_options: Dict[str, Any] = {}
            if formats:
                scrape_options["formats"] = formats
            if only_main_content is not None:
                scrape_options["only_main_content"] = only_main_content
            if timeout_opt is not None:
                scrape_options["timeout"] = timeout_opt

            kwargs: Dict[str, Any] = {
                "url": url,
            }
            if scrape_options:
                kwargs["scrape_options"] = ScrapeOptions(**scrape_options)
            if session_options:
                kwargs["session_options"] = session_options

            return hb_client.scrape.start_and_wait(StartScrapeJobParams(**kwargs))

        async def _batch(url_list: List[str]):
            from hyperbrowser import Hyperbrowser
            from hyperbrowser.models.scrape import StartBatchScrapeJobParams, ScrapeOptions

            hb_client = Hyperbrowser(api_key=os.getenv("HYPERBROWSER_API_KEY"))
            kwargs: Dict[str, Any] = {
                "urls": url_list,
            }
            if formats or only_main_content is not None or timeout_opt is not None:
                sopts: Dict[str, Any] = {}
                if formats:
                    sopts["formats"] = formats
                if only_main_content is not None:
                    sopts["only_main_content"] = only_main_content
                if timeout_opt is not None:
                    sopts["timeout"] = timeout_opt
                kwargs["scrape_options"] = ScrapeOptions(**sopts)

            return hb_client.scrape.batch.start_and_wait(StartBatchScrapeJobParams(**kwargs))

        start_ts = time.monotonic()
        try:
            if len(urls) == 1:
                result = await client._with_limits(lambda: _single(urls[0]), overall_timeout_ms)
            else:
                result = await client._with_limits(lambda: _batch(urls), overall_timeout_ms)

            duration_ms = int((time.monotonic() - start_ts) * 1000)
            payload = {
                "source": "Hyperbrowser-Scrape",
                "raw_data": getattr(result, "model_dump", lambda: getattr(result, "__dict__", {}))(),
                "meta": {
                    "urls": urls,
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
                "source": "Hyperbrowser-Scrape",
                "raw_data": {"error": "timeout"},
                "meta": {"urls": urls},
            }
        except Exception as e:
            return {
                "source": "Hyperbrowser-Scrape",
                "raw_data": {"error": str(e)},
                "meta": {"urls": urls},
            }


