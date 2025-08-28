import os
from typing import Dict, Any
import requests
from .base import BaseTool


class XVerifyTool(BaseTool):
    @property
    def name(self) -> str:
        return "x_verify"

    @property
    def stage(self) -> str:
        return "shallow"

    def _enabled(self) -> bool:
        return os.getenv("X_VERIFY_ENABLE", "false").lower() == "true"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        if not self._enabled():
            return False
        if not os.getenv("SCRAPINGDOG_API_KEY"):
            return False
        best = params.get("x_finder_best_url") or ""
        return bool(best)

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.getenv("SCRAPINGDOG_API_KEY")
        url = params.get("x_finder_best_url")
        timeout_s = int(os.getenv("X_VERIFY_TIMEOUT_S", "20"))
        try:
            r = requests.get(
                "https://api.scrapingdog.com/x/profile",
                params={
                    "api_key": api_key,
                    "profileId": url,
                    "parsed": "true",
                },
                timeout=timeout_s,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            return {"source": "X-Verify", "raw_data": {"error": str(e), "url": url}}

        return {"source": "X-Verify", "raw_data": data}


