from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.admin.dto.admin_script_dto import (
    AdminScriptRequest, AdminScriptResponse, AdminScriptGetResponse, AdminScriptUpdateRequest,
    UserAudioStatsResponse, AllUsersStatsResponse, AdminCreateRequest, AdminCreateResponse,
    AdminLoginRequest, AdminLoginResponse
)
from app.admin.usecase.admin_script_usecase import AdminScriptUsecase
from infrastructure.database import get_db
from common.logger import get_logger


logger = get_logger("admin_script_handler")
router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin_token(
    x_admin_token: str = Header(None, alias="X-Admin-Token"),
    db: Session = Depends(get_db)
):
    """Validate admin token from X-Admin-Token header."""
    if not x_admin_token:
        raise HTTPException(status_code=401, detail="Missing admin token")

    usecase = AdminScriptUsecase(db)
    if not usecase.validate_admin_token(x_admin_token):
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")
    return True


@router.post("/create", response_model=AdminCreateResponse)
def create_admin_user(
    req: AdminCreateRequest,
    db: Session = Depends(get_db)
):
    """Create an admin user with name, email, and password."""
    logger.info(f"[admin_script_handler] POST /admin/create received for email: {req.email}")
    try:
        usecase = AdminScriptUsecase(db)
        response = usecase.create_admin_user(req)
        return response
    except Exception as e:
        logger.error(f"[admin_script_handler] Error creating admin user: {e}")
        return AdminCreateResponse(
            success=False,
            id="",
            name=req.name,
            email=req.email,
            message="Error creating admin user",
            error=str(e)
        )


