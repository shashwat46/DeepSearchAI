from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict

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