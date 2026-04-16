import uuid
from sqlalchemy import Column, String, Boolean, Text
from infrastructure.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ToolRegistry(Base):
    __tablename__ = "tool_registry"
    id = Column(String, primary_key=True, default=gen_uuid)
    module_name = Column(String, nullable=False)
    tool_name = Column(String, nullable=False, unique=True)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False, default="POST")
    inject_org = Column(Boolean, default=True)
    body_schema = Column(Text, nullable=True)
    local_filters = Column(Text, nullable=True)
    report_columns = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
