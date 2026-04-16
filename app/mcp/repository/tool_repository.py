import json
from typing import Optional, List
from sqlalchemy.orm import Session
from models.tool_registry import ToolRegistry
from common.logger import get_logger

logger = get_logger("tool_repository")


def add_tool(db: Session, payload: dict) -> ToolRegistry:
    logger.info(f"[tool_repository] add_tool | tool_name='{payload.get('tool_name')}' module='{payload.get('module_name')}' endpoint='{payload.get('endpoint')}'")
    try:
        tool = ToolRegistry(
            module_name=payload.get("module_name"),
            tool_name=payload.get("tool_name"),
            endpoint=payload.get("endpoint"),
            method=payload.get("method", "POST"),
            inject_org=payload.get("inject_org", True),
            body_schema=json.dumps(payload.get("body_schema") or {}),
            report_columns=json.dumps(payload.get("report_columns") or []),
            active=True,
        )
        logger.info("[tool_repository] Adding tool to DB session")
        db.add(tool)
        db.commit()
        db.refresh(tool)
        logger.info(f"[tool_repository] Tool committed | id={tool.id} tool_name='{tool.tool_name}'")
        return tool
    except Exception as exc:
        logger.error(f"[tool_repository] add_tool failed | tool_name='{payload.get('tool_name')}' | error={exc}")
        db.rollback()
        raise


def fetch_tool(db: Session, tool_name: str) -> Optional[ToolRegistry]:
    logger.info(f"[tool_repository] fetch_tool | tool_name='{tool_name}'")
    try:
        result = db.query(ToolRegistry).filter(ToolRegistry.tool_name == tool_name).first()
        if result:
            logger.info(f"[tool_repository] Found tool | id={result.id} active={result.active}")
        else:
            logger.warning(f"[tool_repository] Tool not found | tool_name='{tool_name}'")
        return result
    except Exception as exc:
        logger.error(f"[tool_repository] fetch_tool failed | tool_name='{tool_name}' | error={exc}")
        raise


def fetch_all_tools(db: Session) -> List[ToolRegistry]:
    logger.info("[tool_repository] fetch_all_tools")
    try:
        results = db.query(ToolRegistry).all()
        logger.info(f"[tool_repository] {len(results)} tool(s) fetched")
        return results
    except Exception as exc:
        logger.error(f"[tool_repository] fetch_all_tools failed | error={exc}")
        raise


def disable_tool_repo(db: Session, tool_name: str) -> Optional[ToolRegistry]:
    logger.info(f"[tool_repository] disable_tool_repo | tool_name='{tool_name}'")
    try:
        tool = fetch_tool(db, tool_name)
        if not tool:
            logger.warning(f"[tool_repository] Cannot disable — tool not found | tool_name='{tool_name}'")
            return None
        logger.info(f"[tool_repository] Setting active=False for tool_name='{tool_name}'")
        tool.active = False
        db.add(tool)
        db.commit()
        db.refresh(tool)
        logger.info(f"[tool_repository] Tool disabled and committed | id={tool.id}")
        return tool
    except Exception as exc:
        logger.error(f"[tool_repository] disable_tool_repo failed | tool_name='{tool_name}' | error={exc}")
        db.rollback()
        raise
