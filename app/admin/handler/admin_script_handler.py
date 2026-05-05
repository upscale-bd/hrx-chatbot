from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.admin.dto.admin_script_dto import (
    AdminScriptRequest, AdminScriptResponse, AdminScriptGetResponse, AdminScriptUpdateRequest
)
from app.admin.usecase.admin_script_usecase import AdminScriptUsecase
from infrastructure.database import get_db
from common.logger import get_logger


logger = get_logger("admin_script_handler")
router = APIRouter(prefix="/admin", tags=["admin"])


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
