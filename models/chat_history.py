import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from infrastructure.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(String, primary_key=True, default=gen_uuid)
    organization_id = Column(String, nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
