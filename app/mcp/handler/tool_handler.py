from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from infrastructure.database import get_db
from app.mcp.dto.tool_dto import ToolCreate
from app.mcp.usecase.tool_usecase import (
    create_tool_usecase,
    get_tool_usecase,
    list_tools_usecase,
    disable_tool_usecase,
)
from common.logger import get_logger


logger = get_logger("tool_handler")
router = APIRouter(prefix="/mcp/tool", tags=["MCP Tools"])


@router.post("/", status_code=201)
def create_tool_endpoint(payload: ToolCreate, db: Session = Depends(get_db)):
    logger.info(f"[tool_handler] POST /mcp/tool/ | tool_name='{payload.tool_name}' module='{payload.module_name}'")
    try:
        t = create_tool_usecase(db, payload.model_dump())
        logger.info(f"[tool_handler] Tool created successfully | tool_name='{t.tool_name}'")
        return {"tool_name": t.tool_name, "module_name": t.module_name, "active": t.active}
    except Exception as exc:
        logger.error(f"[tool_handler] create_tool_endpoint failed | tool_name='{payload.tool_name}' | error={exc}")
        raise HTTPException(status_code=500, detail=f"Failed to create tool: {exc}")


@router.get("/")
def list_tools_endpoint(db: Session = Depends(get_db)):
    logger.info("[tool_handler] GET /mcp/tool/ — listing all tools")
    try:
        tools = list_tools_usecase(db)
        logger.info(f"[tool_handler] Returning {len(tools)} tool(s)")
        return [
            {"tool_name": t.tool_name, "endpoint": t.endpoint, "active": t.active}
            for t in tools
        ]
    except Exception as exc:
        logger.error(f"[tool_handler] list_tools_endpoint failed | error={exc}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {exc}")


@router.get("/{tool_name}")
def get_tool_endpoint(tool_name: str, db: Session = Depends(get_db)):
    logger.info(f"[tool_handler] GET /mcp/tool/{tool_name}")
    try:
        t = get_tool_usecase(db, tool_name)
        if not t:
            logger.warning(f"[tool_handler] Tool not found | tool_name='{tool_name}'")
            raise HTTPException(status_code=404, detail="Tool not found")
        logger.info(f"[tool_handler] Tool found | tool_name='{t.tool_name}' active={t.active}")
        return {"tool_name": t.tool_name, "module_name": t.module_name, "endpoint": t.endpoint, "method": t.method, "active": t.active}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[tool_handler] get_tool_endpoint failed | tool_name='{tool_name}' | error={exc}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tool: {exc}")


@router.post("/{tool_name}/disable")
def disable_tool_endpoint(tool_name: str, db: Session = Depends(get_db)):
    logger.info(f"[tool_handler] POST /mcp/tool/{tool_name}/disable")
    try:
        t = disable_tool_usecase(db, tool_name)
        if not t:
            logger.warning(f"[tool_handler] Tool not found for disable | tool_name='{tool_name}'")
            raise HTTPException(status_code=404, detail="Tool not found")
        logger.info(f"[tool_handler] Tool disabled | tool_name='{t.tool_name}' active={t.active}")
        return {"tool_name": t.tool_name, "active": t.active}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[tool_handler] disable_tool_endpoint failed | tool_name='{tool_name}' | error={exc}")
        raise HTTPException(status_code=500, detail=f"Failed to disable tool: {exc}")
