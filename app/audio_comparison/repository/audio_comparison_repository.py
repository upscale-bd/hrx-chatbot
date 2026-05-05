from sqlalchemy.orm import Session
from models.audio_comparison import AudioComparison
from common.logger import get_logger


logger = get_logger("audio_comparison_repository")


class AudioComparisonRepository:
    """Repository for audio comparison data operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_comparison(self, user_name: str, admin_name: str, transcribed_text: str,
                       admin_script: str, similarity_percentage: float = None,
                       audio_file_name: str = None) -> AudioComparison:
        """Save audio comparison result to database."""
        try:
            comparison = AudioComparison(
                user_name=user_name,
                admin_name=admin_name,
                transcribed_text=transcribed_text,
                admin_script=admin_script,
                similarity_percentage=similarity_percentage,
                audio_file_name=audio_file_name
            )
            self.db.add(comparison)
            self.db.commit()
            self.db.refresh(comparison)
            logger.info(f"[audio_comparison_repository] Saved comparison with ID: {comparison.id}")
            return comparison
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error saving comparison: {e}")
            self.db.rollback()
            raise
    
    def get_comparison_by_id(self, comparison_id: str) -> AudioComparison:
        """Get audio comparison result by ID."""
        try:
            comparison = self.db.query(AudioComparison).filter(
                AudioComparison.id == comparison_id
            ).first()
            if not comparison:
                logger.warning(f"[audio_comparison_repository] Comparison not found: {comparison_id}")
            return comparison
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error fetching comparison: {e}")
            raise
    
    def get_comparisons_by_user(self, user_name: str, limit: int = 100) -> list:
        """Get all comparisons for a user."""
        try:
            comparisons = self.db.query(AudioComparison).filter(
                AudioComparison.user_name == user_name
            ).order_by(AudioComparison.created_at.desc()).limit(limit).all()
            logger.info(f"[audio_comparison_repository] Fetched {len(comparisons)} comparisons for user: {user_name}")
            return comparisons
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error fetching comparisons: {e}")
            raise

    def is_processing_enabled(self) -> bool:
        """Check if project processing is enabled."""
        try:
            # Check if any comparison has is_enabled=True; if none exist, default to True
            result = self.db.query(AudioComparison).filter(
                AudioComparison.is_enabled == True
            ).first()
            return result is not None if self.db.query(AudioComparison).count() > 0 else True
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error checking if processing enabled: {e}")
            return True  # Default to enabled if error

    def set_processing_enabled(self, enabled: bool) -> None:
        """Enable or disable all audio processing."""
        try:
            self.db.query(AudioComparison).update({"is_enabled": enabled})
            self.db.commit()
            logger.info(f"[audio_comparison_repository] Set processing_enabled to {enabled}")
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error setting processing enabled: {e}")
            self.db.rollback()
            raise
            raise
