from typing import Tuple, Optional, Dict
from .config import load_resolver_config

_alias_to_service: Dict[str, str] = {}
for item in load_resolver_config():
    svc = (item.get("service") or "").lower()
    if not svc:
        continue
    _alias_to_service[svc] = svc
    for alias in item.get("aliases", []) or []:
        _alias_to_service[alias.lower()] = svc

def canonicalize_service(label: str) -> Optional[Tuple[str, str]]:
    if not isinstance(label, str):
        return None
    raw = label.strip().lower()
    raw = raw.rstrip("/")
    raw = raw.split("?")[0]
    raw = raw.split("#")[0]
    if raw.startswith("www."):
        raw = raw[4:]
    host = raw
    if "/" in host:
        host = host.split("/", 1)[0]
    service = _alias_to_service.get(host, host)
    return service, host


