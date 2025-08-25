import os
import time
import httpx
import asyncio
import logging
from typing import Any, Dict, Optional, List, Tuple

BASE_URL = "https://irbis.espysys.com/api"

class EspyClient:
    def __init__(self):
        self.api_key = os.getenv("ESPY_API_KEY")
        # Map endpoint -> list of (lookupId, lookupName)
        self._lookup_map: Optional[Dict[str, List[Tuple[int, str]]]] = None
        self._rate_lock = asyncio.Lock()
        self._last_start_ts: Optional[float] = None
        self._min_interval_seconds = 30.0
        self._log = logging.getLogger(__name__)
        # Prefer specific lookupIds when multiple entries share the same endpoint
        self._preferred_lookup_id_by_endpoint: Dict[str, int] = {
            "/api/developer/combined_email": 121,
            "/api/developer/combined_phone": 66,
            "/api/developer/deepweb": 119,
        }

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            ep = self._normalize_endpoint(endpoint)
            r = await client.post(f"{BASE_URL}{ep}", json=payload)
            r.raise_for_status()
            return r.json()

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            ep = self._normalize_endpoint(endpoint)
            r = await client.get(f"{BASE_URL}{ep}")
            r.raise_for_status()
            return r.json()

    def _normalize_endpoint(self, endpoint: str) -> str:
        if endpoint.startswith("/api/"):
            return endpoint[4:]
        return endpoint

    async def _ensure_lookup_map(self) -> None:
        if self._lookup_map is not None:
            return
        if not self.api_key:
            self._lookup_map = {}
            self._log.warning("ESPY key missing; lookupId map disabled")
            return
        url = f"/request-monitor/lookupid-list?key={self.api_key}"
        try:
            data = await self._get(url)
            mapping: Dict[str, List[Tuple[int, str]]] = {}
            if isinstance(data, list):
                for item in data:
                    ep = item.get("endPoint")
                    lid = item.get("lookupId")
                    lname = item.get("lookupName") or ""
                    if isinstance(ep, str) and isinstance(lid, int):
                        mapping.setdefault(ep, []).append((lid, str(lname)))
            self._lookup_map = mapping
            self._log.info("ESPY lookupId map loaded: %d endpoints", len(mapping))
        except Exception:
            self._lookup_map = {}
            self._log.exception("Failed to load ESPY lookupId map")

    async def _respect_rate_limit(self) -> None:
        async with self._rate_lock:
            now = time.monotonic()
            if self._last_start_ts is not None:
                elapsed = now - self._last_start_ts
                if elapsed < self._min_interval_seconds:
                    await asyncio.sleep(self._min_interval_seconds - elapsed)
            self._last_start_ts = time.monotonic()

    async def run_lookup(self, endpoint: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "ESPY_API_KEY not configured."}
        await self._ensure_lookup_map()
        ep_full = endpoint if endpoint.startswith("/api/") else f"/api{endpoint}"
        options = (self._lookup_map or {}).get(ep_full, [])
        lookup_id: Optional[int] = None
        if options:
            pref = self._preferred_lookup_id_by_endpoint.get(ep_full)
            if pref and any(lid == pref for lid, _ in options):
                lookup_id = pref
            else:
                lookup_id = options[0][0]
        if not lookup_id:
            self._log.error("ESPY lookupId missing for endpoint: %s", ep_full)
            return {"error": "LookupId not found for endpoint.", "endpoint": ep_full}
        try:
            await self._respect_rate_limit()
            start_payload = {"key": self.api_key, "lookupId": lookup_id, **input_data}
            self._log.info("ESPY start %s lid=%s payload_keys=%s", ep_full, lookup_id, sorted(list(input_data.keys())))
            start_response = await self._post(endpoint, start_payload)
            job_id = start_response.get("id") or start_response.get("requestId")
            if not job_id:
                self._log.error("ESPY start failed: no id/requestId; resp_keys=%s", list(start_response.keys()))
                return {"error": "Failed to get request handle from ESPY.", "details": start_response}
            # Polling parameters (env configurable)
            delay = float(os.getenv("ESPY_POLL_INTERVAL_SEC", "4"))
            max_attempts = int(os.getenv("ESPY_POLL_MAX_ATTEMPTS", "20"))
            last_response: Optional[Dict[str, Any]] = None
            for _ in range(max_attempts):
                await asyncio.sleep(delay)
                poll_url = f"/request-monitor/api-usage/{job_id}?key={self.api_key}"
                poll_response = await self._get(poll_url)
                last_response = poll_response
                status = poll_response.get("status")
                status_l = str(status).lower() if status is not None else ""
                self._log.info("ESPY poll %s id=%s status=%s", ep_full, job_id, status)
                # Treat multiple terminal statuses as success
                if status_l in {"completed", "finished", "done", "success"}:
                    self._log.info("ESPY done %s id=%s", ep_full, job_id)
                    if isinstance(poll_response, dict):
                        poll_response.setdefault("requestId", job_id)
                    return poll_response
            # Return last response so caller sees current status/data, plus an error note
            return {"error": "Polling timed out for ESPY lookup.", "requestId": job_id, "last": last_response}

    async def poll_request(self, request_id: int) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "ESPY_API_KEY not configured."}
        try:
            poll_url = f"/request-monitor/api-usage/{request_id}?key={self.api_key}"
            resp = await self._get(poll_url)
            if isinstance(resp, dict):
                resp.setdefault("requestId", request_id)
            return resp
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error during ESPY poll: {e.response.status_code}", "details": e.response.text}
        except Exception as e:
            return {"error": f"Unexpected error during ESPY poll: {str(e)}"}
        except httpx.HTTPStatusError as e:
            self._log.error("ESPY HTTP error %s: %s", e.response.status_code, e.response.text[:200])
            return {"error": f"HTTP error during ESPY lookup: {e.response.status_code}", "details": e.response.text}
        except Exception as e:
            self._log.exception("ESPY unexpected error")
            return {"error": f"An unexpected error occurred during ESPY lookup: {str(e)}"}
