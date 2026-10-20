from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import (
    ConversationDetailOut,
    ConversationOut,
    ConversationRenameRequest,
    FeedbackRequest,
    MessageOut,
    SendMessageRequest,
)
from app.services.chat_stream import stream_agent_turn

router = APIRouter(prefix="/api/chat", tags=["chat"])


async def _get_owned_conversation(db: AsyncSession, conversation_id: UUID, user: User) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conversation


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.organization_id == current_user.organization_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    conversation = Conversation(organization_id=current_user.organization_id, user_id=current_user.id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(db, conversation_id, current_user)
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    messages = list(result.scalars().all())
    return ConversationDetailOut(
        **ConversationOut.model_validate(conversation).model_dump(),
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: UUID,
    payload: ConversationRenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    conversation = await _get_owned_conversation(db, conversation_id, current_user)
    conversation.title = payload.title
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    conversation = await _get_owned_conversation(db, conversation_id, current_user)
    await db.delete(conversation)
    await db.commit()


@router.post("/conversations/{conversation_id}/messages")
@limiter.limit("20/minute")
async def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    conversation = await _get_owned_conversation(db, conversation_id, current_user)

    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    prior_messages = list(history_result.scalars().all())
    history = [{"role": m.role, "content": m.content} for m in prior_messages]

    user_message = Message(conversation_id=conversation_id, role="user", content=payload.content)
    db.add(user_message)

    if conversation.title == "New conversation" and not prior_messages:
        conversation.title = payload.content[:60]

    await db.commit()

    return StreamingResponse(
        stream_agent_turn(db, request, current_user.organization_id, conversation_id, payload.content, history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/conversations/{conversation_id}/regenerate")
@limiter.limit("20/minute")
async def regenerate_last_message(
    conversation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    # Called for its ownership check (404s if the conversation isn't the user's).
    await _get_owned_conversation(db, conversation_id, current_user)

    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    messages = list(result.scalars().all())
    if not messages or messages[-1].role != "assistant":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to regenerate yet.")

    last_user_message = next((m for m in reversed(messages) if m.role == "user"), None)
    if last_user_message is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to regenerate yet.")

    await db.execute(delete(Message).where(Message.id == messages[-1].id))
    await db.commit()

    history = [{"role": m.role, "content": m.content} for m in messages[:-1]]

    return StreamingResponse(
        stream_agent_turn(
            db, request, current_user.organization_id, conversation_id, last_user_message.content, history[:-1]
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.patch("/messages/{message_id}/feedback", response_model=MessageOut)
async def set_feedback(
    message_id: UUID,
    payload: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    message = await db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    conversation = await db.get(Conversation, message.conversation_id)
    if conversation is None or conversation.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    message.feedback = payload.feedback
    await db.commit()
    await db.refresh(message)
    return message
