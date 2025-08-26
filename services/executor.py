import os
from typing import Dict, Any, List

from schemas import PlanResponse
from tools.hyperbrowser.scrape import HyperbrowserScrapeTool

_ALLOWED_HOSTS = set(
    (os.getenv("SCRAPE_ALLOWLIST_HOSTS", "github.com,x.com,medium.com,dev.to").split(","))
)


def _is_host_allowed(url: str) -> bool:
    try:
        from urllib.parse import urlparse

        host = urlparse(url).hostname or ""
        return any(host.endswith(h.strip()) for h in _ALLOWED_HOSTS if h.strip())
    except Exception:
        return False


def _filter_urls(urls: List[str], limit: int) -> List[str]:
    out: List[str] = []
    for u in urls:
        if len(out) >= limit:
            break
        if isinstance(u, str) and _is_host_allowed(u):
            out.append(u)
    return out


async def execute_plan_scrape_only(plan: PlanResponse) -> List[Dict[str, Any]]:
    max_urls = int(os.getenv("SCRAPE_MAX_URLS_PER_REQUEST", "5"))
    per_url_timeout_ms = int(os.getenv("HYPERBROWSER_SCRAPE_TIMEOUT_MS", os.getenv("HYPERBROWSER_TIMEOUT_MS", "30000")))

    results: List[Dict[str, Any]] = []
    scrape_tool = HyperbrowserScrapeTool()

    for step in plan.steps:
        if step.tool != "hyperbrowser_scrape":
            continue
        urls = step.inputs.get("urls") or []
        if not isinstance(urls, list) or not urls:
            continue
        filtered = _filter_urls(urls, max_urls)
        if not filtered:
            results.append({"source": "Hyperbrowser-Scrape", "raw_data": {"error": "no_allowed_urls"}, "meta": {"urls": urls}})
            continue
        params: Dict[str, Any] = {
            "hyperbrowser": {
                "scrape": {
                    "urls": filtered,
                    "formats": step.inputs.get("formats") or ["markdown", "links"],
                    "only_main_content": bool(step.inputs.get("only_main_content", True)),
                    "timeout_ms": per_url_timeout_ms,
                }
            }
        }
        try:
            result = await scrape_tool.execute(params)
            results.append(result)
        except Exception as e:
            results.append({"source": "Hyperbrowser-Scrape", "raw_data": {"error": str(e)}, "meta": {"urls": filtered}})

    return results