@router.post("/login", response_model=AdminLoginResponse)
def login_admin_user(
    req: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """Login admin user with email and password."""
    logger.info(f"[admin_script_handler] POST /admin/login received for email: {req.email}")
    try:
        usecase = AdminScriptUsecase(db)
        response = usecase.login_admin_user(req)
        return response
    except Exception as e:
        logger.error(f"[admin_script_handler] Error logging in admin user: {e}")
        return AdminLoginResponse(
            success=False,
            token="",
            expires_at=None,
            message="Error logging in",
            error=str(e)
        )


@router.post("/script", response_model=AdminScriptResponse)
def save_script(
    req: AdminScriptRequest,
    db: Session = Depends(get_db)
):
    """
    Save admin script to database.
    
    - **admin_name**: Name of the admin
    - **script**: Script content to save
    
    Returns script ID and confirmation.
    """
    logger.info(f"[admin_script_handler] POST /admin/script received")
    logger.info(f"[admin_script_handler] Admin: {req.admin_name} | Script length: {len(req.script)}")
    
    try:
        usecase = AdminScriptUsecase(db)
        response = usecase.save_script(req)
        
        if response.success:
            logger.info(f"[admin_script_handler] Script saved | ID: {response.id}")
        else:
            logger.warning(f"[admin_script_handler] Failed to save script")
        
        return response
    
    except Exception as e:
        logger.error(f"[admin_script_handler] Error saving script: {e}")
        return AdminScriptResponse(
            success=False,
            id="",
            admin_name=req.admin_name,
            script=req.script,
            message="Error saving script",
            error=str(e)
        )


@router.get("/script/{script_id}", response_model=AdminScriptGetResponse)
def get_script(
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve script by ID.
    
    - **script_id**: ID of the script to retrieve
    
    Returns script details with admin name and content.
    """
    logger.info(f"[admin_script_handler] GET /admin/script/{script_id} received")
    
    try:
        usecase = AdminScriptUsecase(db)
        response = usecase.get_script(script_id)
        
        if response.success:
            logger.info(f"[admin_script_handler] Script retrieved | Admin: {response.admin_name}")
        else:
            logger.warning(f"[admin_script_handler] Script not found: {script_id}")
        
        return response
    
    except Exception as e:
        logger.error(f"[admin_script_handler] Error retrieving script: {e}")
        return AdminScriptGetResponse(
            success=False,
            id=script_id,
            admin_name="",
            script="",
            created_at=None,
            error=str(e)
        )


@router.put("/script/{script_id}", response_model=AdminScriptGetResponse)
def update_script(
    script_id: str,
    req: AdminScriptUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update script by ID.
    
    - **script_id**: ID of the script to update
    - **script**: New script content
    
    Returns updated script details.
    """
    logger.info(f"[admin_script_handler] PUT /admin/script/{script_id} received")
    logger.info(f"[admin_script_handler] New script length: {len(req.script)}")
    
    try:
        usecase = AdminScriptUsecase(db)
        response = usecase.update_script(script_id, req)
        
        if response.success:
            logger.info(f"[admin_script_handler] Script updated | Admin: {response.admin_name}")
        else:
            logger.warning(f"[admin_script_handler] Failed to update script: {script_id}")
        
        return response
    
    except Exception as e:
        logger.error(f"[admin_script_handler] Error updating script: {e}")
        return AdminScriptGetResponse(
            success=False,
            id=script_id,
            admin_name="",
            script="",
            created_at=None,
            error=str(e)
        )


@router.get("/audio/processing")
def check_processing_status(db: Session = Depends(get_db)):
    """Check if processing is enabled or disabled."""
    logger.info("[admin_script_handler] GET /admin/audio/processing received")
    try:
        usecase = AdminScriptUsecase(db)
        response = usecase.get_processing_status()
        return response
    except Exception as e:
        logger.error(f"[admin_script_handler] Error checking processing status: {e}")
        return {"success": False, "message": "Error checking status", "error": str(e)}


@router.put("/audio/processing/{status}")
def set_processing_status(status: str, db: Session = Depends(get_db)):
    """Enable or disable audio processing.

    - **status**: 'on' to enable or 'off' to disable
    """
    logger.info(f"[admin_script_handler] PUT /admin/audio/processing/{status} received")
    try:
        enabled = status.lower() == "on"
        usecase = AdminScriptUsecase(db)
        response = usecase.set_processing_status(enabled)
        return response
    except Exception as e:
        logger.error(f"[admin_script_handler] Error setting processing status: {e}")
        return {"success": False, "message": "Error updating status", "error": str(e)}


@router.get("/audio/stats/all", response_model=AllUsersStatsResponse)
def get_all_users_stats(
    db: Session = Depends(get_db),
    _authorized: bool = Depends(require_admin_token)
):
    """Get statistics for all users.

    Returns a list of all users with their:
    - Total submission count
    - Average score across all submissions
    - Last submission score
    - Last submission time
    """
    logger.info("[admin_script_handler] GET /admin/audio/stats/all received")
    try:
        usecase = AdminScriptUsecase(db)
        result = usecase.get_all_users_stats()

        if result["success"]:
            logger.info(f"[admin_script_handler] Retrieved stats for {result['total_users']} users")
            return AllUsersStatsResponse(
                success=True,
                total_users=result["total_users"],
                users=[UserAudioStatsResponse(**user) for user in result["users"]],
                error=None
            )
        else:
            logger.error(f"[admin_script_handler] Error: {result.get('error')}")
            return AllUsersStatsResponse(
                success=False,
                total_users=0,
                users=[],
                error=result.get("error")
            )
    except Exception as e:
        logger.error(f"[admin_script_handler] Error getting all users stats: {e}")
        return AllUsersStatsResponse(
            success=False,
            total_users=0,
            users=[],
            error=str(e)
        )


@router.get("/audio/stats/user/{user_id}", response_model=UserAudioStatsResponse)
def get_user_stats(
    user_id: str,
    db: Session = Depends(get_db),
    _authorized: bool = Depends(require_admin_token)
):
    """Get audio statistics for a specific user by user_id.

    - **user_id**: Unique user identifier

    Returns:
    - Total submission count
    - Average score across all submissions
    - Last submission score
    - Last submission time
    """
    logger.info(f"[admin_script_handler] GET /admin/audio/stats/user/{user_id} received")
    try:
        usecase = AdminScriptUsecase(db)
        result = usecase.get_user_stats(user_id)

        if result["success"]:
            logger.info(f"[admin_script_handler] Retrieved stats for user_id: {user_id}")
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
            logger.warning(f"[admin_script_handler] No stats found for user_id: {user_id}")
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
        logger.error(f"[admin_script_handler] Error getting user stats: {e}")
        return UserAudioStatsResponse(
            user_id=user_id,
            user_name="Unknown",
            submission_count=0,
            last_score=None,
            average_score=0.0,
            last_submission_time=None,
            error=str(e)
        )
