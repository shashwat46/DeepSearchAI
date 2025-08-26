from typing import Dict, Any
from ..base import BaseTool
from .client import EspyClient

class EspyDeepwebTool(BaseTool):
    @property
    def name(self) -> str:
        return "espy_deepweb"

    @property
    def stage(self) -> str:
        return "deep"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("email") or params.get("phone"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        email = params.get("email")
        phone = params.get("phone")
        client = EspyClient()
        print(f"TOOL: ESPY Deepweb/BreachScan for {email or phone}...")
        # Deepweb expects: key, value, lookupId (lookupId resolved internally).
        input_data = {"value": email or phone}
        result = await client.run_lookup(
            endpoint="/developer/deepweb",
            input_data=input_data
        )
        return {"source": "ESPY-Deepweb", "raw_data": result}

