import asyncio
import logging
from typing import List, Dict, Any, Optional
from .base import BaseTool
from .github import GitHubTool
from .numverify import NumverifyTool
# ESPY tools temporarily disabled
from .holehe_cli import HoleheCliTool
from .holehe_resolver import HoleheResolverTool
from .espy.email import EspyEmailTool
from .hyperbrowser.extract import HyperbrowserExtractTool
from .hyperbrowser.scrape import HyperbrowserScrapeTool
from .hyperbrowser.crawl import HyperbrowserCrawlTool
# from .espy.deepweb import EspyDeepwebTool
from .ghunt import GHuntTool
from .ignorant_cli import IgnorantCliTool

class ToolRegistry:
    def __init__(self):
        self._tools: List[BaseTool] = [
            GitHubTool(),
            NumverifyTool(),
            HoleheCliTool(),
            HoleheResolverTool(),
            EspyEmailTool(),
            GHuntTool(),
            IgnorantCliTool(),
            HyperbrowserExtractTool(),
            HyperbrowserScrapeTool(),
            HyperbrowserCrawlTool(),
        ]
        self._log = logging.getLogger(__name__)

    def get_tools_by_stage(self, stage: str) -> List[BaseTool]:
        return [t for t in self._tools if t.stage == stage]

    def get_applicable_tools(self, params: Dict[str, Any], stage: Optional[str] = None) -> List[BaseTool]:
        tools = self._tools if stage is None else self.get_tools_by_stage(stage)
        applicable = [tool for tool in tools if tool.can_handle(params)]
        self._log.info("Applicable tools stage=%s: %s", stage, [t.name for t in applicable])
        return applicable

    async def execute_tools(self, params: Dict[str, Any], stage: Optional[str] = None) -> List[Dict[str, Any]]:
        applicable_tools = self.get_applicable_tools(params, stage)
        tasks = [tool.execute(params) for tool in applicable_tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        data_list: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, Exception):
                data_list.append({"source": "error", "raw_data": {}, "error": str(r)})
            else:
                data_list.append(r)
        if params.get("location"):
            data_list.append({"source": "user_input", "raw_data": {"location": params["location"]}})
        return data_list
