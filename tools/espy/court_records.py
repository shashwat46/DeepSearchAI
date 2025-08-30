from typing import Dict, Any
from ..base import BaseTool
from .client import EspyClient


class EspyCourtRecordsTool(BaseTool):
    @property
    def name(self) -> str:
        return "espy_court_records"

    @property
    def stage(self) -> str:
        return "deep"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        name = (params.get("name") or "").strip()
        country = (params.get("country") or "").strip().upper()
        return bool(name) and country == "US"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = (params.get("name") or "").strip()
        loc = (params.get("location") or "").strip()
        keyphrase = name
        if loc:
            keyphrase = f"{name} {loc}"
        client = EspyClient()
        result = await client.run_lookup(
            endpoint="/developer/compliance_screening/court_records",
            input_data={"keyphrase": keyphrase}
        )
        return {"source": "ESPY-CourtRecords", "raw_data": result}


