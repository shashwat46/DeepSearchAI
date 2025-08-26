import json
from typing import Dict, Any
from schemas import PlanResponse
from services.llm import get_gemini_model

_TOOL_MANIFEST = {
    "function_declarations": [
        {
            "name": "hyperbrowser_scrape",
            "description": "Fetch content for one or many URLs; prefer formats ['markdown','links'] and only_main_content=true.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "urls": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "formats": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "only_main_content": {"type": "BOOLEAN"},
                    "timeout_ms": {"type": "NUMBER"}
                },
                "required": ["urls"]
            }
        },
        {
            "name": "hyperbrowser_extract",
            "description": "Extract structured data from URLs via schema or prompt.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "urls": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "schema": {"type": "OBJECT"},
                    "prompt": {"type": "STRING"},
                    "max_links": {"type": "NUMBER"}
                },
                "required": ["urls"]
            }
        },
        {
            "name": "hyperbrowser_crawl",
            "description": "Constrained crawl of a site to a small number of pages.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "url": {"type": "STRING"},
                    "max_pages": {"type": "NUMBER"},
                    "include_patterns": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "exclude_patterns": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "formats": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "only_main_content": {"type": "BOOLEAN"},
                    "timeout_ms": {"type": "NUMBER"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "espy_email",
            "description": "High-cost email enrichment; use only after strong identity match.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"email": {"type": "STRING"}},
                "required": ["email"]
            }
        },
        {
            "name": "espy_phone",
            "description": "High-cost phone enrichment; use only after strong identity match.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"phone": {"type": "STRING"}},
                "required": ["phone"]
            }
        },
        {
            "name": "holehe_cli",
            "description": "Discover services linked to an email.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"email": {"type": "STRING"}},
                "required": ["email"]
            }
        },
        {
            "name": "numverify",
            "description": "Validate phone format and metadata.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"phone": {"type": "STRING"}},
                "required": ["phone"]
            }
        },
        {
            "name": "github",
            "description": "Scrape GitHub by username.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"username": {"type": "STRING"}},
                "required": ["username"]
            }
        }
    ]
}

_DEFAULT_BUDGET = {"max_steps": 5, "max_runtime_s": 60}


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        end = s.rfind("```")
        if end > 3:
            inner = s[3:end]
            # Remove optional language tag
            first_newline = inner.find("\n")
            if first_newline != -1:
                inner = inner[first_newline + 1 :]
            return inner.strip()
    return s


def _extract_json_object(s: str) -> str:
    s = _strip_code_fences(s)
    start = s.find("{")
    if start == -1:
        return s
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return s[start:]


async def generate_plan(stage: str, params: Dict[str, Any]) -> PlanResponse:
    model = get_gemini_model(model_name="gemini-2.5-flash")
    if model is None:
        return PlanResponse(steps=[], finish_if="Model unavailable", budget=_DEFAULT_BUDGET)
    guidance = {
        "stage": stage,
        "budget": _DEFAULT_BUDGET,
        "policy": {
            "prefer": ["hyperbrowser_scrape", "github", "numverify", "holehe_cli"],
            "use_crawl_only_if": "domain is personal/company and you need multiple pages",
            "use_espy_only_if": "email/phone has medium-high confidence",
            "allowlist_hint": ["github.com","x.com","linkedin.com","medium.com","dev.to","scholar.google.com","orcid.org"]
        }
    }
    prompt = f"""
You produce a minimal execution plan in JSON. No execution.

Context:
{json.dumps({"stage": stage, "inputs": params}, separators=(",", ":"))}

Tool manifest:
{json.dumps(_TOOL_MANIFEST, separators=(",", ":"))}

Guidance:
{json.dumps(guidance, separators=(",", ":"))}

Output JSON schema:
{{
  "steps": [{{"tool": "string", "inputs": {{}}, "why": "string", "success_if": "string"}}],
  "finish_if": "string",
  "budget": {{"max_steps": "number", "max_runtime_s": "number"}}
}}

Rules:
- Keep steps ≤ budget.max_steps.
- Minimize cost. Prefer scrape→extract. Use crawl only if necessary.
- Use allowlisted domains when suggesting URLs.
- If inputs are insufficient for a tool, omit that step.
Return only JSON.
"""
    resp = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
    try:
        return PlanResponse.model_validate_json(resp.text)
    except Exception:
        try:
            import json as _json

            raw = _extract_json_object(getattr(resp, "text", ""))
            obj = _json.loads(raw)
            return PlanResponse.model_validate(obj)
        except Exception:
            return PlanResponse(steps=[], finish_if="Invalid plan", budget=_DEFAULT_BUDGET)


