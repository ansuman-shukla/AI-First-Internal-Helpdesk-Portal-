"""
Notification schemas for the helpdesk system

This module defines Pydantic schemas for notification-related operations
including creation, updates, and responses.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    """Enumeration of notification types"""
    TICKET_CREATED = "ticket_created"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_UPDATED = "ticket_updated"
    MESSAGE_RECEIVED = "message_received"
    MISUSE_DETECTED = "misuse_detected"
    SYSTEM_ALERT = "system_alert"


class NotificationCreateSchema(BaseModel):
    """Schema for creating new notifications"""
    
    user_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="ID of the user to receive the notification"
    )
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Notification title (1-200 characters)"
    )
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Notification message content (1-1000 characters)"
    )
    type: NotificationType = Field(
        ...,
        description="Type of notification"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional additional data as JSON object"
    )
    
    @field_validator('title', 'message')
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        """Validate and clean text fields"""
        if isinstance(v, str):
            return v.strip()
        return v
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )


class NotificationUpdateSchema(BaseModel):
    """Schema for updating notifications"""
    
    read: Optional[bool] = Field(
        default=None,
        description="Whether the notification has been read"
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )


class NotificationSchema(BaseModel):
    """Schema for notification responses"""
    
    id: Optional[str] = Field(None, description="MongoDB ObjectId as string")
    notification_id: str = Field(..., description="Unique notification identifier")
    user_id: str = Field(..., description="ID of the user who receives the notification")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message content")
    type: NotificationType = Field(..., description="Type of notification")
    read: bool = Field(default=False, description="Whether the notification has been read")
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional additional data as JSON object"
    )
    created_at: datetime = Field(..., description="When the notification was created")
    read_at: Optional[datetime] = Field(
        default=None,
        description="When the notification was marked as read"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list responses"""
    
    notifications: list[NotificationSchema] = Field(
        default_factory=list,
        description="List of notifications"
    )
    total: int = Field(
        default=0,
        description="Total number of notifications"
    )
    page: int = Field(
        default=1,
        description="Current page number"
    )
    limit: int = Field(
        default=20,
        description="Number of notifications per page"
    )
    has_next: bool = Field(
        default=False,
        description="Whether there are more notifications"
    )
    unread_count: int = Field(
        default=0,
        description="Number of unread notifications"
    )
    
    model_config = ConfigDict(from_attributes=True)


class NotificationCountResponse(BaseModel):
    """Schema for notification count responses"""
    
    unread_count: int = Field(
        default=0,
        description="Number of unread notifications"
    )
    total_count: int = Field(
        default=0,
        description="Total number of notifications"
    )
    
    model_config = ConfigDict(from_attributes=True)
