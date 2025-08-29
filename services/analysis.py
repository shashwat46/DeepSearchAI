from typing import List, Dict, Any, Tuple, Set


class IdentityAnalysisService:
    def analyze(self, raw_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        signals = {
            "email": self._collect_values(raw_results, self._extract_email, {"Holehe", "GHunt", "ESPY-Email", "GitHub-Extras"}),
            "phone": self._collect_values(raw_results, self._extract_phone, {"Ignorant", "Numverify", "ESPY-Phone"}),
            "username": self._collect_values(raw_results, self._extract_username, {"GitHub", "GitHub-Extras"}),
            "name": self._collect_values(raw_results, self._extract_name, {"GitHub"}),
            "location": self._collect_values(raw_results, self._extract_location, {"GitHub", "GitHub-Extras", "user_input", "OpenCage"}),
        }

        signal_analysis: Dict[str, Dict[str, Any]] = {}
        for key, entries in signals.items():
            platforms = {src for src, _ in entries}
            values: Set[str] = {val for _, val in entries if isinstance(val, str) and val}
            avg_conf = self._average_confidence(key, entries)
            signal_analysis[key] = {
                "platforms_found": len(platforms),
                "unique_values": len(values),
                "avg_confidence": avg_conf,
            }

        identity_confidence = self._compute_identity_confidence(signal_analysis)
        verification_status = self._verification_status(identity_confidence)
        risk = self._risk_assessment(signal_analysis, raw_results)
        insights = self._cross_platform_insights(signal_analysis, raw_results)

        return {
            "identity_confidence": identity_confidence,
            "verification_status": verification_status,
            "signal_analysis": signal_analysis,
            "risk_assessment": risk,
            "cross_platform_insights": insights,
        }

    def _collect_values(
        self,
        raw_results: List[Dict[str, Any]],
        extractor,
        preferred_sources: Set[str],
    ) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for item in raw_results:
            source = item.get("source") or ""
            raw = item.get("raw_data") or {}
            value = extractor(source, raw)
            if isinstance(value, str) and value:
                out.append((source, value))
        if out:
            out.sort(key=lambda t: (0 if t[0] in preferred_sources else 1, t[0]))
        return out

    def _extract_email(self, source: str, raw: Dict[str, Any]) -> str:
        if source == "Holehe":
            return (raw.get("email") or "").strip().lower()
        if source == "GHunt":
            return (raw.get("email") or "").strip().lower()
        if source == "ESPY-Email":
            v = raw.get("value") or raw.get("email")
            return (v or "").strip().lower()
        if source == "GitHub-Extras":
            return (raw.get("email") or "").strip().lower()
        return ""

    def _extract_phone(self, source: str, raw: Dict[str, Any]) -> str:
        if source == "Ignorant":
            return (raw.get("phone") or "").strip()
        if source == "Numverify":
            v = raw.get("international_format") or raw.get("number") or ""
            return str(v).strip()
        if source == "ESPY-Phone":
            v = raw.get("value") or raw.get("phone")
            return (v or "").strip()
        return ""

    def _extract_username(self, source: str, raw: Dict[str, Any]) -> str:
        if source == "GitHub":
            return (raw.get("username") or raw.get("login") or "").strip().lower()
        if source == "GitHub-Extras":
            return (raw.get("username") or "").strip().lower()
        return ""

    def _extract_name(self, source: str, raw: Dict[str, Any]) -> str:
        if source == "GitHub":
            return (raw.get("name") or "").strip()
        return ""

    def _extract_location(self, source: str, raw: Dict[str, Any]) -> str:
        if source == "GitHub":
            return (raw.get("location") or "").strip()
        if source == "GitHub-Extras":
            return (raw.get("location") or "").strip()
        if source == "user_input":
            return (raw.get("location") or "").strip()
        if source == "OpenCage":
            comps = raw.get("components") or {}
            city = (comps.get("city") or "").strip()
            cc = (comps.get("country_code") or "").upper()
            if city and cc:
                return f"{city}, {cc}"
            return cc
        return ""

    def _average_confidence(self, key: str, entries: List[Tuple[str, str]]) -> float:
        if not entries:
            return 0.0
        scores: List[float] = []
        for source, _ in entries:
            if key == "email":
                scores.append(0.6 if source in {"Holehe", "GHunt"} else 0.5)
            elif key == "phone":
                if source == "Numverify":
                    scores.append(0.9)
                else:
                    scores.append(0.6)
            elif key == "username":
                scores.append(0.9 if source == "GitHub" else 0.5)
            elif key == "name":
                scores.append(0.7 if source == "GitHub" else 0.5)
            elif key == "location":
                scores.append(0.7 if source == "GitHub" else 0.5)
        return sum(scores) / len(scores)

    def _compute_identity_confidence(self, signal_analysis: Dict[str, Dict[str, Any]]) -> float:
        weights = {"email": 0.35, "phone": 0.25, "username": 0.2, "name": 0.1, "location": 0.1}
        total = 0.0
        for key, w in weights.items():
            s = signal_analysis.get(key) or {}
            pf = int(s.get("platforms_found") or 0)
            uv = int(s.get("unique_values") or 0)
            if uv <= 1 and pf >= 2:
                score = 1.0
            elif uv <= 1 and pf == 1:
                score = 0.5
            else:
                score = 0.0
            total += w * score
        return max(0.0, min(1.0, total))

    def _verification_status(self, identity_confidence: float) -> str:
        if identity_confidence >= 0.8:
            return "HIGH"
        if identity_confidence >= 0.5:
            return "MEDIUM"
        return "LOW"

    def _risk_assessment(
        self,
        signal_analysis: Dict[str, Dict[str, Any]],
        raw_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        flags: List[Dict[str, Any]] = []
        for key in ["name", "location", "email", "phone"]:
            s = signal_analysis.get(key) or {}
            if int(s.get("unique_values") or 0) > 1:
                flags.append({
                    "type": f"{key}_inconsistency",
                    "severity": "medium" if key in {"name", "location"} else "high",
                    "description": f"Multiple distinct {key} values observed across sources",
                })
        overall = 2.0 + 1.5 * sum(1 for f in flags if f.get("severity") == "high") + 1.0 * sum(1 for f in flags if f.get("severity") == "medium")
        overall = float(min(10.0, max(1.0, overall)))
        return {"overall_score": overall, "flags": flags}

    def _cross_platform_insights(self, signal_analysis: Dict[str, Dict[str, Any]], raw_results: List[Dict[str, Any]]) -> List[str]:
        out: List[str] = []
        s_email = signal_analysis.get("email") or {}
        if int(s_email.get("unique_values") or 0) == 1 and int(s_email.get("platforms_found") or 0) >= 2:
            out.append("Email consistent across multiple sources")
        s_phone = signal_analysis.get("phone") or {}
        if int(s_phone.get("platforms_found") or 0) >= 1:
            if any((item.get("source") == "Numverify" and (item.get("raw_data") or {}).get("valid") is True) for item in raw_results):
                out.append("Phone validated by Numverify")
        gh = next((item for item in raw_results if item.get("source") == "GitHub"), None)
        if gh:
            raw = gh.get("raw_data") or {}
            if isinstance(raw.get("followers"), int):
                out.append(f"GitHub profile found with {raw['followers']} followers")
        return out


