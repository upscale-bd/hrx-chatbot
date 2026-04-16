from pydantic import BaseModel, Field, field_validator
from services.gemini.gemini_types import GeminiModel
from google.generativeai.types import HarmCategory, HarmBlockThreshold


class GeminiConfig(BaseModel):
    """Configuration class for Gemini service"""

    api_key: str = Field(..., description="API key for Gemini service")
    model: GeminiModel = Field(default=GeminiModel.PRO)
    temperature: float = Field(default=0.7, ge=0, le=1)
    max_tokens: int = Field(default=4096, gt=0)
    top_p: float = Field(default=0.9, ge=0, le=1)
    top_k: int = Field(default=40, gt=0)
    timeout: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, ge=0)
    enable_logging: bool = Field(default=True)
    log_requests: bool = Field(
        default=False, description="Disable in production for privacy"
    )

    @field_validator("api_key")
    def validate_api_key(cls, v):
        if not v.strip():
            raise ValueError("API key cannot be empty")
        return v

    def get_safety_settings(self):
        safety_settings = {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        return safety_settings
