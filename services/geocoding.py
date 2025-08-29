import os
from typing import Dict, Any, Optional
import httpx


async def geocode_location(text: str, language: Optional[str] = None) -> Dict[str, Any]:
    api_key = os.getenv("OPENCAGE_API_KEY")
    if not api_key or not isinstance(text, str) or not text.strip():
        return {"error": "missing_input_or_key"}
    params = {
        "q": text.strip(),
        "key": api_key,
        "no_annotations": 1,
    }
    if language:
        params["language"] = language
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get("https://api.opencagedata.com/geocode/v1/json", params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return {"error": str(e)}
    results = data.get("results") or []
    if not results:
        return {"error": "no_results"}
    top = results[0]
    comps = top.get("components") or {}
    geometry = top.get("geometry") or {}
    country_code = (comps.get("country_code") or "").upper()
    city = comps.get("city") or comps.get("town") or comps.get("village") or comps.get("suburb") or ""
    state = comps.get("state") or comps.get("region") or ""
    formatted = top.get("formatted") or ""
    confidence = top.get("confidence") or 0
    return {
        "components": {
            "country_code": country_code,
            "country": comps.get("country") or "",
            "state": state,
            "city": city,
            "county": comps.get("county") or "",
            "postcode": comps.get("postcode") or "",
        },
        "geometry": {
            "lat": geometry.get("lat"),
            "lng": geometry.get("lng"),
        },
        "formatted": formatted,
        "confidence": confidence,
        "provider": "OpenCage",
        "raw": top,
    }

def country_to_mkt(country_code: str) -> str:
    mapping = {"IN": "en-IN", "GB": "en-GB", "CA": "en-CA", "AU": "en-AU", "US": "en-US"}
    return mapping.get((country_code or "").upper(), "en-US")


