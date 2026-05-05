from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from common.logger import get_logger
from config.config import settings


logger = get_logger("database")

Base = declarative_base()
engine = None
SessionLocal = None


def init_engine() -> None:
    """Initialize SQLAlchemy engine (idempotent)."""
    global engine, SessionLocal
    if engine is not None:
        logger.info("[database] Engine already initialized — skipping")
        return
    db_url = settings.APP_DATABASE_URL
    logger.info(f"[database] init_engine | connecting to: {db_url.split('@')[-1]}")
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("[database] Engine and SessionLocal created successfully")


def init_db() -> bool:
    """Create all tables (import models first to register metadata)."""
    logger.info("[database] init_db — starting table creation")
    try:
        init_engine()
        logger.info("[database] Importing model modules to register metadata")
        from models import tool_registry, chat_history, report_log, audio_comparison, admin_script  # noqa: F401
        logger.info("[database] Models registered: tool_registry, chat_history, report_log, audio_comparison, admin_script")
        logger.info("[database] Running create_all on metadata")
        Base.metadata.create_all(bind=engine)
        logger.info("[database] All tables created/verified successfully")
        return True
    except Exception as exc:
        logger.error(f"[database] init_db failed: {exc}")
        return False


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""
    logger.info("[database] get_db — opening new session")
    init_engine()
    db = SessionLocal()
    try:
        yield db
        logger.info("[database] Session yielded successfully")
    finally:
        logger.info("[database] Closing DB session")
        db.close()


def check_connection() -> bool:
    """Verify the database is reachable."""
    logger.info("[database] check_connection — verifying DB reachability")
    try:
        init_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[database] DB connection check passed")
        return True
    except Exception as exc:
        logger.error(f"[database] DB connection check failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Legacy async DatabaseManager kept for reference / future async migration
# ---------------------------------------------------------------------------




class DatabaseManager:
    """Sync database manager wrapping init_engine/init_db helpers."""

    def __init__(self):
        self.logger = get_logger("DatabaseManager")

    def create_tables(self) -> None:
        init_db()
        self.logger.info("Tables ready")

    def check_connection(self) -> bool:
        return check_connection()

    def get_session(self) -> Generator[Session, None, None]:
        return get_db()


db_manager = DatabaseManager()
