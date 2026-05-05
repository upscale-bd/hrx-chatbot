from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AudioComparisonRequest(BaseModel):
    """Request to upload audio for transcription and comparison."""
    user_name: str
    admin_name: str


class AudioComparisonResponse(BaseModel):
    """Response after audio upload, transcription and comparison."""
    success: bool = True
    name: str
    message: str
    comparison_id: Optional[str] = None
    similarity_percentage: Optional[float] = None
    error: Optional[str] = None


class AudioResultResponse(BaseModel):
    """Response with audio result - name, id, and percentage."""
    success: bool = True
    name: str
    comparison_id: str
    similarity_percentage: Optional[float] = None
    created_at: datetime
    error: Optional[str] = None


class AudioStatusResponse(BaseModel):
    """Response indicating whether audio has been transcribed."""
    success: bool = True
    comparison_id: str
    transcribed: bool
    transcribed_text: Optional[str] = None
    created_at: Optional[datetime] = None
    message: Optional[str] = None
    error: Optional[str] = None
