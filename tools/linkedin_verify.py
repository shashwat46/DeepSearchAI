import os
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup
from .base import BaseTool


class LinkedInVerifyTool(BaseTool):
    @property
    def name(self) -> str:
        return "linkedin_verify"

    @property
    def stage(self) -> str:
        return "shallow"

    def _enabled(self) -> bool:
        return os.getenv("LINKEDIN_VERIFY_ENABLE", "false").lower() == "true"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        if not self._enabled():
            return False
        if not os.getenv("SCRAPINGDOG_API_KEY"):
            return False
        last = params.get("linkedin_finder_best_url") or ""
        return bool(last)

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.getenv("SCRAPINGDOG_API_KEY")
        url = params.get("linkedin_finder_best_url")
        timeout_s = int(os.getenv("LINKEDIN_VERIFY_TIMEOUT_S", "30"))
        country = (params.get("country") or os.getenv("LINKEDIN_VERIFY_COUNTRY", "US"))
        try:
            r = requests.get(
                "https://api.scrapingdog.com/scrape",
                params={
                    "api_key": api_key,
                    "url": url,
                    "render_js": "true",
                    "retry": 2,
                    "country": country,
                },
                timeout=timeout_s,
            )
            r.raise_for_status()
            html = r.text
        except Exception as e:
            return {"source": "LinkedIn-Verify", "raw_data": {"error": str(e), "url": url}}

        soup = BeautifulSoup(html, "html.parser")
        name = self._text(soup.select_one("h1"))
        headline = self._text(soup.select_one("div.text-body-medium"))
        location = self._guess_location(soup)
        company = self._guess_company(soup)
        photo = self._guess_photo(soup)

        return {
            "source": "LinkedIn-Verify",
            "raw_data": {
                "url": url,
                "name": name,
                "headline": headline,
                "location": location,
                "company": company,
                "photo": photo,
            },
        }

    def _text(self, el) -> str:
        return el.get_text(strip=True) if el else ""

    def _guess_location(self, soup) -> str:
        el = soup.find(string=lambda s: isinstance(s, str) and ", " in s and len(s) <= 64)
        return (el or "").strip()

    def _guess_company(self, soup) -> str:
        el = soup.find("span", string=lambda s: isinstance(s, str) and any(k in s.lower() for k in ["at ", "@"]))
        return (el.get_text(strip=True) if el else "").replace("at ", "").replace("@", "").strip()

    def _guess_photo(self, soup) -> str:
        img = soup.select_one('img[src*="profile"][src^="https://media."]') or soup.select_one('img[src*="profile-displayphoto"]')
        return img.get("src").strip() if img and img.get("src") else ""


