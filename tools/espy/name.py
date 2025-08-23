from typing import Dict, Any
from ..base import BaseTool
from .client import EspyClient

class EspyNameTool(BaseTool):
    @property
    def name(self) -> str:
        return "espy_name"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("name"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params["name"]
        client = EspyClient()
        print(f"TOOL: ESPY Name lookup for {name}...")
        result = await client.run_lookup(
            endpoint="/developer/combined_name",
            value=name,
            lookup_id=3  # Assuming lookupId for name
        )
        return {"source": "ESPY-Name", "raw_data": result}
