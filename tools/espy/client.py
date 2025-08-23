import os
import httpx
import asyncio
from typing import Any, Dict

BASE_URL = "https://irbis.espysys.com/api"

class EspyClient:
    def __init__(self):
        self.api_key = os.getenv("ESPY_API_KEY")

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{BASE_URL}{endpoint}", json=payload)
            r.raise_for_status()
            return r.json()

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{BASE_URL}{endpoint}")
            r.raise_for_status()
            return r.json()

    async def run_lookup(self, endpoint: str, value: str, lookup_id: int) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "ESPY_API_KEY not configured."}
        
        try:
            start_payload = {"key": self.api_key, "value": value, "lookupId": lookup_id}
            start_response = await self._post(endpoint, start_payload)
            
            request_id = start_response.get("requestId")
            if not request_id:
                return {"error": "Failed to get request ID from ESPY.", "details": start_response}

            for _ in range(10):  # Poll up to 10 times (30 seconds total)
                await asyncio.sleep(3)
                poll_url = f"/request-monitor/api-usage/{request_id}?key={self.api_key}"
                poll_response = await self._get(poll_url)
                if poll_response.get("status") == "completed":
                    return poll_response
            
            return {"error": "Polling timed out for ESPY lookup."}

        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error during ESPY lookup: {e.response.status_code}", "details": e.response.text}
        except Exception as e:
            return {"error": f"An unexpected error occurred during ESPY lookup: {str(e)}"}
