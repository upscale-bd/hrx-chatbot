import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.admin.repository.admin_script_repository import AdminScriptRepository
from app.admin.dto.admin_script_dto import (
    AdminScriptRequest, AdminScriptResponse, AdminScriptGetResponse, AdminScriptUpdateRequest,
    AdminCreateRequest, AdminCreateResponse, AdminLoginRequest, AdminLoginResponse
)
from config.config import settings
from common.logger import get_logger


logger = get_logger("admin_script_usecase")


class AdminScriptUsecase:
    """Usecase for admin script management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = AdminScriptRepository(db)

    def _hash_password(self, password: str) -> str:
        """Hash password with app secret."""
        secret = settings.APP_SECRET_KEY if settings else "dev-secret"
        raw = f"{secret}:{password}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
    
    def save_script(self, req: AdminScriptRequest) -> AdminScriptResponse:
        """Save admin script to database.
        
        Args:
            req: AdminScriptRequest with admin_name and script
            
        Returns:
            AdminScriptResponse with script details and ID
        """
        try:
            logger.info(f"[admin_script_usecase] Saving script for admin: {req.admin_name}")
            
            script = self.repository.save_script(
                admin_name=req.admin_name,
                script=req.script
            )
            
            logger.info(f"[admin_script_usecase] Script saved successfully | ID: {script.id}")
            
            return AdminScriptResponse(
                success=True,
                id=script.id,
                admin_name=script.admin_name,
                script=script.script,
                message="Script saved successfully in database"
            )
        
        except Exception as e:
            logger.error(f"[admin_script_usecase] Error saving script: {e}")
            return AdminScriptResponse(
                success=False,
                id="",
                admin_name=req.admin_name,
                script=req.script,
                message="Error saving script",
                error=str(e)
            )
    
    def get_script(self, script_id: str) -> AdminScriptGetResponse:
        """Get script by ID.
        
        Args:
            script_id: ID of the script
            
        Returns:
            AdminScriptGetResponse with script details
        """
        try:
            logger.info(f"[admin_script_usecase] Fetching script: {script_id}")
            
            script = self.repository.get_script_by_id(script_id)
            
            if not script:
                logger.warning(f"[admin_script_usecase] Script not found: {script_id}")
                return AdminScriptGetResponse(
                    success=False,
                    id=script_id,
                    admin_name="",
                    script="",
                    created_at=None,
                    error="Script not found"
                )
            
            logger.info(f"[admin_script_usecase] Script retrieved successfully")
            
            return AdminScriptGetResponse(
                success=True,
                id=script.id,
                admin_name=script.admin_name,
                script=script.script,
                created_at=script.created_at
            )
        
        except Exception as e:
            logger.error(f"[admin_script_usecase] Error fetching script: {e}")
            return AdminScriptGetResponse(
                success=False,
                id=script_id,
                admin_name="",
                script="",
                created_at=None,
                error=str(e)
            )
    
    def update_script(self, script_id: str, req: AdminScriptUpdateRequest) -> AdminScriptGetResponse:
        """Update script by ID.
        
        Args:
            script_id: ID of the script to update
            req: AdminScriptUpdateRequest with new script
            
        Returns:
            AdminScriptGetResponse with updated script details
        """
        try:
            logger.info(f"[admin_script_usecase] Updating script: {script_id}")
            
            script = self.repository.update_script(script_id, req.script)
            
            if not script:
                logger.warning(f"[admin_script_usecase] Script not found for update: {script_id}")
                return AdminScriptGetResponse(
                    success=False,
                    id=script_id,
                    admin_name="",
                    script="",
                    created_at=None,
                    error="Script not found"
                )
            
            logger.info(f"[admin_script_usecase] Script updated successfully")
            
            return AdminScriptGetResponse(
                success=True,
                id=script.id,
                admin_name=script.admin_name,
                script=script.script,
                created_at=script.created_at
            )
        
        except Exception as e:
            logger.error(f"[admin_script_usecase] Error updating script: {e}")
            return AdminScriptGetResponse(
                success=False,
                id=script_id,
                admin_name="",
                script="",
                created_at=None,
                error=str(e)
            )

    def create_admin_user(self, req: AdminCreateRequest) -> AdminCreateResponse:
        """Create a new admin user with email and password."""
        try:
            existing = self.repository.get_admin_by_email(req.email)
            if existing:
                return AdminCreateResponse(
                    success=False,
                    id="",
                    name=req.name,
                    email=req.email,
                    message="Admin user already exists",
                    error="admin_exists"
                )

            password_hash = self._hash_password(req.password)
            admin_user = self.repository.create_admin_user(
                name=req.name,
                email=req.email,
                password_hash=password_hash
            )

            return AdminCreateResponse(
                success=True,
                id=admin_user.id,
                name=admin_user.name,
                email=admin_user.email,
                message="Admin user created successfully",
                error=None
            )
        except Exception as e:
            logger.error(f"[admin_script_usecase] Error creating admin user: {e}")
            return AdminCreateResponse(
                success=False,
                id="",
                name=req.name,
                email=req.email,
                message="Error creating admin user",
                error=str(e)
            )

    def login_admin_user(self, req: AdminLoginRequest) -> AdminLoginResponse:
        """Login admin user and return a token."""
        try:
            admin_user = self.repository.get_admin_by_email(req.email)
            if not admin_user:
                return AdminLoginResponse(
                    success=False,
                    token="",
                    expires_at=datetime.utcnow(),
                    message="Invalid credentials",
                    error="invalid_credentials"
                )

            password_hash = self._hash_password(req.password)
            if admin_user.password_hash != password_hash:
                return AdminLoginResponse(
                    success=False,
                    token="",
                    expires_at=datetime.utcnow(),
                    message="Invalid credentials",
                    error="invalid_credentials"
                )

            token = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            self.repository.set_admin_token(admin_user.id, token, expires_at)

            return AdminLoginResponse(
                success=True,
                token=token,
                expires_at=expires_at,
                message="Login successful",
                error=None
            )
        except Exception as e:
            logger.error(f"[admin_script_usecase] Error logging in admin user: {e}")
            return AdminLoginResponse(
                success=False,
                token="",
                expires_at=datetime.utcnow(),
                message="Error logging in",
                error=str(e)
            )

    def validate_admin_token(self, token: str) -> bool:
        """Validate admin auth token."""
        try:
            admin_user = self.repository.get_admin_by_token(token)
            if not admin_user or not admin_user.token_expires_at:
                return False
            now = datetime.now(timezone.utc)
            expires_at = admin_user.token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return now <= expires_at
        except Exception as e:
            logger.error(f"[admin_script_usecase] Error validating admin token: {e}")
            return False

    def get_processing_status(self) -> dict:
        """Get current processing enabled status."""
        try:
            enabled = self.repository.is_processing_enabled()
            return {
                "success": True,
                "processing_enabled": enabled,
                "message": "Processing is on" if enabled else "Off is on"
            }
        except Exception as e:
            logger.error(f"[admin_script_usecase] Error getting processing status: {e}")
            return {"success": False, "message": "Error getting status", "error": str(e)}

    def set_processing_status(self, enabled: bool) -> dict:
        """Set processing enabled or disabled."""
        try:
            self.repository.set_processing_enabled(enabled)
            return {
                "success": True,
                "processing_enabled": enabled,
                "message": "Processing enabled" if enabled else "Processing disabled"
            }
        except Exception as e:
            logger.error(f"[admin_script_usecase] Error setting processing status: {e}")
            return {"success": False, "message": "Error updating status", "error": str(e)}

    def get_all_users_stats(self) -> dict:
        """Get all users with their audio statistics."""
        try:
            logger.info("[admin_script_usecase] Fetching all users' statistics from stats table")

            stats = self.repository.get_all_user_stats_from_db()

            logger.info(f"[admin_script_usecase] Retrieved stats for {len(stats)} users")

            return {
                "success": True,
                "total_users": len(stats),
                "users": stats,
                "error": None
            }

        except Exception as e:
            logger.error(f"[admin_script_usecase] Error fetching all user stats: {e}")
            return {
                "success": False,
                "total_users": 0,
                "users": [],
                "error": str(e)
            }

    def get_user_stats(self, user_id: str) -> dict:
        """Get audio statistics for a specific user by user_id from stats table."""
        try:
            logger.info(f"[admin_script_usecase] Fetching statistics for user_id: {user_id} from stats table")

            stats = self.repository.get_user_stats_from_db(user_id)

            if not stats:
                logger.warning(f"[admin_script_usecase] No stats found for user_id: {user_id}")
                return {
                    "success": False,
                    "message": f"No data found for user_id: {user_id}",
                    "error": "user_not_found"
                }

            return {
                "success": True,
                "user_id": stats["user_id"],
                "user_name": stats["user_name"],
                "submission_count": stats["submission_count"],
                "last_score": stats["last_score"],
                "average_score": stats["average_score"],
                "last_submission_time": stats["last_submission_time"]
            }

        except Exception as e:
            logger.error(f"[admin_script_usecase] Error fetching user stats for user_id {user_id}: {e}")
            return {
                "success": False,
                "message": f"Error fetching stats for user_id {user_id}",
                "error": str(e)
            }
