from typing import Dict, Any
from ..base import BaseTool
from .client import EspyClient

class EspyPhoneTool(BaseTool):
    @property
    def name(self) -> str:
        return "espy_phone"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("phone"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        phone = params["phone"]
        client = EspyClient()
        print(f"TOOL: ESPY Phone lookup for {phone}...")
        result = await client.run_lookup(
            endpoint="/developer/combined_phone",
            value=phone,
            lookup_id=2  # Assuming lookupId for phone
        )
        return {"source": "ESPY-Phone", "raw_data": result}
