from typing import List, Dict, Any, Optional
import logging
from schemas import SearchQuery, FinalProfile, Candidate
from .ai_agent import parse_user_request, synthesize_profile
from tools.registry import ToolRegistry
import phonenumbers


class SearchOrchestrator:
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self._log = logging.getLogger(__name__)

    async def perform_shallow_search(self, query: SearchQuery) -> Dict[str, Any]:
        params = query.model_dump(exclude_none=True)
        self._log.info("Shallow input keys=%s", list(params.keys()))
        if query.free_text_context:
            extracted = await parse_user_request(query.free_text_context)
            for k, v in extracted.model_dump(exclude_none=True).items():
                params.setdefault(k, v)
        self._log.info("Shallow merged keys=%s", list(params.keys()))
        raw_results = await self.tool_registry.execute_tools(params, stage="shallow")
        candidates = self._build_candidates_from_shallow(raw_results, params)
        self._log.info("Shallow candidates=%d", len(candidates))
        return {"candidates": candidates, "raw": raw_results}

    async def perform_deep_search(self, candidate: Candidate) -> Dict[str, Any]:
        params = candidate.model_dump(exclude_none=True)
        self._log.info("Deep input candidate keys=%s", list(params.keys()))
        deep_results = await self.tool_registry.execute_tools(params, stage="deep")
        agg = [{"source": "candidate", "raw_data": params}] + deep_results
        profile = await synthesize_profile(agg)
        return {"profile": profile, "raw": deep_results}

    def _build_candidates_from_shallow(self, raw_results: List[Dict[str, Any]], seed_params: Dict[str, Any]) -> List[Candidate]:
        merged: Dict[str, Dict[str, Any]] = {}
        extras_by_key: Dict[str, Dict[str, Any]] = {}
        for result in raw_results:
            if result.get("error"):
                continue
            data = result.get("raw_data") or {}
            # Attach Holehe extras by email key
            if result.get("source") == "Holehe":
                email = (data.get("email") or "").strip().lower()
                if email:
                    key = f"email:{email}"
                    ex = extras_by_key.setdefault(key, {})
                    if isinstance(data.get("used_services"), list):
                        ex["used_services"] = data["used_services"]
                    if isinstance(data.get("used_service_ids"), list):
                        ex["used_service_ids"] = data["used_service_ids"]
            norm = self._normalize_data(data)
            key = self._generate_key(norm)
            if not key:
                continue
            existing = merged.get(key)
            if existing:
                for f in ("name", "email", "phone", "username", "location"):
                    if not existing.get(f) and norm.get(f):
                        existing[f] = norm[f]
            else:
                merged[key] = {k: v for k, v in norm.items() if k in {"name", "email", "phone", "username", "location"}}
        if not merged and any(seed_params.get(k) for k in ("name", "email", "phone", "username")):
            norm_seed = self._normalize_data(seed_params)
            key = self._generate_key(norm_seed)
            if key:
                merged[key] = {k: v for k, v in norm_seed.items() if k in {"name", "email", "phone", "username", "location"}}
        # Apply collected extras (e.g., used_services)
        for key, extras in extras_by_key.items():
            if key in merged:
                merged[key].update(extras)
        ordered = sorted(merged.values(), key=self._candidate_strength_key, reverse=True)
        return [Candidate(**c) for c in ordered]

    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Optional[str]] = {}
        email = data.get("email")
        if isinstance(email, str):
            out["email"] = email.strip().lower()
        phone = data.get("phone")
        if isinstance(phone, str):
            out["phone"] = self._normalize_phone(phone)
        username = data.get("username")
        if isinstance(username, str):
            out["username"] = username.strip().lower()
        name = data.get("name")
        if isinstance(name, str):
            out["name"] = name.strip()
        location = data.get("location")
        if isinstance(location, str):
            out["location"] = location.strip()
        return out

    def _normalize_phone(self, value: str) -> str:
        try:
            parsed = phonenumbers.parse(value, "US")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            return value.strip()

    def _generate_key(self, data: Dict[str, Any]) -> Optional[str]:
        if data.get("email"):
            return f"email:{data['email']}"
        if data.get("phone"):
            return f"phone:{data['phone']}"
        if data.get("username"):
            return f"username:{data['username']}"
        if data.get("name"):
            return f"name:{data['name'].lower()}"
        return None

    def _candidate_strength_key(self, data: Dict[str, Any]) -> int:
        score = 0
        if data.get("email"):
            score += 8
        if data.get("phone"):
            score += 4
        if data.get("username"):
            score += 2
        if data.get("name"):
            score += 1
        return score
