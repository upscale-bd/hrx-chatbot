from app.mcp.repository.tool_repository import (
    add_tool,
    fetch_tool,
    fetch_all_tools,
    disable_tool_repo,
)
from common.logger import get_logger

logger = get_logger("tool_usecase")


def create_tool_usecase(db, payload: dict):
    logger.info(f"[tool_usecase] create_tool_usecase | tool_name='{payload.get('tool_name')}'")
    result = add_tool(db, payload)
    logger.info(f"[tool_usecase] Tool persisted | id={result.id} tool_name='{result.tool_name}'")
    return result


def get_tool_usecase(db, tool_name: str):
    logger.info(f"[tool_usecase] get_tool_usecase | tool_name='{tool_name}'")
    result = fetch_tool(db, tool_name)
    if result:
        logger.info(f"[tool_usecase] Tool found | tool_name='{result.tool_name}' active={result.active}")
    else:
        logger.warning(f"[tool_usecase] Tool not found | tool_name='{tool_name}'")
    return result


def list_tools_usecase(db):
    logger.info("[tool_usecase] list_tools_usecase — fetching all tools")
    results = fetch_all_tools(db)
    logger.info(f"[tool_usecase] {len(results)} tool(s) retrieved")
    return results


def disable_tool_usecase(db, tool_name: str):
    logger.info(f"[tool_usecase] disable_tool_usecase | tool_name='{tool_name}'")
    result = disable_tool_repo(db, tool_name)
    if result:
        logger.info(f"[tool_usecase] Tool disabled | tool_name='{result.tool_name}'")
    else:
        logger.warning(f"[tool_usecase] Tool not found for disable | tool_name='{tool_name}'")
    return result
