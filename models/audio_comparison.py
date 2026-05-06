import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, Integer
from sqlalchemy.sql import func
from infrastructure.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    """User registration table - stores user information for audio submission tracking."""
    __tablename__ = "user"
    
    id = Column(String, primary_key=True, default=gen_uuid)
    user_name = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AudioComparison(Base):
    __tablename__ = "audio_comparison"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, nullable=True, index=True)  # Unique user identifier (UUID or custom ID)
    user_name = Column(String, nullable=False, index=True)
    admin_name = Column(String, nullable=False, index=True)
    transcribed_text = Column(Text, nullable=False)
    admin_script = Column(Text, nullable=False)
    similarity_percentage = Column(Float, nullable=True)
    audio_file_name = Column(String, nullable=True)
    is_enabled = Column(Boolean, nullable=False, server_default="1", default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserAudioStats(Base):
    """Statistics table for user audio submissions - tracks aggregated data for fast retrieval."""
    __tablename__ = "user_audio_stats"
    
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, nullable=False, unique=True, index=True)
    user_name = Column(String, nullable=False)
    submission_count = Column(Integer, nullable=False, default=0)
    average_score = Column(Float, nullable=False, default=0.0)
    last_score = Column(Float, nullable=True)
    last_submission_time = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
