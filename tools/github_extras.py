import os
import re
import requests
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base import BaseTool


class GitHubExtrasTool(BaseTool):
    @property
    def name(self) -> str:
        return "github_extras"

    @property
    def stage(self) -> str:
        return "shallow"

    def _enabled(self) -> bool:
        return os.getenv("GITHUB_EXTRAS_ENABLE", "false").lower() == "true"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return self._enabled() and bool(params.get("username"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        username = params.get("username")
        timeout = int(os.getenv("GITHUB_EXTRAS_TIMEOUT", "10"))
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://github.com/{username}"
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
        except Exception as e:
            return {"source": "GitHub-Extras", "raw_data": {"error": str(e), "username": username}}

        soup = BeautifulSoup(resp.content, "html.parser")
        website = self._get_website(soup)
        domain = self._domain_from_url(website) if website else None
        company = self._text(soup.select_one('[itemprop="worksFor"]'))
        location = self._text(soup.select_one('[itemprop="homeLocation"]'))
        email = self._get_email(soup)
        twitter = self._get_social(soup, ["twitter.com", "x.com"]) or self._handle_from_bio(soup)
        linkedin = self._get_social(soup, ["linkedin.com"]) 
        orgs = self._get_orgs(soup)

        data = {
            "username": username,
            "website": website,
            "domain": domain,
            "company": company,
            "location": location,
            "email": email,
            "twitter": twitter,
            "linkedin": linkedin,
            "organizations": orgs,
        }
        return {"source": "GitHub-Extras", "raw_data": data}

    def _text(self, el) -> str:
        return el.get_text(strip=True) if el else ""

    def _get_website(self, soup) -> str:
        el = soup.select_one('[data-test-selector="profile-website-url"]')
        if el and el.get("href"):
            return el.get("href").strip()
        link = soup.select_one('[data-bio-text] a[href]')
        if link and isinstance(link.get("href"), str):
            href = link.get("href")
            if any(k in href for k in ["http://", "https://", ".", "blog", "portfolio", "medium.com", "dev.to"]):
                return href.strip()
        return ""

    def _get_email(self, soup) -> str:
        el = soup.select_one('[itemprop="email"]')
        if el:
            return self._text(el)
        bio = soup.select_one('[data-bio-text]')
        if bio:
            m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", bio.get_text())
            if m:
                return m.group(0)
        return ""

    def _get_social(self, soup, hosts: List[str]) -> str:
        for a in soup.select('[data-bio-text] a[href], a[href]'):
            href = a.get("href") or ""
            if any(h in href for h in hosts):
                return href.strip()
        return ""

    def _handle_from_bio(self, soup) -> str:
        bio = soup.select_one('[data-bio-text]')
        if not bio:
            return ""
        m = re.search(r"@([A-Za-z0-9_]{1,30})\b", bio.get_text())
        if m:
            return "@" + m.group(1)
        return ""

    def _get_orgs(self, soup) -> List[str]:
        out: List[str] = []
        for a in soup.select('[data-test-selector="profile-orgs"] a[href]'):
            href = a.get("href") or ""
            if href.startswith("/"):
                slug = href.strip("/")
                if slug and slug not in out:
                    out.append(slug)
        return out

    def _domain_from_url(self, url_str: str) -> str:
        try:
            p = urlparse(url_str)
            host = p.netloc or ""
            if host.startswith("www."):
                host = host[4:]
            return host
        except Exception:
            return ""


