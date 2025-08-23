from typing import List, Dict, Any
from .base import BaseTool
from .github import GitHubTool
from .numverify import NumverifyTool


class ToolRegistry:
    def __init__(self):
        self._tools: List[BaseTool] = [
            GitHubTool(),
            NumverifyTool(),
        ]

    def get_applicable_tools(self, params: Dict[str, Any]) -> List[BaseTool]:
        return [tool for tool in self._tools if tool.can_handle(params)]

    def execute_tools(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        data_list = []
        applicable_tools = self.get_applicable_tools(params)
        
        for tool in applicable_tools:
            result = tool.execute(params)
            data_list.append(result)
        
        if params.get("location"):
            data_list.append({"source": "user_input", "raw_data": {"location": params["location"]}})
        
        return data_list
