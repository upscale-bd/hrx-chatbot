import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from infrastructure.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ReportLog(Base):
    __tablename__ = "report_log"
    id = Column(String, primary_key=True, default=gen_uuid)
    organization_id = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    report_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
