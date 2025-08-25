import json
import os
from functools import lru_cache
from typing import List, Dict, Any

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "resolvers.json")

@lru_cache(maxsize=1)
def load_resolver_config() -> List[Dict[str, Any]]:
    path = os.getenv("RESOLVER_CONFIG_PATH", _CONFIG_PATH)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


