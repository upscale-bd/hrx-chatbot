import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from infrastructure.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class AdminScript(Base):
    __tablename__ = "admin_script"
    id = Column(String, primary_key=True, default=gen_uuid)
    admin_name = Column(String, nullable=False, index=True)
    script = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
