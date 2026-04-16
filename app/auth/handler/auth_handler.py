"""
Authentication Handler Endpoints
Swagger UI Authorization integration
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.auth.hrx_auth import HRXAuthService
from common.logger import get_logger

logger = get_logger("auth_handler")

router = APIRouter(prefix="/auth", tags=["Authorization"])


class TokenStatusResponse(BaseModel):
    """Token status response."""
    status: str  # "active", "expired", or "missing"
    message: str
    remaining_hours: float = None
    expires_at: str = None


class MessageResponse(BaseModel):
    """Simple message response."""
    success: bool
    message: str


@router.get(
    "/token-status",
    response_model=TokenStatusResponse,
    summary="Check Bearer Token Status",
    description="Check if Bearer token is currently active in memory"
)
def check_token_status():
    """GET /auth/token-status - Check current Bearer token status."""
    try:
        status_info = HRXAuthService.get_token_status()
        
        logger.info(f"[auth_handler] Token status check: {status_info['status']}")
        
        response = TokenStatusResponse(
            status=status_info["status"],
            message=f"Token is {status_info['status']}"
        )
        
        if status_info.get("expires_at"):
            response.expires_at = status_info["expires_at"]
        if status_info.get("remaining_hours"):
            response.remaining_hours = status_info["remaining_hours"]
        
        return response
        
    except Exception as exc:
        logger.error(f"[auth_handler] Error checking token status: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (Clear Bearer Token)",
    description="Clear Bearer token from memory"
)
def logout():
    """POST /auth/logout - Clear cached Bearer token."""
    try:
        HRXAuthService.clear_token()
        logger.info("[auth_handler] Bearer token cleared")
        
        return MessageResponse(
            success=True,
            message="✅ Bearer token cleared. You are now logged out."
        )
        
    except Exception as exc:
        logger.error(f"[auth_handler] Logout error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

