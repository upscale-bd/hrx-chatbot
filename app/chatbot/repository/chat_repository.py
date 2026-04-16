from typing import Optional, List
from sqlalchemy.orm import Session
from models.chat_history import ChatHistory
from common.logger import get_logger

logger = get_logger("chat_repository")


def create_chat_entry(db: Session, organization_id: str, user_message: str) -> ChatHistory:
    """Persist a new chat entry (bot_response filled in later)."""
    logger.info(f"[chat_repository] create_chat_entry | org={organization_id}")
    logger.info(f"[chat_repository] user_message='{user_message[:120]}'")
    try:
        chat = ChatHistory(
            organization_id=organization_id,
            user_message=user_message,
            bot_response=None,
        )
        logger.info("[chat_repository] Adding chat entry to session")
        db.add(chat)
        db.commit()
        db.refresh(chat)
        logger.info(f"[chat_repository] Chat entry persisted | id={chat.id}")
        return chat
    except Exception as exc:
        logger.error(f"[chat_repository] create_chat_entry failed | org={organization_id} | error={exc}")
        db.rollback()
        raise


def update_chat_response(db: Session, chat_id: str, bot_response: str) -> Optional[ChatHistory]:
    """Set the bot_response on an existing chat entry."""
    logger.info(f"[chat_repository] update_chat_response | chat_id={chat_id}")
    try:
        chat = db.query(ChatHistory).filter(ChatHistory.id == chat_id).first()
        if not chat:
            logger.warning(f"[chat_repository] Chat entry not found | id={chat_id}")
            return None
        logger.info("[chat_repository] Found chat entry, setting bot_response")
        chat.bot_response = bot_response
        db.add(chat)
        db.commit()
        db.refresh(chat)
        logger.info(f"[chat_repository] bot_response updated successfully | id={chat.id}")
        return chat
    except Exception as exc:
        logger.error(f"[chat_repository] update_chat_response failed | chat_id={chat_id} | error={exc}")
        db.rollback()
        raise


def get_chat_history(db: Session, organization_id: str, limit: int = 100) -> List[ChatHistory]:
    """Retrieve chat history for an organization (sorted by newest first)."""
    logger.info(f"[chat_repository] get_chat_history | org={organization_id} | limit={limit}")
    try:
        chats = (
            db.query(ChatHistory)
            .filter(ChatHistory.organization_id == organization_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        logger.info(f"[chat_repository] Retrieved {len(chats)} messages | org={organization_id}")
        return chats
    except Exception as exc:
        logger.error(f"[chat_repository] get_chat_history failed | org={organization_id} | error={exc}")
        raise
