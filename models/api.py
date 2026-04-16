"""API models (pydantic) for external/internal services."""
from pydantic import BaseModel


class AttendanceRecord(BaseModel):
    employeeName: str
    totalPresent: int
    totalAbsent: int
