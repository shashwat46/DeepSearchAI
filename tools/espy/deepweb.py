from typing import Dict, Any
from ..base import BaseTool
from .client import EspyClient

class EspyDeepwebTool(BaseTool):
    @property
    def name(self) -> str:
        return "espy_deepweb"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("email") or params.get("phone"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        value = params.get("email") or params.get("phone")
        client = EspyClient()
        print(f"TOOL: ESPY Deepweb/BreachScan for {value}...")
        result = await client.run_lookup(
            endpoint="/developer/deepweb",
            value=value,
            lookup_id=4  # Assuming lookupId for deepweb
        )
        return {"source": "ESPY-Deepweb", "raw_data": result}
