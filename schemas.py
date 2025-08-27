from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

class SearchRequest(BaseModel):
    username: str

class ProfileData(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None

class SearchResponse(BaseModel):
    username: str
    profile: ProfileData
    timestamp: datetime
    success: bool

class SearchQuery(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    location: Optional[str] = None
    free_text_context: Optional[str] = None

class Candidate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    location: Optional[str] = None
    used_services: Optional[List[str]] = None
    used_service_ids: Optional[List[str]] = None
    # Optional: include google_osint summary if available in UI hops later
    # Keeping minimal to avoid breaking existing consumers

# --- Hyperbrowser integration models ---

class HyperbrowserSessionOptions(BaseModel):
    use_proxy: Optional[bool] = None
    solve_captchas: Optional[bool] = None
    proxy_country: Optional[str] = None
    locales: Optional[List[str]] = None
    use_stealth: Optional[bool] = None
    adblock: Optional[bool] = None
    trackers: Optional[bool] = None
    annoyances: Optional[bool] = None
    accept_cookies: Optional[bool] = None
    operating_systems: Optional[List[str]] = None
    device: Optional[List[str]] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    wait_for_ms: Optional[int] = None

class HyperbrowserExtractParams(BaseModel):
    urls: Optional[List[str]] = None
    schema_def: Optional[Dict] = Field(default=None, alias="schema")
    prompt: Optional[str] = None
    max_links: Optional[int] = None
    session_options: Optional[HyperbrowserSessionOptions] = None

class HyperbrowserScrapeParams(BaseModel):
    urls: Optional[List[str]] = None
    formats: Optional[List[str]] = None
    only_main_content: Optional[bool] = None
    timeout_ms: Optional[int] = None
    session_options: Optional[HyperbrowserSessionOptions] = None

class HyperbrowserCrawlParams(BaseModel):
    url: Optional[str] = None
    max_pages: Optional[int] = None
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    formats: Optional[List[str]] = None
    only_main_content: Optional[bool] = None
    timeout_ms: Optional[int] = None
    session_options: Optional[HyperbrowserSessionOptions] = None

class HyperbrowserParams(BaseModel):
    extract: Optional[HyperbrowserExtractParams] = None
    scrape: Optional[HyperbrowserScrapeParams] = None
    crawl: Optional[HyperbrowserCrawlParams] = None
    session_options: Optional[HyperbrowserSessionOptions] = None

class FinalProfile(BaseModel):
    full_name: str
    summary: str
    locations: List[str]
    employment_history: List[Dict]

class ShallowResponse(BaseModel):
    candidates: List[Candidate]
    raw: List[Dict]

class DeepResponse(BaseModel):
    profile: FinalProfile
    raw: List[Dict]

class PlanStep(BaseModel):
    tool: str
    inputs: Dict[str, Any]
    why: Optional[str] = None
    success_if: Optional[str] = None

class PlanResponse(BaseModel):
    steps: List[PlanStep]
    finish_if: Optional[str] = None
    budget: Optional[Dict[str, Any]] = None