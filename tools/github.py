from typing import Dict, Any
from scraper import scrape_github_profile
from .base import BaseTool


class GitHubTool(BaseTool):
    @property
    def name(self) -> str:
        return "github"

    @property
    def stage(self) -> str:
        return "shallow"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("username"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        username = params.get("username")
        print(f"TOOL: Scraping GitHub for {username}…")
        profile = scrape_github_profile(username)
        return {
            "source": "GitHub",
            "raw_data": profile.model_dump(),
        }


async def get_real_github_data(username: str) -> dict:
    tool = GitHubTool()
    return await tool.execute({"username": username})