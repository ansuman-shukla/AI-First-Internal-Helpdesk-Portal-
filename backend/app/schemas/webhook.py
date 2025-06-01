"""
Webhook payload schemas for the helpdesk system

This module defines Pydantic schemas for webhook payloads
to avoid circular import issues.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TicketCreatedPayload(BaseModel):
    """Payload for ticket creation webhook"""
    ticket_id: str
    user_id: str
    title: str
    description: str
    urgency: str
    status: str
    department: Optional[str] = None
    misuse_flag: bool
    created_at: datetime


class MisuseDetectedPayload(BaseModel):
    """Payload for misuse detection webhook"""
    user_id: str
    ticket_id: str
    misuse_type: str
    confidence_score: Optional[float] = None
    detected_at: datetime


class MessageSentPayload(BaseModel):
    """Payload for message sent webhook"""
    message_id: str
    ticket_id: str
    sender_id: str
    sender_role: str
    message_type: str
    content: str
    isAI: bool
    feedback: str
    timestamp: datetime
