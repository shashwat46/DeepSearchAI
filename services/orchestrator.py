from fastapi import HTTPException
from schemas import SearchQuery, FinalProfile
from .ai_agent import parse_user_request, synthesize_profile
from tools.registry import ToolRegistry


class SearchOrchestrator:
    def __init__(self):
        self.tool_registry = ToolRegistry()

    async def search(self, query: SearchQuery) -> FinalProfile:
        params = query.model_dump(exclude_none=True)

        if query.free_text_context:
            extracted = await parse_user_request(query.free_text_context)
            for k, v in extracted.model_dump(exclude_none=True).items():
                params.setdefault(k, v)

        data_list = await self.tool_registry.execute_tools(params)

        if not data_list:
            raise HTTPException(status_code=400, detail="Not enough information to run any searches.")

        profile = await synthesize_profile(data_list)
        return profile
