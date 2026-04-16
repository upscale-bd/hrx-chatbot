from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    message: str


class ToolInfo(BaseModel):
    """Information about extracted/executed tool."""
    name: Optional[str] = None  # get_attendance, get_leave, etc.
    endpoint: Optional[str] = None  # api/attendance/attendance-list
    status: str = "not_used"  # not_used, success, failed
    recordsCount: Optional[int] = None


class ReportInfo(BaseModel):
    """Information about generated report."""
    id: Optional[str] = None
    downloadUrl: Optional[str] = None
    format: str = "xlsx"
    expiresIn: Optional[int] = 300  # seconds


class ChatResponseData(BaseModel):
    """Core response data."""
    chatId: str
    answer: str  # Plain text version
    answerMarkdown: Optional[str] = None  # Markdown-formatted version for rich display
    toolUsed: ToolInfo
    report: Optional[ReportInfo] = None
    metadata: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    status: str  # completed, out_of_scope, error
    data: Optional[ChatResponseData] = None
    error: Optional[str] = None


class ChatHistoryItem(BaseModel):
    """Single message in chat history."""
    chatId: str
    userMessage: str
    botResponse: Optional[str] = None
    createdAt: datetime


class ChatHistoryResponse(BaseModel):
    """Chat history list response."""
    success: bool = True
    organizationId: str
    totalCount: int
    messages: list[ChatHistoryItem]
