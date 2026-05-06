from sqlalchemy.orm import Session
from models.audio_comparison import AudioComparison, UserAudioStats, User
from common.logger import get_logger


logger = get_logger("audio_comparison_repository")


class AudioComparisonRepository:
    """Repository for audio comparison data operations and user management."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, user_name: str) -> User:
        """Create a new user.
        
        Args:
            user_name: Name of the user (must be unique)
            
        Returns:
            User object with generated ID
        """
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(
                User.user_name == user_name
            ).first()
            
            if existing_user:
                logger.warning(f"[audio_comparison_repository] User already exists: {user_name}")
                return existing_user
            
            user = User(user_name=user_name)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"[audio_comparison_repository] Created user: {user_name} with ID: {user.id}")
            return user
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error creating user: {e}")
            self.db.rollback()
            raise
    
    def get_user_by_id(self, user_id: str) -> User:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None if not found
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"[audio_comparison_repository] User not found: {user_id}")
            return user
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error fetching user: {e}")
            raise
    
    def get_user_by_name(self, user_name: str) -> User:
        """Get user by name.
        
        Args:
            user_name: User name
            
        Returns:
            User object or None if not found
        """
        try:
            user = self.db.query(User).filter(User.user_name == user_name).first()
            if not user:
                logger.warning(f"[audio_comparison_repository] User not found: {user_name}")
            return user
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error fetching user: {e}")
            raise
    
    def get_all_users(self) -> list:
        """Get all users.
        
        Returns:
            List of all User objects
        """
        try:
            users = self.db.query(User).order_by(User.created_at.desc()).all()
            logger.info(f"[audio_comparison_repository] Fetched {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error fetching all users: {e}")
            raise
    
    # ==================== AUDIO COMPARISON ====================
    
    def save_comparison(self, user_id: str, user_name: str, admin_name: str, transcribed_text: str,
                       admin_script: str, similarity_percentage: float = None,
                       audio_file_name: str = None) -> AudioComparison:
        """Save audio comparison result to database.
        
        Args:
            user_id: Unique user identifier (UUID or custom ID)
            user_name: User display name
            admin_name: Admin name
            transcribed_text: Transcribed audio text
            admin_script: Admin script to compare against
            similarity_percentage: Calculated similarity score
            audio_file_name: Name of the audio file
        """
        try:
            comparison = AudioComparison(
                user_id=user_id,
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
            
            # Update user statistics
            self.update_user_stats(user_id, user_name)
            
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
    
    def get_comparisons_by_user(self, user_id: str, limit: int = 100) -> list:
        """Get all comparisons for a user by user_id.
        
        Args:
            user_id: Unique user identifier
            limit: Maximum number of records to fetch
            
        Returns:
            List of AudioComparison records for the user
        """
        try:
            comparisons = self.db.query(AudioComparison).filter(
                AudioComparison.user_id == user_id
            ).order_by(AudioComparison.created_at.desc()).limit(limit).all()
            logger.info(f"[audio_comparison_repository] Fetched {len(comparisons)} comparisons for user_id: {user_id}")
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

    def get_all_user_stats(self) -> list:
        """Get statistics for all users - count, average score, last score, last submission time."""
        try:
            from sqlalchemy import func
            
            # Get all unique user_ids with their stats
            user_stats = self.db.query(
                AudioComparison.user_id,
                AudioComparison.user_name,
                func.count(AudioComparison.id).label("submission_count"),
                func.avg(AudioComparison.similarity_percentage).label("average_score"),
                func.max(AudioComparison.created_at).label("last_submission_time")
            ).filter(AudioComparison.user_id != None).group_by(AudioComparison.user_id, AudioComparison.user_name).all()
            
            stats_list = []
            for stat in user_stats:
                # Get the last score for this user_id
                last_record = self.db.query(AudioComparison).filter(
                    AudioComparison.user_id == stat.user_id
                ).order_by(AudioComparison.created_at.desc()).first()
                
                stats_list.append({
                    "user_id": stat.user_id,
                    "user_name": stat.user_name,
                    "submission_count": stat.submission_count,
                    "average_score": round(stat.average_score, 2) if stat.average_score else 0.0,
                    "last_score": last_record.similarity_percentage if last_record else None,
                    "last_submission_time": stat.last_submission_time
                })
            
            logger.info(f"[audio_comparison_repository] Fetched stats for {len(stats_list)} users")
            return stats_list
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error fetching user stats: {e}")
            raise

    def get_user_average_score(self, user_id: str) -> float:
        """Get average score for a specific user by user_id.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Average similarity score rounded to 2 decimals
        """
        try:
            from sqlalchemy import func
            
            avg_score = self.db.query(
                func.avg(AudioComparison.similarity_percentage)
            ).filter(
                AudioComparison.user_id == user_id,
                AudioComparison.similarity_percentage != None
            ).scalar()
            
            return round(avg_score, 2) if avg_score else 0.0
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error calculating average score for user_id {user_id}: {e}")
            return 0.0

    def update_user_stats(self, user_id: str, user_name: str) -> None:
        """Update or create user statistics after a new submission.
        
        Args:
            user_id: Unique user identifier
            user_name: User display name
        """
        try:
            # Calculate current stats from AudioComparison table
            from sqlalchemy import func
            
            stats_data = self.db.query(
                func.count(AudioComparison.id).label("submission_count"),
                func.avg(AudioComparison.similarity_percentage).label("average_score")
            ).filter(
                AudioComparison.user_id == user_id
            ).first()

            last_record = self.db.query(AudioComparison).filter(
                AudioComparison.user_id == user_id
            ).order_by(AudioComparison.created_at.desc()).first()
            
            submission_count = stats_data.submission_count or 0
            average_score = round(stats_data.average_score, 2) if stats_data.average_score else 0.0
            last_score = last_record.similarity_percentage if last_record else None
            last_submission_time = last_record.created_at if last_record else None
            
            # Check if user stats already exists
            existing_stats = self.db.query(UserAudioStats).filter(
                UserAudioStats.user_id == user_id
            ).first()
            
            if existing_stats:
                # Update existing stats
                existing_stats.user_name = user_name
                existing_stats.submission_count = submission_count
                existing_stats.average_score = average_score
                existing_stats.last_score = last_score
                existing_stats.last_submission_time = last_submission_time
                self.db.commit()
                logger.info(f"[audio_comparison_repository] Updated stats for user_id: {user_id}")
            else:
                # Create new stats record
                new_stats = UserAudioStats(
                    user_id=user_id,
                    user_name=user_name,
                    submission_count=submission_count,
                    average_score=average_score,
                    last_score=last_score,
                    last_submission_time=last_submission_time
                )
                self.db.add(new_stats)
                self.db.commit()
                logger.info(f"[audio_comparison_repository] Created stats for user_id: {user_id}")
        
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error updating user stats for {user_id}: {e}")
            self.db.rollback()
            # Don't raise - stats update should not fail the main submission

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
                logger.warning(f"[audio_comparison_repository] Stats not found for user_id: {user_id}")
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
            logger.error(f"[audio_comparison_repository] Error fetching stats for user_id {user_id}: {e}")
            return {}

    def get_all_user_stats_from_db(self) -> list:
        """Get all user statistics from stats table (fast, no calculation needed).
        
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
            
            logger.info(f"[audio_comparison_repository] Fetched stats for {len(stats_list)} users from stats table")
            return stats_list
        except Exception as e:
            logger.error(f"[audio_comparison_repository] Error fetching all user stats: {e}")
            return []

