import phonenumbers
from typing import Dict, Optional


class RegionResolver:
    def infer(self, params: Dict[str, str]) -> Dict[str, str]:
        country = self._country_from_phone(params.get("phone")) or self._country_from_location(params.get("location")) or self._country_from_email(params.get("email")) or "US"
        mkt = self._mkt_from_country(country)
        return {"country": country, "mkt": mkt}

    def _country_from_phone(self, phone: Optional[str]) -> Optional[str]:
        if not phone:
            return None
        try:
            parsed = phonenumbers.parse(phone, None)
            cc = phonenumbers.region_code_for_number(parsed)
            return cc or None
        except Exception:
            return None

    def _country_from_location(self, location: Optional[str]) -> Optional[str]:
        if not location:
            return None
        loc = location.lower()
        mapping = [
            ("india", "IN"), ("jharkhand", "IN"), ("delhi", "IN"), ("mumbai", "IN"), ("bengaluru", "IN"), ("bangalore", "IN"), ("hyderabad", "IN"),
            ("united kingdom", "GB"), ("uk", "GB"), ("london", "GB"),
            ("canada", "CA"), ("toronto", "CA"),
            ("australia", "AU"), ("sydney", "AU"),
        ]
        for token, code in mapping:
            if token in loc:
                return code
        return None

    def _country_from_email(self, email: Optional[str]) -> Optional[str]:
        if not email or "@" not in email:
            return None
        domain = email.split("@", 1)[1].lower()
        if domain.endswith(".in"):
            return "IN"
        if domain.endswith(".uk"):
            return "GB"
        if domain.endswith(".ca"):
            return "CA"
        if domain.endswith(".au"):
            return "AU"
        return None

    def _mkt_from_country(self, country: str) -> str:
        mapping = {"IN": "en-IN", "GB": "en-GB", "CA": "en-CA", "AU": "en-AU", "US": "en-US"}
        return mapping.get(country.upper(), "en-US")


