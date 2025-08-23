import asyncio
from typing import List, Dict, Any
from .base import BaseTool
from .github import GitHubTool
from .numverify import NumverifyTool
from .espy.email import EspyEmailTool
from .espy.phone import EspyPhoneTool
from .espy.name import EspyNameTool
from .espy.deepweb import EspyDeepwebTool

class ToolRegistry:
    def __init__(self):
        self._tools: List[BaseTool] = [
            GitHubTool(),
            NumverifyTool(),
            EspyEmailTool(),
            EspyPhoneTool(),
            EspyNameTool(),
            EspyDeepwebTool(),
        ]

    def get_applicable_tools(self, params: Dict[str, Any]) -> List[BaseTool]:
        return [tool for tool in self._tools if tool.can_handle(params)]

    async def execute_tools(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        applicable_tools = self.get_applicable_tools(params)
        
        tasks = [tool.execute(params) for tool in applicable_tools]
        results = await asyncio.gather(*tasks)
        
        data_list = list(results)
        
        if params.get("location"):
            data_list.append({"source": "user_input", "raw_data": {"location": params["location"]}})
        
        return data_list
