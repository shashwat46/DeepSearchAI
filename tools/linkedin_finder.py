import os
import re
import json
from typing import Dict, Any, List, Tuple
import httpx
from .base import BaseTool


class LinkedInFinderTool(BaseTool):
    @property
    def name(self) -> str:
        return "linkedin_finder"

    @property
    def stage(self) -> str:
        return "shallow"

    def _enabled(self) -> bool:
        return os.getenv("LINKEDIN_FINDER_ENABLE", "false").lower() == "true"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        api_key = os.getenv("SERPAPI_API_KEY")
        return self._enabled() and bool(api_key) and bool(params.get("name"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.getenv("SERPAPI_API_KEY")
        name = (params.get("name") or "").strip()
        location = (params.get("location") or "").strip()
        company = (params.get("company") or "").strip()
        hint = (params.get("search_hint") or "").strip()
        max_queries = int(os.getenv("LINKEDIN_FINDER_MAX_QUERIES", "4"))
        max_results = int(os.getenv("LINKEDIN_MAX_RESULTS", "3"))
        mkt_default = os.getenv("LINKEDIN_FINDER_MKT_DEFAULT", "en-US")
        timeout_s = int(os.getenv("LINKEDIN_FINDER_TIMEOUT_S", "10"))

        mkt = self._infer_mkt(location) or mkt_default
        queries = self._build_queries(name, company, location, hint)[:max_queries]
        seen: Dict[str, float] = {}

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            for q in queries:
                try:
                    res = await client.get(
                        "https://serpapi.com/search",
                        params={"engine": "bing", "q": q, "api_key": api_key, "mkt": mkt},
                    )
                    res.raise_for_status()
                    data = res.json()
                    items = data.get("organic_results") or []
                    for url, title, snippet in self._extract_linkedin(items):
                        score = self._score(title, snippet, name, company, location)
                        seen[url] = max(seen.get(url, 0.0), score)
                except Exception:
                    continue

        ranked = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)[:max_results]
        candidates = [
            {"url": u, "confidence": round(s, 3)} for u, s in ranked
        ]
        best_url = candidates[0]["url"] if candidates else ""

        return {
            "source": "LinkedIn-Finder",
            "raw_data": {
                "candidates": candidates,
                "best_url": best_url,
                "queries": queries,
                "engine": "bing",
                "mkt": mkt,
            },
        }

    def _build_queries(self, name: str, company: str, city: str, hint: str) -> List[str]:
        parts_name = f'"{name}"' if name else ""
        parts_company = f' "{company}"' if company else ""
        parts_city = f' "{city}"' if city else ""
        parts_ctx = f' "{re.sub(r"\\s+", " ", hint)[:50]}"' if hint else ""
        q1 = f"site:linkedin.com/in {parts_name}{parts_company}{parts_city}{parts_ctx}".strip()
        q2 = f"site:linkedin.com/in {parts_name}{parts_company}".strip()
        q3 = f"site:linkedin.com/in {parts_name}{parts_city}".strip()
        q4 = f"site:linkedin.com/in {parts_name}".strip()
        out = [q1, q2, q3, q4]
        seen = set()
        uniq: List[str] = []
        for q in out:
            if q and q not in seen:
                uniq.append(q)
                seen.add(q)
        return uniq

    def _extract_linkedin(self, items: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
        out: List[Tuple[str, str, str]] = []
        for r in items:
            url = (r.get("link") or r.get("link_url") or "").strip()
            if not url:
                continue
            if "linkedin.com/in/" not in url:
                continue
            clean = url.split("?")[0].rstrip("/")
            title = (r.get("title") or "").strip()
            snippet = (r.get("snippet") or r.get("snippet_highlighted_words") or "")
            if isinstance(snippet, list):
                snippet = " ".join(snippet)
            out.append((clean, title, snippet))
        return out

    def _score(self, title: str, snippet: str, name: str, company: str, city: str) -> float:
        text = f"{title} {snippet}".lower()
        name_norm = re.sub(r"[^a-z ]", "", name.lower())
        text_norm = re.sub(r"[^a-z ]", "", text)
        name_score = 1.0 if name_norm and name_norm in text_norm else 0.6 if all(p in text_norm for p in name_norm.split()[:1]) else 0.0
        comp_score = 0.3 if company and company.lower() in text else 0.0
        city_score = 0.2 if city and city.lower() in text else 0.0
        return max(0.0, min(1.0, 0.5 * name_score + comp_score + city_score))

    def _infer_mkt(self, location: str) -> str:
        loc = (location or "").lower()
        if any(k in loc for k in ["india", "in", "mumbai", "delhi", "chennai", "bangalore", "bengaluru", "hyderabad"]):
            return "en-IN"
        if any(k in loc for k in ["united kingdom", "uk", "london", "manchester", "edinburgh"]):
            return "en-GB"
        if any(k in loc for k in ["canada", "toronto", "vancouver", "montreal"]):
            return "en-CA"
        if any(k in loc for k in ["australia", "sydney", "melbourne", "brisbane"]):
            return "en-AU"
        return ""


