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


class AdminUser(Base):
    __tablename__ = "admin_user"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    auth_token = Column(String, nullable=True, index=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
