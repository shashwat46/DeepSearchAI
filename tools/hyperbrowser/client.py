import os
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from schemas import (
    HyperbrowserSessionOptions,
    HyperbrowserExtractParams,
    HyperbrowserScrapeParams,
    HyperbrowserCrawlParams,
)


class HyperbrowserClient:
    def __init__(self):
        self._api_key = os.getenv("HYPERBROWSER_API_KEY")
        concurrency = int(os.getenv("HYPERBROWSER_CONCURRENCY", "2"))
        self._sem = asyncio.Semaphore(concurrency)

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def _with_limits(self, coro_fn, timeout_ms: int) -> Any:
        async with self._sem:
            timeout_s = max(1, int(timeout_ms) // 1000) if timeout_ms else None
            if timeout_s:
                return await asyncio.wait_for(coro_fn(), timeout=timeout_s)
            return await coro_fn()

    def _build_session_opts(self, so: Optional[HyperbrowserSessionOptions]) -> Dict[str, Any]:
        if not so:
            return {}
        payload: Dict[str, Any] = {}
        if so.use_proxy is not None:
            payload["use_proxy"] = so.use_proxy
        if so.solve_captchas is not None:
            payload["solve_captchas"] = so.solve_captchas
        if so.proxy_country:
            payload["proxy_country"] = so.proxy_country
        if so.locales:
            payload["locales"] = so.locales
        if so.use_stealth is not None:
            payload["use_stealth"] = so.use_stealth
        if so.adblock is not None:
            payload["adblock"] = so.adblock
        if so.trackers is not None:
            payload["trackers"] = so.trackers
        if so.annoyances is not None:
            payload["annoyances"] = so.annoyances
        if so.accept_cookies is not None:
            payload["accept_cookies"] = so.accept_cookies
        if so.operating_systems:
            payload["operating_systems"] = so.operating_systems
        if so.device:
            payload["device"] = so.device
        if so.screen_width is not None and so.screen_height is not None:
            payload["screen"] = {"width": so.screen_width, "height": so.screen_height}
        if so.wait_for_ms is not None:
            payload["wait_for"] = so.wait_for_ms
        return payload

    # Placeholders for tools to call; these will be implemented using the SDK in execute paths.
    async def extract(self, params: HyperbrowserExtractParams) -> Dict[str, Any]:
        return {
            "error": "not_implemented",
            "message": "SDK call should be implemented in tool using client configuration",
        }

    async def scrape(self, params: HyperbrowserScrapeParams) -> Dict[str, Any]:
        return {
            "error": "not_implemented",
            "message": "SDK call should be implemented in tool using client configuration",
        }

    async def crawl(self, params: HyperbrowserCrawlParams) -> Dict[str, Any]:
        return {
            "error": "not_implemented",
            "message": "SDK call should be implemented in tool using client configuration",
        }


