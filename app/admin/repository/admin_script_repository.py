from sqlalchemy.orm import Session
from models.admin_script import AdminScript, AdminUser
from models.audio_comparison import AudioComparison, UserAudioStats
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

    def create_admin_user(self, name: str, email: str, password_hash: str) -> AdminUser:
        """Create a new admin user."""
        try:
            admin_user = AdminUser(
                name=name,
                email=email,
                password_hash=password_hash
            )
            self.db.add(admin_user)
            self.db.commit()
            self.db.refresh(admin_user)
            logger.info(f"[admin_script_repository] Admin user created: {email} | ID: {admin_user.id}")
            return admin_user
        except Exception as e:
            logger.error(f"[admin_script_repository] Error creating admin user: {e}")
            self.db.rollback()
            raise

    def get_admin_by_email(self, email: str) -> AdminUser:
        """Get admin user by email."""
        try:
            admin_user = self.db.query(AdminUser).filter(
                AdminUser.email == email
            ).first()
            if not admin_user:
                logger.warning(f"[admin_script_repository] Admin user not found: {email}")
            return admin_user
        except Exception as e:
            logger.error(f"[admin_script_repository] Error fetching admin user by email: {e}")
            raise

    def get_admin_by_token(self, token: str) -> AdminUser:
        """Get admin user by auth token."""
        try:
            admin_user = self.db.query(AdminUser).filter(
                AdminUser.auth_token == token
            ).first()
            if not admin_user:
                logger.warning("[admin_script_repository] Admin token not found")
            return admin_user
        except Exception as e:
            logger.error(f"[admin_script_repository] Error fetching admin user by token: {e}")
            raise

    def set_admin_token(self, admin_id: str, token: str, expires_at) -> None:
        """Set admin auth token and expiry."""
        try:
            admin_user = self.db.query(AdminUser).filter(
                AdminUser.id == admin_id
            ).first()
            if not admin_user:
                logger.warning(f"[admin_script_repository] Admin user not found for token update: {admin_id}")
                return
            admin_user.auth_token = token
            admin_user.token_expires_at = expires_at
            self.db.commit()
            logger.info(f"[admin_script_repository] Admin token set | admin_id={admin_id}")
        except Exception as e:
            logger.error(f"[admin_script_repository] Error setting admin token: {e}")
            self.db.rollback()
            raise

    def is_processing_enabled(self) -> bool:
        """Check if project processing is enabled."""
        try:
            result = self.db.query(AudioComparison).filter(
                AudioComparison.is_enabled == True
            ).first()
            return result is not None if self.db.query(AudioComparison).count() > 0 else True
        except Exception as e:
            logger.error(f"[admin_script_repository] Error checking if processing enabled: {e}")
            return True

    def set_processing_enabled(self, enabled: bool) -> None:
        """Enable or disable all audio processing."""
        try:
            self.db.query(AudioComparison).update({"is_enabled": enabled})
            self.db.commit()
            logger.info(f"[admin_script_repository] Set processing_enabled to {enabled}")
        except Exception as e:
            logger.error(f"[admin_script_repository] Error setting processing enabled: {e}")
            self.db.rollback()
            raise

    def get_user_stats_from_db(self, user_id: str) -> dict:
        """Get user statistics from stats table.

        Args:
            user_id: Unique user identifier

        Returns:
            Dictionary with user stats or empty dict if not found
        """
        try:
            stats = self.db.query(UserAudioStats).filter(
                UserAudioStats.user_id == user_id
            ).first()

            if not stats:
                logger.warning(f"[admin_script_repository] Stats not found for user_id: {user_id}")
                return {}

            return {
                "user_id": stats.user_id,
                "user_name": stats.user_name,
                "submission_count": stats.submission_count,
                "average_score": stats.average_score,
                "last_score": stats.last_score,
                "last_submission_time": stats.last_submission_time
            }
        except Exception as e:
            logger.error(f"[admin_script_repository] Error fetching stats for user_id {user_id}: {e}")
            return {}

    def get_all_user_stats_from_db(self) -> list:
        """Get all user statistics from stats table.

        Returns:
            List of user stats dictionaries
        """
        try:
            all_stats = self.db.query(UserAudioStats).order_by(
                UserAudioStats.updated_at.desc()
            ).all()

            stats_list = []
            for stat in all_stats:
                stats_list.append({
                    "user_id": stat.user_id,
                    "user_name": stat.user_name,
                    "submission_count": stat.submission_count,
                    "average_score": stat.average_score,
                    "last_score": stat.last_score,
                    "last_submission_time": stat.last_submission_time
                })

            logger.info(f"[admin_script_repository] Fetched stats for {len(stats_list)} users from stats table")
            return stats_list
        except Exception as e:
            logger.error(f"[admin_script_repository] Error fetching all user stats: {e}")
            return []
