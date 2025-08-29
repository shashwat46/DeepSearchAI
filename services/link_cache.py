import time
from typing import Dict, Optional


class LinkCache:
    def __init__(self, ttl_seconds: int = 900):
        self._ttl = ttl_seconds
        self._data: Dict[str, Dict[str, str]] = {}
        self._ts: Dict[str, float] = {}

    def _now(self) -> float:
        return time.monotonic()

    def _key(self, platform: str, fingerprint: str) -> str:
        return f"{platform}:{fingerprint}"

    def set_best(self, platform: str, fingerprint: str, url: str) -> None:
        k = self._key(platform, fingerprint)
        self._data[k] = {"url": url}
        self._ts[k] = self._now()

    def get_best(self, platform: str, fingerprint: str) -> Optional[str]:
        k = self._key(platform, fingerprint)
        ts = self._ts.get(k)
        if ts is None:
            return None
        if self._now() - ts > self._ttl:
            self._data.pop(k, None)
            self._ts.pop(k, None)
            return None
        rec = self._data.get(k) or {}
        url = rec.get("url")
        return url if isinstance(url, str) and url else None

    @staticmethod
    def fingerprint(params: Dict[str, str]) -> str:
        email = (params.get("email") or "").strip().lower()
        if email:
            return f"email:{email}"
        phone = (params.get("phone") or "").strip()
        if phone:
            return f"phone:{phone}"
        name = (params.get("name") or "").strip().lower()
        loc = (params.get("location") or "").strip().lower()
        if name or loc:
            return f"name_loc:{name}|{loc}"
        return "anon"


