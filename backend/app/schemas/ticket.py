from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class TicketUrgency(str, Enum):
    """Ticket urgency levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TicketStatus(str, Enum):
    """Ticket status values"""

    OPEN = "open"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketDepartment(str, Enum):
    """Department types"""

    IT = "IT"
    HR = "HR"


class TicketCreateSchema(BaseModel):
    """Schema for creating a new ticket"""

    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    description: str = Field(
        ..., min_length=1, max_length=2000, description="Ticket description"
    )
    urgency: TicketUrgency = Field(
        default=TicketUrgency.MEDIUM, description="Ticket urgency level"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError("Description cannot be empty or whitespace only")
        return v.strip()


class TicketUpdateSchema(BaseModel):
    """Schema for updating an existing ticket"""

    title: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Updated ticket title"
    )
    description: Optional[str] = Field(
        None, min_length=1, max_length=2000, description="Updated ticket description"
    )
    urgency: Optional[TicketUrgency] = Field(None, description="Updated urgency level")
    status: Optional[TicketStatus] = Field(None, description="Updated ticket status")
    department: Optional[TicketDepartment] = Field(
        None, description="Updated department"
    )
    assignee_id: Optional[str] = Field(None, description="Updated assignee ID")
    feedback: Optional[str] = Field(None, description="Post-resolution feedback")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip() if v else v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Description cannot be empty or whitespace only")
        return v.strip() if v else v


class TicketUserInfo(BaseModel):
    """User information for ticket responses"""
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")


class TicketSchema(BaseModel):
    """Schema for ticket responses"""

    id: Optional[str] = Field(None, description="MongoDB ObjectId as string")
    ticket_id: str = Field(..., description="Auto-generated ticket ID")
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Ticket description")
    urgency: TicketUrgency = Field(..., description="Ticket urgency level")
    status: TicketStatus = Field(..., description="Current ticket status")
    department: Optional[TicketDepartment] = Field(
        None, description="Assigned department"
    )
    assignee_id: Optional[str] = Field(None, description="Assigned agent ID")
    user_id: str = Field(..., description="Ticket creator ID")
    user_info: Optional[TicketUserInfo] = Field(None, description="User information for agents/admins")
    created_at: datetime = Field(..., description="Ticket creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    closed_at: Optional[datetime] = Field(None, description="Ticket closure timestamp")
    misuse_flag: bool = Field(default=False, description="Misuse detection flag")
    feedback: Optional[str] = Field(None, description="Post-resolution feedback")

    model_config = ConfigDict(from_attributes=True)
