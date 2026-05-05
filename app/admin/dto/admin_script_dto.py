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
