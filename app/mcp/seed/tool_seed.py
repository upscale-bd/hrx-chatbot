"""
HRX Tool Registry Seed
----------------------
Auto-registers all known HRX tools on startup.
Uses INSERT OR IGNORE pattern — safe to call multiple times.
Add new tools here as you integrate more HRX endpoints.
"""
import json
from sqlalchemy.orm import Session
from models.tool_registry import ToolRegistry
from common.logger import get_logger

logger = get_logger("tool_seed")

# ─────────────────────────────────────────────
# Define all HRX tools here
# tool_name must match exactly what Gemini will extract
# ─────────────────────────────────────────────
HRX_TOOLS = [
    {
        "module_name": "attendance",
        "tool_name": "get_attendance",
        "endpoint": "api/attendance/attendance-list",
        "method": "GET",
        "inject_org": True,
        "body_schema": {
            "page": 1,
            "pageSize": 10,
            "startDate": "YYYY-MM-DD",
            "endDate": "YYYY-MM-DD",
        },
        "local_filters": [
            "name",
            "employee_id",
            "checkInStatus",
        ],
        "report_columns": [
            "name",
            "employee_id",
            "date",
            "checkInTime",
            "checkOutTime",
            "checkInStatus",
        ],
    },
    {
        "module_name": "leave",
        "tool_name": "get_leave",
        "endpoint": "api/leave-applications",
        "method": "GET",
        "inject_org": True,
        "body_schema": {
            "page": 1,
            "pageSize": 10,
            "startDate": "YYYY-MM-DD",
            "endDate": "YYYY-MM-DD",
        },
        "local_filters": [
            "name",
            "employee_id",
            "leaveType",
            "status",
        ],
        "report_columns": [
            "name",
            "employee_id",
            "leaveType",
            "startDate",
            "endDate",
            "status",
        ],
    },
    {
        "module_name": "payroll",
        "tool_name": "get_payroll_batches",
        "endpoint": "api/payroll/batch",
        "method": "GET",
        "inject_org": False,
        "body_schema": {
            "page": 1,
            "limit": 10,
        },
        "local_filters": [
            "month",
            "year",
            "name",
            "status",
        ],
        "report_columns": [
            "batch_name",
            "month",
            "year",
            "total_employees",
            "total_amount",
            "status",
            "salary_sheet",
        ],
    },
    {
        "module_name": "payroll",
        "tool_name": "get_payroll_salary_sheet",
        "endpoint": "api/payroll/batch/{batch_id}/salary-sheet",
        "method": "GET",
        "inject_org": False,
        "body_schema": {
            "page": 1,
            "limit": 10,
        },
        "local_filters": [
            "name",
            "employee_id",
            "batch_id",
            "status",
            "month",
            "year",
            "department",
        ],
        "report_columns": [
            "employee_name",
            "employee_id",
            "department_name",
            "net_salary",
            "total_base_salary_structure_amount",
            "status",
            "payment_date",
        ],
    },
]


def seed_tools(db: Session) -> None:
    """Insert or UPDATE tools. Refreshes parameters if tools already exist."""
    logger.info(f"[tool_seed] Starting tool registry seed | total={len(HRX_TOOLS)} tools")
    inserted = 0
    updated = 0

    for tool_def in HRX_TOOLS:
        tool_name = tool_def["tool_name"]
        existing = db.query(ToolRegistry).filter_by(tool_name=tool_name).first()

        if existing:
            # Update existing tool with new schema (in case parameters changed)
            try:
                existing.endpoint = tool_def["endpoint"]
                existing.method = tool_def.get("method", "GET")
                existing.inject_org = tool_def.get("inject_org", True)
                existing.body_schema = json.dumps(tool_def.get("body_schema") or {})
                existing.local_filters = json.dumps(tool_def.get("local_filters") or [])
                existing.report_columns = json.dumps(tool_def.get("report_columns") or [])
                existing.active = True
                db.commit()
                logger.info(f"[tool_seed] Updated tool | tool_name='{tool_name}' endpoint='{tool_def['endpoint']}'")
                updated += 1
            except Exception as exc:
                db.rollback()
                logger.error(f"[tool_seed] Failed to update tool | tool_name='{tool_name}' | error={exc}")
            continue

        try:
            tool = ToolRegistry(
                module_name=tool_def["module_name"],
                tool_name=tool_name,
                endpoint=tool_def["endpoint"],
                method=tool_def.get("method", "GET"),
                inject_org=tool_def.get("inject_org", True),
                body_schema=json.dumps(tool_def.get("body_schema") or {}),
                local_filters=json.dumps(tool_def.get("local_filters") or []),
                report_columns=json.dumps(tool_def.get("report_columns") or []),
                active=True,
            )
            db.add(tool)
            db.commit()
            logger.info(f"[tool_seed] Registered tool | tool_name='{tool_name}' endpoint='{tool_def['endpoint']}'")
            inserted += 1
        except Exception as exc:
            db.rollback()
            logger.error(f"[tool_seed] Failed to register tool | tool_name='{tool_name}' | error={exc}")

    logger.info(f"[tool_seed] Seed complete | inserted={inserted} updated={updated}")
