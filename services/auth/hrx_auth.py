"""
HRX Authentication Service
Manage HRX Bearer tokens (manual or dynamic)
"""
from datetime import datetime, timedelta
from typing import Optional
from common.logger import get_logger

logger = get_logger("hrx_auth")

# Global token cache (in production, use Redis or database)
_token_cache = {
    "token": None,
    "expires_at": None,
}


class HRXAuthService:
    """Manage HRX API authentication."""
    
    @staticmethod
    def set_token(token: str, ttl_hours: int = 24) -> bool:
        """Set bearer token manually.
        
        Args:
            token: Bearer token string
            ttl_hours: Token validity in hours (default 24)
            
        Returns:
            True if successful
        """
        if not token or not isinstance(token, str):
            logger.warning("[hrx_auth] Invalid token format")
            return False
        
        logger.info(f"[hrx_auth] Setting bearer token | token_length={len(token)}")
        
        _token_cache["token"] = token
        _token_cache["expires_at"] = datetime.utcnow() + timedelta(hours=ttl_hours)
        logger.info(f"[hrx_auth] Token set successfully | expires_at={_token_cache['expires_at']}")
        
        return True
    
    @staticmethod
    def get_cached_token() -> Optional[str]:
        """Get cached token if valid."""
        if not _token_cache["token"]:
            logger.debug("[hrx_auth] No cached token available")
            return None
        
        # Check if token expired
        if datetime.utcnow() > _token_cache["expires_at"]:
            logger.warning("[hrx_auth] Cached token expired")
            _token_cache["token"] = None
            _token_cache["expires_at"] = None
            return None
        
        logger.debug("[hrx_auth] Using cached token")
        return _token_cache["token"]
    
    @staticmethod
    def clear_token():
        """Clear cached token."""
        _token_cache["token"] = None
        _token_cache["expires_at"] = None
        logger.info("[hrx_auth] Token cleared from cache")
    
    @staticmethod
    def get_token_status() -> dict:
        """Get current token status."""
        token = _token_cache["token"]
        expires_at = _token_cache["expires_at"]
        
        if not token:
            return {
                "status": "missing",
                "message": "No token set"
            }
        
        if datetime.utcnow() > expires_at:
            return {
                "status": "expired",
                "expires_at": expires_at.isoformat()
            }
        
        return {
            "status": "valid",
            "expires_at": expires_at.isoformat(),
            "remaining_hours": round((expires_at - datetime.utcnow()).total_seconds() / 3600, 2)
        }
