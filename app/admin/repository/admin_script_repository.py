from sqlalchemy.orm import Session
from models.admin_script import AdminScript
from common.logger import get_logger


logger = get_logger("admin_script_repository")


class AdminScriptRepository:
    """Repository for admin script operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_script(self, admin_name: str, script: str) -> AdminScript:
        """Save or update admin script."""
        try:
            admin_script = AdminScript(
                admin_name=admin_name,
                script=script
            )
            self.db.add(admin_script)
            self.db.commit()
            self.db.refresh(admin_script)
            logger.info(f"[admin_script_repository] Script saved for admin: {admin_name} | ID: {admin_script.id}")
            return admin_script
        except Exception as e:
            logger.error(f"[admin_script_repository] Error saving script: {e}")
            self.db.rollback()
            raise
    
    def get_script_by_id(self, script_id: str) -> AdminScript:
        """Get script by ID."""
        try:
            script = self.db.query(AdminScript).filter(
                AdminScript.id == script_id
            ).first()
            if not script:
                logger.warning(f"[admin_script_repository] Script not found: {script_id}")
            return script
        except Exception as e:
            logger.error(f"[admin_script_repository] Error fetching script: {e}")
            raise
    
    def update_script(self, script_id: str, new_script: str) -> AdminScript:
        """Update script by ID."""
        try:
            script = self.db.query(AdminScript).filter(
                AdminScript.id == script_id
            ).first()
            if not script:
                logger.warning(f"[admin_script_repository] Script not found for update: {script_id}")
                return None
            
            script.script = new_script
            self.db.commit()
            self.db.refresh(script)
            logger.info(f"[admin_script_repository] Script updated: {script_id}")
            return script
        except Exception as e:
            logger.error(f"[admin_script_repository] Error updating script: {e}")
            self.db.rollback()
            raise
