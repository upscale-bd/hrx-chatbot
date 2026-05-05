from sqlalchemy.orm import Session
from app.admin.repository.admin_script_repository import AdminScriptRepository
from app.admin.dto.admin_script_dto import (
    AdminScriptRequest, AdminScriptResponse, AdminScriptGetResponse, AdminScriptUpdateRequest
)
from common.logger import get_logger


logger = get_logger("admin_script_usecase")


class AdminScriptUsecase:
    """Usecase for admin script management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = AdminScriptRepository(db)
    
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
