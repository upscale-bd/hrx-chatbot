from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.audio_comparison.dto.audio_comparison_dto import (
    AudioComparisonRequest, AudioComparisonResponse, AudioResultResponse, AudioStatusResponse
)
from app.audio_comparison.usecase.audio_comparison_usecase import AudioComparisonUsecase
from infrastructure.database import get_db
from common.logger import get_logger


logger = get_logger("audio_comparison_handler")
router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("/upload", response_model=AudioComparisonResponse)
async def upload_audio(
    user_name: str = Form(...),
    admin_name: str = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and transcribe audio file, compare with admin script.
    
    - **user_name**: User/Student name
    - **admin_name**: Admin whose script to compare against
    - **audio_file**: Audio file to transcribe (WAV, MP3, etc.)
    
    Returns success message, comparison ID, and similarity percentage.
    """
    logger.info(f"[audio_handler] POST /audio/upload received from user: {user_name}")
    logger.info(f"[audio_handler] Audio file: {audio_file.filename}, Admin: {admin_name}")
    
    try:
        # Read audio file content
        audio_content = await audio_file.read()
        
        # Process audio upload
        usecase = AudioComparisonUsecase(db)
        response = usecase.process_audio_upload(
            user_name=user_name,
            admin_name=admin_name,
            audio_file_content=audio_content,
            audio_file_name=audio_file.filename
        )
        
        logger.info(f"[audio_handler] Audio processing completed | ID: {response.comparison_id}")
        return response
    
    except Exception as e:
        logger.error(f"[audio_handler] Error processing audio: {e}")
        return AudioComparisonResponse(
            success=False,
            name=user_name,
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