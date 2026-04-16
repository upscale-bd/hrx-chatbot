from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.chatbot.dto.chat_dto import ChatRequest, ChatResponse, ChatHistoryResponse, ChatHistoryItem
from app.chatbot.usecase.chat_usecase import ChatUsecase
from app.chatbot.repository.chat_repository import get_chat_history
from infrastructure.database import get_db
from common.logger import get_logger


logger = get_logger("chat_handler")
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message/{organization_id}", response_model=ChatResponse)
def send_message(organization_id: str, req: ChatRequest, db: Session = Depends(get_db)):
    logger.info(f"[chat_handler] POST /chat/message/{organization_id} received")
    logger.info(f"[chat_handler] User message: '{req.message}'")
    usecase = ChatUsecase(db)
    logger.info("[chat_handler] ChatUsecase initialized, delegating to handle_message")
    # Pass organizationId directly to usecase
    response = usecase.handle_message(req, organization_id)
    answer = response.data.answer if response.data else None
    report_link = response.data.report.downloadUrl if response.data and response.data.report else None
    logger.info(
        f"[chat_handler] Response ready | answer='{answer}' | report_link={report_link}"
    )
    return response


@router.get("/history/{organization_id}", response_model=ChatHistoryResponse)
def get_history(organization_id: str, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve chat history for an organization.
    
    - **organization_id**: Organization ID to retrieve history for
    - **limit**: Maximum number of messages to return (default: 100)
    """
    logger.info(f"[chat_handler] GET /chat/history/{organization_id} | limit={limit}")
    try:
        chats = get_chat_history(db, organization_id, limit=limit)
        
        # Convert to response DTOs
        messages = [
            ChatHistoryItem(
                chatId=chat.id,
                userMessage=chat.user_message,
                botResponse=chat.bot_response,
                createdAt=chat.created_at
            )
            for chat in chats
        ]
        
        logger.info(f"[chat_handler] History retrieved successfully | count={len(messages)}")
        return ChatHistoryResponse(
            organizationId=organization_id,
            totalCount=len(messages),
            messages=messages
        )
    except Exception as exc:
        logger.error(f"[chat_handler] get_history failed | org={organization_id} | error={exc}")
        return ChatHistoryResponse(
            success=False,
            organizationId=organization_id,
            totalCount=0,
            messages=[]
        )