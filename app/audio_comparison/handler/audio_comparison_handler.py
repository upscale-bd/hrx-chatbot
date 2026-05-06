from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.audio_comparison.dto.audio_comparison_dto import (
    AudioComparisonRequest, AudioComparisonResponse, AudioResultResponse, AudioStatusResponse,
    UserAudioStatsResponse, AllUsersStatsResponse, UserCreateRequest, UserCreateResponse, UserResponse, AllUsersResponse
)
from app.audio_comparison.usecase.audio_comparison_usecase import AudioComparisonUsecase
from infrastructure.database import get_db
from common.logger import get_logger


logger = get_logger("audio_comparison_handler")
router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("/upload", response_model=AudioComparisonResponse)
async def upload_audio(
    user_id: str = Form(...),
    admin_name: str = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and transcribe audio file, compare with admin script.
    
    - **user_id**: User ID from /user/create endpoint
    - **admin_name**: Admin whose script to compare against
    - **audio_file**: Audio file to transcribe (WAV, MP3, etc.)
    
    Returns success message, comparison ID, and similarity percentage.
    """
    logger.info(f"[audio_handler] POST /audio/upload received from user_id: {user_id}")
    logger.info(f"[audio_handler] Audio file: {audio_file.filename}, Admin: {admin_name}")
    
    try:
        # Fetch user information
        usecase = AudioComparisonUsecase(db)
        user_result = usecase.get_user(user_id)
        
        if not user_result.get("success"):
            logger.error(f"[audio_handler] User not found: {user_id}")
            return AudioComparisonResponse(
                success=False,
                name="Unknown",
                message="User not found",
                error="invalid_user_id"
            )
        
        user_name = user_result["user_name"]
        logger.info(f"[audio_handler] User found: {user_name}")
        
        # Read audio file content
        audio_content = await audio_file.read()
        
        # Process audio upload
        response = usecase.process_audio_upload(
            user_id=user_id,
            user_name=user_name,
            admin_name=admin_name,
            audio_file_content=audio_content,
            audio_file_name=audio_file.filename
        )
        
        if response.success and response.comparison_id:
            logger.info(f"[audio_handler] Audio processing completed | ID: {response.comparison_id}")
        else:
            logger.warning(f"[audio_handler] Audio processing failed | error={response.error}")
        return response
    
    except Exception as e:
        logger.error(f"[audio_handler] Error processing audio: {e}")
        return AudioComparisonResponse(
            success=False,
            name="Unknown",
            message="Error processing audio",
            error=str(e)
        )


@router.get("/result/{comparison_id}", response_model=AudioResultResponse)
def get_comparison_result(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve audio result by ID - shows name, id, and percentage.
    
    - **comparison_id**: ID of the audio from upload endpoint
    
    Returns name, comparison ID, and similarity percentage.
    """
    logger.info(f"[audio_handler] GET /audio/result/{comparison_id} received")
    
    try:
        usecase = AudioComparisonUsecase(db)
        response = usecase.get_comparison_result(comparison_id)
        
        if response.success:
            logger.info(f"[audio_handler] Result retrieved | Name: {response.name} | ID: {response.comparison_id}")
        else:
            logger.warning(f"[audio_handler] Result not found: {comparison_id}")
        
        return response
    
    except Exception as e:
        logger.error(f"[audio_handler] Error retrieving result: {e}")
        return AudioResultResponse(
            success=False,
            name="",
            comparison_id=comparison_id,
            similarity_percentage=None,
            created_at=None,
            error=str(e)
        )


@router.get("/status/{comparison_id}", response_model=AudioStatusResponse)
def get_transcription_status(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """Check whether the audio for given ID has been transcribed."""
    logger.info(f"[audio_handler] GET /audio/status/{comparison_id} received")
    try:
        usecase = AudioComparisonUsecase(db)
        response = usecase.get_transcription_status(comparison_id)
        if response.success:
            logger.info(f"[audio_handler] Status retrieved | ID: {comparison_id} | transcribed={response.transcribed}")
        else:
            logger.warning(f"[audio_handler] Status check failed for ID: {comparison_id}")
        return response
    except Exception as e:
        logger.error(f"[audio_handler] Error checking transcription status: {e}")
        return AudioStatusResponse(
            success=False,
            comparison_id=comparison_id,
            transcribed=False,
            transcribed_text=None,
            created_at=None,
            error=str(e)
        )

@router.get("/processing")
def check_processing_status(db: Session = Depends(get_db)):
    """Check if processing is enabled or disabled."""
    logger.info("[audio_handler] GET /audio/processing received")
    try:
        usecase = AudioComparisonUsecase(db)
        response = usecase.get_processing_status()
        return response
    except Exception as e:
        logger.error(f"[audio_handler] Error checking processing status: {e}")
        return {"success": False, "message": "Error checking status", "error": str(e)}


@router.put("/processing/{status}")
def set_processing_status(status: str, db: Session = Depends(get_db)):
    """Enable or disable audio processing.
    
    - **status**: 'on' to enable or 'off' to disable
    """
    logger.info(f"[audio_handler] PUT /audio/processing/{status} received")
    try:
        enabled = status.lower() == "on"
        usecase = AudioComparisonUsecase(db)
        response = usecase.set_processing_status(enabled)
        return response
    except Exception as e:
        logger.error(f"[audio_handler] Error setting processing status: {e}")
        return {"success": False, "message": "Error updating status", "error": str(e)}


@router.get("/stats/all", response_model=AllUsersStatsResponse)
def get_all_users_stats(db: Session = Depends(get_db)):
    """Get statistics for all users.
    
    Returns a list of all users with their:
    - Total submission count
    - Average score across all submissions
    - Last submission score
    - Last submission time
    """
    logger.info("[audio_handler] GET /audio/stats/all received")
    try:
        usecase = AudioComparisonUsecase(db)
        result = usecase.get_all_users_stats()
        
        if result["success"]:
            logger.info(f"[audio_handler] Retrieved stats for {result['total_users']} users")
            return AllUsersStatsResponse(
                success=True,
                total_users=result["total_users"],
                users=[UserAudioStatsResponse(**user) for user in result["users"]],
                error=None
            )
        else:
            logger.error(f"[audio_handler] Error: {result.get('error')}")
            return AllUsersStatsResponse(
                success=False,
                total_users=0,
                users=[],
                error=result.get("error")
            )
    except Exception as e:
        logger.error(f"[audio_handler] Error getting all users stats: {e}")
        return AllUsersStatsResponse(
            success=False,
            total_users=0,
            users=[],
            error=str(e)
        )


@router.get("/stats/user/{user_id}", response_model=UserAudioStatsResponse)
def get_user_stats(user_id: str, db: Session = Depends(get_db)):
    """Get audio statistics for a specific user by user_id.
    
    - **user_id**: Unique user identifier
    
    Returns:
    - Total submission count
    - Average score across all submissions
    - Last submission score
    - Last submission time
    """
    logger.info(f"[audio_handler] GET /audio/stats/user/{user_id} received")
    try:
        usecase = AudioComparisonUsecase(db)
        result = usecase.get_user_stats(user_id)
        
        if result["success"]:
            logger.info(f"[audio_handler] Retrieved stats for user_id: {user_id}")
            return UserAudioStatsResponse(
                user_id=result["user_id"],
                user_name=result["user_name"],
                submission_count=result["submission_count"],
                last_score=result["last_score"],
                average_score=result["average_score"],
                last_submission_time=result["last_submission_time"],
                error=None
            )
        else:
            logger.warning(f"[audio_handler] No stats found for user_id: {user_id}")
            return UserAudioStatsResponse(
                user_id=user_id,
                user_name="Unknown",
                submission_count=0,
                last_score=None,
                average_score=0.0,
                last_submission_time=None,
                error=result.get("error")
            )
    except Exception as e:
        logger.error(f"[audio_handler] Error getting user stats: {e}")
        return UserAudioStatsResponse(
            user_id=user_id,
            user_name="Unknown",
            submission_count=0,
            last_score=None,
            average_score=0.0,
            last_submission_time=None,
            error=str(e)
        )


# ==================== USER MANAGEMENT ENDPOINTS ====================

@router.post("/user/create", response_model=UserCreateResponse)
def create_user(
    request: UserCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new user for audio submissions.
    
    - **user_name**: User's name (must be unique)
    
    Returns user ID which will be used for all audio submissions.
    """
    logger.info(f"[audio_handler] POST /user/create received for user: {request.user_name}")
    
    try:
        usecase = AudioComparisonUsecase(db)
        response = usecase.create_user(request.user_name)
        
        if response.success:
            logger.info(f"[audio_handler] User created successfully | ID: {response.user_id} | Name: {response.user_name}")
        else:
            logger.error(f"[audio_handler] Failed to create user: {response.error}")
        
        return response
    
    except Exception as e:
        logger.error(f"[audio_handler] Error creating user: {e}")
        return UserCreateResponse(
            success=False,
            user_id="",
            user_name=request.user_name,
            message="Error creating user",
            error=str(e)
        )


@router.get("/user/info/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user information by user ID.
    
    - **user_id**: User ID from create endpoint
    
    Returns user information.
    """
    logger.info(f"[audio_handler] GET /user/info/{user_id} received")
    
    try:
        usecase = AudioComparisonUsecase(db)
        result = usecase.get_user(user_id)
        
        if result.get("success"):
            logger.info(f"[audio_handler] User info retrieved | ID: {user_id} | Name: {result['user_name']}")
            return UserResponse(
                user_id=result["user_id"],
                user_name=result["user_name"],
                created_at=result["created_at"],
                error=None
            )
        else:
            logger.warning(f"[audio_handler] User not found: {user_id}")
            return UserResponse(
                user_id=user_id,
                user_name="",
                created_at=None,
                error=result.get("error")
            )
    
    except Exception as e:
        logger.error(f"[audio_handler] Error fetching user: {e}")
        return UserResponse(
            user_id=user_id,
            user_name="",
            created_at=None,
            error=str(e)
        )


@router.get("/user/all", response_model=AllUsersResponse)
def get_all_users(db: Session = Depends(get_db)):
    """
    Get list of all users.
    
    Returns all registered users with their IDs and creation times.
    """
    logger.info("[audio_handler] GET /user/all received")
    
    try:
        usecase = AudioComparisonUsecase(db)
        result = usecase.get_all_users()
        
        if result.get("success"):
            logger.info(f"[audio_handler] Retrieved {result['total_users']} users")
            return AllUsersResponse(
                success=True,
                total_users=result["total_users"],
                users=[UserResponse(
                    user_id=u["user_id"],
                    user_name=u["user_name"],
                    created_at=u["created_at"],
                    error=None
                ) for u in result["users"]],
                error=None
            )
        else:
            logger.error(f"[audio_handler] Error: {result.get('error')}")
            return AllUsersResponse(
                success=False,
                total_users=0,
                users=[],
                error=result.get("error")
            )
    
    except Exception as e:
        logger.error(f"[audio_handler] Error fetching all users: {e}")
        return AllUsersResponse(
            success=False,
            total_users=0,
            users=[],
            error=str(e)
        )