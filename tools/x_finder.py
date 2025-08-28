import os
import re
from typing import Dict, Any, List, Tuple
import httpx
from .base import BaseTool


class XFinderTool(BaseTool):
    @property
    def name(self) -> str:
        return "x_finder"

    @property
    def stage(self) -> str:
        return "shallow"

    def _enabled(self) -> bool:
        return os.getenv("X_FINDER_ENABLE", "false").lower() == "true"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        api_key = os.getenv("SERPAPI_API_KEY")
        return self._enabled() and bool(api_key) and bool(params.get("name") or params.get("username"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.getenv("SERPAPI_API_KEY")
        name = (params.get("name") or "").strip()
        username = (params.get("username") or "").strip().lstrip("@")
        location = (params.get("location") or "").strip()
        company = (params.get("company") or "").strip()
        context = (params.get("free_text_context") or "").strip()
        max_queries = int(os.getenv("X_FINDER_MAX_QUERIES", "4"))
        max_results = int(os.getenv("X_MAX_RESULTS", "3"))
        mkt_default = os.getenv("X_FINDER_MKT_DEFAULT", "en-US")
        timeout_s = int(os.getenv("X_FINDER_TIMEOUT_S", "10"))

        mkt = self._infer_mkt(location) or mkt_default
        queries = self._build_queries(name, username, company, location, context)[:max_queries]
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
                    for url, title, snippet in self._extract_x(items):
                        score = self._score(title, snippet, name, username, company, location)
                        seen[url] = max(seen.get(url, 0.0), score)
                except Exception:
                    continue

        ranked = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)[:max_results]
        candidates = [
            {"url": u, "confidence": round(s, 3)} for u, s in ranked
        ]
        best_url = candidates[0]["url"] if candidates else ""

        return {
            "source": "X-Finder",
            "raw_data": {
                "candidates": candidates,
                "best_url": best_url,
                "queries": queries,
                "engine": "bing",
                "mkt": mkt,
            },
        }

    def _build_queries(self, name: str, username: str, company: str, city: str, context: str) -> List[str]:
        n = f'"{name}"' if name else ""
        u = f' "{username}"' if username else ""
        c = f' "{company}"' if company else ""
        ct = f' "{city}"' if city else ""
        ctx = ""
        if context:
            s = re.sub(r"\s+", " ", context)[:120]
            ctx = f' "{s}"'
        dorks = [
            f"site:twitter.com {n}{u}{c}{ct}{ctx}".strip(),
            f"site:x.com {n}{u}{c}{ct}{ctx}".strip(),
            f"site:twitter.com {n}{u}{c}".strip(),
            f"site:x.com {n}{u}{c}".strip(),
            f"site:twitter.com {n}{u}".strip(),
            f"site:x.com {n}{u}".strip(),
        ]
        uniq: List[str] = []
        seen = set()
        for q in dorks:
            if q and q not in seen:
                uniq.append(q)
                seen.add(q)
        return uniq

    def _extract_x(self, items: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
        out: List[Tuple[str, str, str]] = []
        for r in items:
            url = (r.get("link") or r.get("link_url") or "").strip()
            if not url:
                continue
            if not ("twitter.com/" in url or "x.com/" in url):
                continue
            if any(seg in url for seg in ["/status/", "/i/", "/login", "/home", "/intent/"]):
                continue
            clean = url.split("?")[0].rstrip("/")
            title = (r.get("title") or "").strip()
            snippet = (r.get("snippet") or r.get("snippet_highlighted_words") or "")
            if isinstance(snippet, list):
                snippet = " ".join(snippet)
            out.append((clean, title, snippet))
        return out

    def _score(self, title: str, snippet: str, name: str, username: str, company: str, city: str) -> float:
        text = f"{title} {snippet}".lower()
        name_norm = re.sub(r"[^a-z ]", "", name.lower())
        text_norm = re.sub(r"[^a-z ]", "", text)
        name_score = 1.0 if name_norm and name_norm in text_norm else 0.6 if name_norm and all(p in text_norm for p in name_norm.split()[:1]) else 0.0
        user_score = 0.4 if username and username.lower() in text else 0.0
        comp_score = 0.2 if company and company.lower() in text else 0.0
        city_score = 0.2 if city and city.lower() in text else 0.0
        score = 0.5 * name_score + user_score + comp_score + city_score
        return max(0.0, min(1.0, score))

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


