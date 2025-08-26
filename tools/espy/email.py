from typing import Dict, Any
from ..base import BaseTool
from .client import EspyClient


class EspyEmailTool(BaseTool):
    @property
    def name(self) -> str:
        return "espy_email"

    @property
    def stage(self) -> str:
        return "deep"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("email"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        email = params["email"]
        client = EspyClient()
        print(f"TOOL: ESPY Email lookup for {email}...")
        # Align with ESPY two-step flow: start lookup (lookupId is resolved internally), then poll.
        result = await client.run_lookup(
            endpoint="/developer/combined_email",
            input_data={"value": email}
        )
        return {"source": "ESPY-Email", "raw_data": result}

