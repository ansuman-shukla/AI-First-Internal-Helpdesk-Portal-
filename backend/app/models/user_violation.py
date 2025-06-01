"""
User Violation Model

Tracks users who attempt to create tickets with inappropriate content.
This helps identify repeat offenders and potential misuse patterns.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum


class ViolationType(str, Enum):
    """Types of content violations"""
    PROFANITY = "profanity"
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"


class ViolationSeverity(str, Enum):
    """Severity levels for violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserViolationModel(BaseModel):
    """Model for user content violations"""
    
    id: Optional[str] = Field(None, alias="_id", description="MongoDB ObjectId as string")
    user_id: str = Field(..., description="ID of the user who attempted inappropriate content")
    violation_type: ViolationType = Field(..., description="Type of violation detected")
    severity: ViolationSeverity = Field(..., description="Severity of the violation")
    attempted_title: str = Field(..., description="Title of the attempted ticket")
    attempted_description: str = Field(..., description="Description of the attempted ticket")
    detection_reason: str = Field(..., description="Reason why content was flagged")
    detection_confidence: float = Field(..., description="AI confidence score (0.0-1.0)")
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="When violation was recorded")
    admin_reviewed: bool = Field(default=False, description="Whether admin has reviewed this violation")
    action_taken: Optional[str] = Field(None, description="Action taken by admin")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for MongoDB storage"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if self.id:
            data["_id"] = ObjectId(self.id)
        elif "_id" in data:
            del data["_id"]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserViolationModel":
        """Create model from MongoDB document"""
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        return cls(**data)


class UserViolationCreateSchema(BaseModel):
    """Schema for creating a new user violation record"""
    user_id: str = Field(..., description="ID of the user")
    violation_type: ViolationType = Field(..., description="Type of violation")
    severity: ViolationSeverity = Field(..., description="Severity level")
    attempted_title: str = Field(..., description="Attempted ticket title")
    attempted_description: str = Field(..., description="Attempted ticket description")
    detection_reason: str = Field(..., description="Reason for flagging")
    detection_confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")


class UserViolationResponseSchema(BaseModel):
    """Schema for user violation API responses"""
    id: str = Field(..., description="Violation ID")
    user_id: str = Field(..., description="User ID")
    violation_type: ViolationType = Field(..., description="Violation type")
    severity: ViolationSeverity = Field(..., description="Severity level")
    attempted_title: str = Field(..., description="Attempted title")
    attempted_description: str = Field(..., description="Attempted description")
    detection_reason: str = Field(..., description="Detection reason")
    detection_confidence: float = Field(..., description="AI confidence")
    created_at: datetime = Field(..., description="Creation timestamp")
    admin_reviewed: bool = Field(..., description="Admin review status")
    action_taken: Optional[str] = Field(None, description="Admin action")


class UserViolationSummarySchema(BaseModel):
    """Schema for user violation summary"""
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    total_violations: int = Field(..., description="Total violation count")
    violation_types: list[ViolationType] = Field(..., description="Types of violations")
    latest_violation: datetime = Field(..., description="Most recent violation")
    unreviewed_count: int = Field(..., description="Number of unreviewed violations")
    risk_level: str = Field(..., description="Risk assessment (low/medium/high/critical)")
