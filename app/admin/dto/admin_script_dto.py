from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AdminScriptRequest(BaseModel):
    """Request to save admin script."""
    admin_name: str
    script: str


class AdminScriptResponse(BaseModel):
    """Response when script is saved."""
    success: bool = True
    id: str
    admin_name: str
    script: str
    message: str
    error: Optional[str] = None


class AdminScriptGetResponse(BaseModel):
    """Response when fetching script."""
    success: bool = True
    id: str
    admin_name: str
    script: str
    created_at: datetime
    error: Optional[str] = None


class AdminScriptUpdateRequest(BaseModel):
    """Request to update script."""
    script: str


class AdminCreateRequest(BaseModel):
    """Request to create an admin user."""
    name: str
    email: str
    password: str


class AdminCreateResponse(BaseModel):
    """Response after admin user creation."""
    success: bool = True
    id: str
    name: str
    email: str
    message: str
    error: Optional[str] = None


class AdminLoginRequest(BaseModel):
    """Request to login an admin user."""
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    """Response after admin login."""
    success: bool = True
    token: str
    expires_at: Optional[datetime] = None
    message: str
    error: Optional[str] = None


class UserAudioStatsResponse(BaseModel):
    """Response with user's audio statistics."""
    user_id: str
    user_name: str
    submission_count: int
    last_score: Optional[float] = None
    average_score: float
    last_submission_time: Optional[datetime] = None
    error: Optional[str] = None


class AllUsersStatsResponse(BaseModel):
    """Response with all users' audio statistics."""
    success: bool = True
    total_users: int
    users: list[UserAudioStatsResponse]
    error: Optional[str] = None
