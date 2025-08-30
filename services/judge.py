import os
from typing import Dict, Any, List, Tuple
from schemas import FinalProfile
from services.llm import get_gemini_model


class ProfileJudge:
    def __init__(self) -> None:
        self.model_name = os.getenv("GEMINI_JUDGE_MODEL", os.getenv("GEMINI_SYNTHESIS_MODEL", "gemini-2.5-pro"))

    async def judge(self, profile: FinalProfile, raw: List[Dict[str, Any]]) -> Dict[str, Any]:
        model = get_gemini_model(model_name=self.model_name)
        if model is None:
            return self._fallback(profile, raw)
        prompt = self._build_prompt(profile, raw)
        try:
            resp = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
            data = self._safe_json(resp.text)
            if not isinstance(data, dict):
                return self._fallback(profile, raw)
            judged = data.get("judged_profile") or {}
            try:
                judged_profile = FinalProfile.model_validate(judged)
            except Exception:
                return self._fallback(profile, raw)
            return {
                "judged_profile": judged_profile,
                "field_confidence": data.get("field_confidence") or {},
                "provenance": data.get("provenance") or {},
                "warnings": data.get("warnings") or [],
            }
        except Exception:
            return self._fallback(profile, raw)

    def _build_prompt(self, profile: FinalProfile, raw: List[Dict[str, Any]]) -> str:
        import json as _json
        policy = {
            "source_priority": ["LinkedIn-Verify", "ESPY", "GitHub", "Numverify", "OpenCage", "Holehe-Modules", "GHunt", "X-Verify", "LinkedIn-Finder", "X-Finder"],
            "rules": [
                "Use only facts present in raw evidence; do not invent data.",
                "If a field in the profile lacks any supporting evidence, drop it.",
                "Resolve conflicts by source_priority; if tied, prefer majority agreement.",
                "Provide confidence 0.0-1.0 per field based on source strength and agreement.",
                "Provide provenance listing sources that support each field value.",
                "Return JSON only with judged_profile, field_confidence, provenance, warnings.",
            ],
        }
        return (
            "You are a strict validator. Sanitize a person profile using raw evidence.\n"
            "Follow policy exactly. If unknown, omit. No speculation.\n\n"
            f"Policy:\n{_json.dumps(policy, separators=(",", ":"))}\n\n"
            f"InputProfile:\n{profile.model_dump_json()}\n\n"
            f"RawEvidence:\n{_json.dumps(raw, default=str) }\n\n"
            "Output schema strictly:\n"
            "{\n  \"judged_profile\": {\"full_name\": str, \"summary\": str, \"locations\": [str], \"employment_history\": [object]},\n"
            "  \"field_confidence\": {str: float},\n  \"provenance\": {str: [str]},\n  \"warnings\": [str]\n}\n"
        )

    def _safe_json(self, text: str) -> Any:
        try:
            import json as _json
            return _json.loads(text or "{}")
        except Exception:
            return {}

    def _fallback(self, profile: FinalProfile, raw: List[Dict[str, Any]]) -> Dict[str, Any]:
        prov: Dict[str, List[str]] = {}
        conf: Dict[str, float] = {}
        sources = [item.get("source") or "" for item in raw]
        prov["full_name"] = [s for s in sources if s in {"LinkedIn-Verify", "GitHub"}] or sources
        conf["full_name"] = 0.9 if "LinkedIn-Verify" in prov["full_name"] else 0.7
        for loc in (profile.locations or []):
            prov_key = f"locations::{loc}"
            prov[prov_key] = [s for s in sources if s in {"LinkedIn-Verify", "OpenCage", "user_input", "GitHub"}] or sources
            conf[prov_key] = 0.85 if "OpenCage" in prov[prov_key] else 0.7
        return {
            "judged_profile": profile,
            "field_confidence": conf,
            "provenance": prov,
            "warnings": [],
        }


