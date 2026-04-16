from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class GeminiModel(str, Enum):
    """Selects the Gemini model to use for inference."""

    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_1_5 = "gemini-1.5"
    GEMINI_1_0 = "gemini-1.0"
    PRO = "gemini-pro"


class ErrorCode(str, Enum):
    """Standard error codes for the service"""

    API_KEY_INVALID = "GEMINI_001"
    QUOTA_EXCEEDED = "GEMINI_002"
    REQUEST_TIMEOUT = "GEMINI_003"
    INVALID_PROMPT = "GEMINI_004"
    MODEL_NOT_AVAILABLE = "GEMINI_005"
    UNKNOWN_ERROR = "GEMINI_999"


class GeminiResponse(BaseModel):
    """Standardized response object"""

    content: str
    model: str
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None

    @model_validator(mode="before")
    def validate_error_consistency(cls, values):
        """Ensure error_code/error_message only appear when success=False"""
        success = values.get("success")
        error_code = values.get("error_code")
        error_message = values.get("error_message")

        if success and (error_code or error_message):
            raise ValueError("Cannot have error_code/error_message when success=True")

        if not success and not (error_code or error_message):
            raise ValueError(
                "Must provide error_code and error_message when success=False"
            )

        return values
