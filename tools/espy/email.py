from typing import Dict, Any
from ..base import BaseTool
from .client import EspyClient


class EspyEmailTool(BaseTool):
    @property
    def name(self) -> str:
        return "espy_email"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("email"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        email = params["email"]
        client = EspyClient()
        print(f"TOOL: ESPY Email lookup for {email}...")
        result = await client.run_lookup(
            endpoint="/developer/combined_email",
            value=email,
            lookup_id=1  # Assuming lookupId for email
        )
        return {"source": "ESPY-Email", "raw_data": result}


