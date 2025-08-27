import re
import html as _html
import requests
from datetime import datetime, timezone
from typing import Dict, Any

from .base import BaseTool


_PROVIDER_BASE = "https://gmail-osint.activetk.jp"


class GHuntTool(BaseTool):
    @property
    def name(self) -> str:
        return "GHunt"

    @property
    def stage(self) -> str:
        return "shallow"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        email = (params.get("email") or "").strip().lower()
        return bool(email.endswith("@gmail.com"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        email: str = (params.get("email") or "").strip().lower()
        try:
            local_part, domain = email.split("@", 1)
        except ValueError:
            return {"source": "GHunt", "raw_data": {"error": "invalid_email"}}
        if domain != "gmail.com" or not local_part:
            return {"source": "GHunt", "raw_data": {"error": "unsupported_domain"}}

        url = f"{_PROVIDER_BASE}/{local_part}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            return {"source": "GHunt", "raw_data": {"error": str(e)}}

        profile_image_url = _extract_profile_image_url(html)
        gaia_id = _extract_gaia_id(html)
        reviews_url = _extract_reviews_url(html, gaia_id)
        reviews_count = 0 if _has_no_reviews_hint(html) else None
        custom_profile_picture = _has_custom_profile_picture_hint(html)

        google_osint: Dict[str, Any] = {
            "gaia_id": gaia_id,
            "profile_image_url": profile_image_url,
            "reviews_url": reviews_url,
            "reviews_count": reviews_count,
            "custom_profile_picture": custom_profile_picture,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": _PROVIDER_BASE,
        }

        return {
            "source": "GHunt",
            "raw_data": {
                "email": email,
                "google_osint": google_osint,
            },
            "meta": {"provider_url": url},
        }


def _extract_profile_image_url(html: str) -> str:
    # Unescape HTML entities first (e.g., =&gt;)
    text = _html.unescape(html)
    # Prefer the explicit marker line
    m = re.search(r'''Custom\s+profile\s+picture\s*!.*?=>\s*(https://[^\s<>"']+)''', text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1)
    # Fallback: known Google avatar hosts
    hosts = [
        "lh3.googleusercontent.com",
        "lh5.googleusercontent.com",
        "lh6.googleusercontent.com",
        "yt3.ggpht.com",
    ]
    for host in hosts:
        m2 = re.search(rf"https://{re.escape(host)}/[^\s\"'<>]+", text)
        if m2:
            return m2.group(0)
    return ""


def _extract_gaia_id(html: str) -> str:
    m = re.search(r"Gaia ID\s*:\s*(\d+)", html)
    return m.group(1) if m else ""


def _extract_reviews_url(html: str, gaia_id: str) -> str:
    m = re.search(r"https://www\\.google\\.com/maps/contrib/(\d+)/reviews", html)
    if m:
        return m.group(0)
    if gaia_id:
        return f"https://www.google.com/maps/contrib/{gaia_id}/reviews"
    return ""


def _has_no_reviews_hint(html: str) -> bool:
    return "No review." in html


def _has_custom_profile_picture_hint(html: str) -> bool:
    return "Custom profile picture" in html


