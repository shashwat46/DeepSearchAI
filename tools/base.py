from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def stage(self) -> str:
        pass

    @abstractmethod
    def can_handle(self, params: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass
