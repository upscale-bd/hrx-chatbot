from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class ToolCreate(BaseModel):
    module_name: str
    tool_name: str
    endpoint: str
    method: str = "POST"
    inject_org: bool = True
    body_schema: Optional[Dict[str, Any]] = None
    report_columns: Optional[List[str]] = None
