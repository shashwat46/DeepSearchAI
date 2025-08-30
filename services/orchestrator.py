from typing import List, Dict, Any, Optional
import asyncio
import logging
from schemas import SearchQuery, FinalProfile, Candidate
from .ai_agent import parse_user_request, synthesize_profile, generate_search_hint
from tools.registry import ToolRegistry
from tools.linkedin_finder import LinkedInFinderTool
from tools.linkedin_verify import LinkedInVerifyTool
from .analysis import IdentityAnalysisService
from .link_cache import LinkCache
from .region import RegionResolver
from .geocoding import geocode_location, country_to_mkt
from .judge import ProfileJudge
import phonenumbers


class SearchOrchestrator:
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self._log = logging.getLogger(__name__)
        self._analysis = IdentityAnalysisService()
        self._link_cache = LinkCache()
        self._region = RegionResolver()
        self._judge = ProfileJudge()

    async def perform_shallow_search(self, query: SearchQuery) -> Dict[str, Any]:
        params = query.model_dump(exclude_none=True)
        self._log.info("Shallow input keys=%s", list(params.keys()))
        if query.free_text_context:
            extracted = await parse_user_request(query.free_text_context)
            for k, v in extracted.model_dump(exclude_none=True).items():
                params.setdefault(k, v)
        self._log.info("Shallow merged keys=%s", list(params.keys()))
        if params.get("location"):
            try:
                geo = await geocode_location(params["location"], language="en")
                if not geo.get("error"):
                    raw_geo = {"source": "OpenCage", "raw_data": geo}
                    cc = (geo.get("components") or {}).get("country_code")
                    if cc:
                        params.setdefault("country", cc)
                        params.setdefault("mkt", country_to_mkt(cc))
                else:
                    raw_geo = {"source": "OpenCage", "raw_data": geo}
            except Exception as e:
                raw_geo = {"source": "OpenCage", "raw_data": {"error": str(e)}}
        else:
            raw_geo = None

        region = self._region.infer(params)
        if region.get("mkt"):
            params.setdefault("mkt", region["mkt"])
        if region.get("country"):
            params.setdefault("country", region["country"])
        if params.get("free_text_context"):
            hint = await generate_search_hint(params["free_text_context"])
            if hint:
                params.setdefault("search_hint", hint)
        raw_results = await self.tool_registry.execute_tools(params, stage="shallow")
        if raw_geo:
            raw_results.insert(0, raw_geo)

        best_linkedin = self._extract_best_url(raw_results, source="LinkedIn-Finder")
        best_x = self._extract_best_url(raw_results, source="X-Finder")
        verify_params = dict(params)
        fp = LinkCache.fingerprint(verify_params)
        if not best_linkedin:
            cached_li = self._link_cache.get_best("linkedin", fp)
            if cached_li:
                best_linkedin = cached_li
        else:
            self._link_cache.set_best("linkedin", fp, best_linkedin)
        if not best_x:
            cached_x = self._link_cache.get_best("x", fp)
            if cached_x:
                best_x = cached_x
        else:
            self._link_cache.set_best("x", fp, best_x)
        if best_linkedin:
            verify_params["linkedin_finder_best_url"] = best_linkedin
        if best_x:
            verify_params["x_finder_best_url"] = best_x
        if best_linkedin or best_x:
            tools = self.tool_registry.get_applicable_tools(verify_params, stage="shallow")
            verify_names = {"linkedin_verify", "x_verify"}
            verify_tools = [t for t in tools if getattr(t, "name", "") in verify_names]
            if verify_tools:
                tasks = [t.execute(verify_params) for t in verify_tools]
                verify_results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in verify_results:
                    if isinstance(r, Exception):
                        raw_results.append({"source": "error", "raw_data": {}, "error": str(r)})
                    else:
                        raw_results.append(r)

        candidates = self._build_candidates_from_shallow(raw_results, params)
        self._log.info("Shallow candidates=%d", len(candidates))
        try:
            analysis = self._analysis.analyze(raw_results)
            raw_results.append({"source": "Analysis", "raw_data": analysis})
        except Exception:
            pass
        return {"candidates": candidates, "raw": raw_results}

    async def perform_deep_search(self, candidate: Candidate) -> Dict[str, Any]:
        params = candidate.model_dump(exclude_none=True)
        self._log.info("Deep input candidate keys=%s", list(params.keys()))
        deep_results = await self.tool_registry.execute_tools(params, stage="deep")

        try:
            fp = LinkCache.fingerprint(params)
            best_li = self._link_cache.get_best("linkedin", fp)
            if not best_li and params.get("email"):
                best_li = None
            if best_li:
                li_verify = LinkedInVerifyTool()
                ver_params = dict(params)
                ver_params["linkedin_finder_best_url"] = best_li
                if li_verify.can_handle(ver_params):
                    vres = await li_verify.execute(ver_params)
                    deep_results.append(vres)
        except Exception as e:
            deep_results.append({"source": "error", "raw_data": {}, "error": str(e)})
        agg = [{"source": "candidate", "raw_data": params}] + deep_results
        profile = await synthesize_profile(agg)
        judge_res = await self._judge.judge(profile, deep_results)
        if isinstance(judge_res, dict) and judge_res.get("judged_profile"):
            deep_results.append({"source": "Judge", "raw_data": {k: (v.model_dump() if hasattr(v, 'model_dump') else v) for k, v in judge_res.items()}})
            profile = judge_res["judged_profile"]
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
            # Attach Ignorant extras by phone key
            if result.get("source") == "Ignorant":
                phone = (data.get("phone") or "").strip()
                if phone:
                    key = f"phone:{phone}"
                    ex = extras_by_key.setdefault(key, {})
                    if isinstance(data.get("used_services"), list):
                        ex["used_services"] = list(set((ex.get("used_services") or []) + data["used_services"]))
                    if isinstance(data.get("used_service_ids"), list):
                        ex["used_service_ids"] = list(set((ex.get("used_service_ids") or []) + data["used_service_ids"]))
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

        # Deterministic safe merge: collapse candidates that share same name+location
        # This merges username/name-only clusters when both agree on identity signals.
        by_name_loc: Dict[str, Dict[str, Any]] = {}
        keep_others: List[Dict[str, Any]] = []
        for c in merged.values():
            name = (c.get("name") or "").strip()
            loc = (c.get("location") or "").strip()
            if name and loc:
                k = f"{name.lower()}|{loc.lower()}"
                existing = by_name_loc.get(k)
                if existing:
                    # Merge fields conservatively: prefer existing non-empty; union lists
                    for f in ("email", "phone", "username", "name", "location"):
                        if not existing.get(f) and c.get(f):
                            existing[f] = c[f]
                    # Union extras if present
                    for lf in ("used_services", "used_service_ids"):
                        a = existing.get(lf) or []
                        b = c.get(lf) or []
                        if isinstance(a, list) or isinstance(b, list):
                            s = set(a if isinstance(a, list) else []) | set(b if isinstance(b, list) else [])
                            existing[lf] = list(s)
                else:
                    by_name_loc[k] = dict(c)
            else:
                keep_others.append(c)

        merged_collapsed: List[Dict[str, Any]] = list(by_name_loc.values()) + keep_others
        ordered = sorted(merged_collapsed, key=self._candidate_strength_key, reverse=True)
        distinct: List[Dict[str, Any]] = []
        seen_keys: set = set()
        for c in ordered:
            k = self._generate_key(c)
            if not k:
                continue
            if k in seen_keys:
                continue
            seen_keys.add(k)
            distinct.append(c)
        return [Candidate(**c) for c in distinct]

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

    def _extract_best_url(self, raw_results: List[Dict[str, Any]], source: str) -> Optional[str]:
        for item in raw_results:
            if item.get("source") == source:
                raw = item.get("raw_data") or {}
                url = raw.get("best_url") or ""
                if isinstance(url, str) and url:
                    return url
        return None
