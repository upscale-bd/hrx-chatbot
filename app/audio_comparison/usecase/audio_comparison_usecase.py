import os
import tempfile
from sqlalchemy.orm import Session
from services.gemini.gemini_service import GeminiService
from app.audio_comparison.repository.audio_comparison_repository import AudioComparisonRepository
from app.admin.repository.admin_script_repository import AdminScriptRepository
from app.audio_comparison.dto.audio_comparison_dto import (
    AudioComparisonRequest, AudioComparisonResponse, AudioResultResponse, AudioStatusResponse,
    UserCreateResponse, UserResponse
)
from common.logger import get_logger


logger = get_logger("audio_comparison_usecase")


class AudioComparisonUsecase:
    """Usecase for audio transcription, comparison with admin script, and user management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
        self.repository = AudioComparisonRepository(db)
        self.admin_repository = AdminScriptRepository(db)
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, user_name: str) -> UserCreateResponse:
        """Create a new user.
        
        Args:
            user_name: Name of the user
            
        Returns:
            UserCreateResponse with user ID
        """
        try:
            logger.info(f"[audio_comparison_usecase] Creating user: {user_name}")
            
            user = self.repository.create_user(user_name)
            
            logger.info(f"[audio_comparison_usecase] User created successfully with ID: {user.id}")
            
            return UserCreateResponse(
                success=True,
                user_id=user.id,
                user_name=user.user_name,
                message=f"User '{user_name}' created successfully",
                error=None
            )
        
        except Exception as e:
            logger.error(f"[audio_comparison_usecase] Error creating user: {e}")
            return UserCreateResponse(
                success=False,
                user_id="",
                user_name=user_name,
                message="Error creating user",
                error=str(e)
            )
    
    def get_user(self, user_id: str) -> dict:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user information
        """
        try:
            logger.info(f"[audio_comparison_usecase] Fetching user: {user_id}")
            
            user = self.repository.get_user_by_id(user_id)
            
            if not user:
                logger.warning(f"[audio_comparison_usecase] User not found: {user_id}")
                return {
                    "success": False,
                    "message": f"User not found: {user_id}",
                    "error": "user_not_found"
                }
            
            logger.info(f"[audio_comparison_usecase] User fetched successfully: {user.user_name}")
            
            return {
                "success": True,
                "user_id": user.id,
                "user_name": user.user_name,
                "created_at": user.created_at
            }
        
        except Exception as e:
            logger.error(f"[audio_comparison_usecase] Error fetching user: {e}")
            return {
                "success": False,
                "message": f"Error fetching user",
                "error": str(e)
            }
    
    def get_all_users(self) -> dict:
        """Get all users.
        
        Returns:
            Dictionary with list of all users
        """
        try:
            logger.info("[audio_comparison_usecase] Fetching all users")
            
            users = self.repository.get_all_users()
            
            users_list = [
                {
                    "user_id": user.id,
                    "user_name": user.user_name,
                    "created_at": user.created_at
                }
                for user in users
            ]
            
            logger.info(f"[audio_comparison_usecase] Fetched {len(users_list)} users")
            
            return {
                "success": True,
                "total_users": len(users_list),
                "users": users_list,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"[audio_comparison_usecase] Error fetching all users: {e}")
            return {
                "success": False,
                "total_users": 0,
                "users": [],
                "error": str(e)
            }
    
    # ==================== AUDIO COMPARISON ====================
    
    def process_audio_upload(self, user_id: str, user_name: str, admin_name: str, audio_file_content: bytes, 
                            audio_file_name: str = "audio.wav") -> AudioComparisonResponse:
        """Process audio file: transcribe and compare with admin script.
        
        Args:
            user_id: Unique user identifier (UUID or custom ID)
            user_name: User display name
            admin_name: Admin who owns the script
            audio_file_content: Binary content of the audio file
            audio_file_name: Name of the audio file
            
        Returns:
            AudioComparisonResponse with upload confirmation and similarity
        """
        try:
            logger.info(f"[audio_comparison_usecase] Starting audio processing | User ID: {user_id} | User Name: {user_name} | Admin: {admin_name}")
            
            # Check if processing is enabled
            if not self.admin_repository.is_processing_enabled():
                logger.warning("[audio_comparison_usecase] Processing is disabled")
                return AudioComparisonResponse(
                    success=False,
                    name=user_name,
                    message="Your project is currently off",
                    error="Processing disabled"
                )
            
            # Get admin script
            logger.info(f"[audio_comparison_usecase] Loading admin script")
            admin_scripts = self.db.query(__import__('models.admin_script', fromlist=['AdminScript']).AdminScript).filter_by(admin_name=admin_name).all()
            
            if not admin_scripts:
                logger.error(f"[audio_comparison_usecase] No script found for admin: {admin_name}")
                return AudioComparisonResponse(
                    success=False,
                    name=user_name,
                    message=f"No script found for admin: {admin_name}",
                    error="Admin script not found"
                )
            
            admin_script = admin_scripts[0].script
            logger.info(f"[audio_comparison_usecase] Admin script loaded: {len(admin_script)} characters")
            
            # Save audio file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_file_content)
                temp_audio_path = temp_file.name
            
            try:
                # Transcribe audio using Gemini
                logger.info("[audio_comparison_usecase] Transcribing audio")
                transcribed_text = self.gemini_service.transcribe_audio(temp_audio_path)
                logger.info(f"[audio_comparison_usecase] Transcription successful: {len(transcribed_text)} characters")
                
                # Calculate similarity percentage
                logger.info("[audio_comparison_usecase] Calculating similarity with admin script")
                similarity_percentage = self.gemini_service.calculate_similarity_percentage(
                    admin_script, transcribed_text
                )
                logger.info(f"[audio_comparison_usecase] Similarity: {similarity_percentage}%")
                
                # Save to database
                logger.info("[audio_comparison_usecase] Saving to database")
                comparison = self.repository.save_comparison(
                    user_id=user_id,
                    user_name=user_name,
                    admin_name=admin_name,
                    transcribed_text=transcribed_text,
                    admin_script=admin_script,
                    similarity_percentage=similarity_percentage,
                    audio_file_name=audio_file_name
                )
                logger.info(f"[audio_comparison_usecase] Audio saved with ID: {comparison.id}")
                
                return AudioComparisonResponse(
                    success=True,
                    name=user_name,
                    message=f"Audio file sent successfully. Similarity: {similarity_percentage:.2f}%",
                    comparison_id=comparison.id,
                    similarity_percentage=similarity_percentage
                )
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                    logger.info("[audio_comparison_usecase] Temporary audio file deleted")
        
        except Exception as e:
            logger.error(f"[audio_comparison_usecase] Error in process_audio_upload: {e}")
            return AudioComparisonResponse(
                success=False,
                name=user_name,
                message="Error processing audio",
                error=str(e)
            )
    
    def get_comparison_result(self, comparison_id: str) -> AudioResultResponse:
        """Retrieve comparison result by ID - name, id, and percentage.
        
        Args:
            comparison_id: ID of the comparison result
            
        Returns:
            AudioResultResponse with name, id, and percentage
        """
        try:
            logger.info(f"[audio_comparison_usecase] Fetching comparison: {comparison_id}")
            
            comparison = self.repository.get_comparison_by_id(comparison_id)
            
            if not comparison:
                logger.warning(f"[audio_comparison_usecase] Comparison not found: {comparison_id}")
                return AudioResultResponse(
                    success=False,
                    name="",
                    comparison_id=comparison_id,
                    similarity_percentage=None,
                    created_at=None,
                    error="Comparison not found"
                )
            
            logger.info(f"[audio_comparison_usecase] Comparison retrieved successfully")
            
            return AudioResultResponse(
                success=True,
                name=comparison.user_name,
                comparison_id=comparison.id,
                similarity_percentage=comparison.similarity_percentage,
                created_at=comparison.created_at
            )
        
        except Exception as e:
            logger.error(f"[audio_comparison_usecase] Error in get_comparison_result: {e}")
            return AudioResultResponse(
                success=False,
                name="",
                comparison_id=comparison_id,
                similarity_percentage=None,
                created_at=None,
                error=str(e)
            )

    def get_transcription_status(self, comparison_id: str) -> AudioStatusResponse:
        """Check whether the audio identified by comparison_id has been transcribed.

        Returns AudioStatusResponse with boolean and optional transcribed text.
        """
        try:
            logger.info(f"[audio_comparison_usecase] Checking transcription status: {comparison_id}")
            comparison = self.repository.get_comparison_by_id(comparison_id)

            if not comparison:
                logger.warning(f"[audio_comparison_usecase] Comparison not found: {comparison_id}")
                return AudioStatusResponse(
                    success=False,
                    comparison_id=comparison_id,
                    transcribed=False,
                    transcribed_text=None,
                    created_at=None,
                    message="Comparison not found",
                    error="not_found"
                )

            transcribed = bool(comparison.transcribed_text and comparison.transcribed_text.strip())
            return AudioStatusResponse(
                success=True,
                comparison_id=comparison.id,
                transcribed=transcribed,
                transcribed_text=comparison.transcribed_text if transcribed else None,
                created_at=comparison.created_at,
                message="Transcribed" if transcribed else "Not transcribed"
            )

        except Exception as e:
            logger.error(f"[audio_comparison_usecase] Error checking transcription status: {e}")
            return AudioStatusResponse(
                success=False,
                comparison_id=comparison_id,
                transcribed=False,
                transcribed_text=None,
                created_at=None,
                error=str(e)
            )

