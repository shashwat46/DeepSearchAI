import os
import requests
from typing import Dict, Any
from .base import BaseTool


class NumverifyTool(BaseTool):
    @property
    def name(self) -> str:
        return "numverify"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("phone"))

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        phone_number = params["phone"]
        print(f"TOOL: Querying Numverify API for {phone_number}…")
        api_key = os.getenv("NUMVERIFY_API_KEY")
        if not api_key:
            return {"source": "Numverify", "raw_data": {"error": "API key not configured."}}

        url = f"http://apilayer.net/api/validate?access_key={api_key}&number={phone_number}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return {"source": "Numverify", "raw_data": resp.json()}
        except Exception as e:
            return {"source": "Numverify", "raw_data": {"error": str(e)}}


def get_phone_number_info(phone_number: str) -> dict:
    tool = NumverifyTool()
    return tool.execute({"phone": phone_number})
