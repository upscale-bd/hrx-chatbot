import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean
from sqlalchemy.sql import func
from infrastructure.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class AudioComparison(Base):
    __tablename__ = "audio_comparison"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_name = Column(String, nullable=False, index=True)
    admin_name = Column(String, nullable=False, index=True)
    transcribed_text = Column(Text, nullable=False)
    admin_script = Column(Text, nullable=False)
    similarity_percentage = Column(Float, nullable=True)
    audio_file_name = Column(String, nullable=True)
    is_enabled = Column(Boolean, nullable=False, server_default="1", default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
