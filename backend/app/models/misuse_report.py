"""
Misuse Report Model

Defines the data model for misuse detection reports stored in MongoDB.
Based on the PRD schema for misuse_reports collection.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum


class MisuseType(str, Enum):
    """Enumeration of misuse types"""
    DUPLICATE_TICKETS = "duplicate_tickets"
    SPAM_CONTENT = "spam_content"
    ABUSIVE_LANGUAGE = "abusive_language"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"


class SeverityLevel(str, Enum):
    """Enumeration of severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceData(BaseModel):
    """Evidence data for misuse detection"""
    ticket_ids: List[str] = Field(default_factory=list, description="List of ticket IDs involved")
    content_samples: List[str] = Field(default_factory=list, description="Sample content that triggered detection")
    pattern_analysis: str = Field(..., description="Analysis of detected patterns")


class AIAnalysisMetadata(BaseModel):
    """AI analysis metadata for misuse detection"""
    detection_confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    model_reasoning: str = Field(..., description="AI model reasoning for detection")
    analysis_timestamp: datetime = Field(..., description="When the analysis was performed")


class MisuseReportModel(BaseModel):
    """
    Misuse Report Model
    
    Represents a misuse detection report in the database.
    Based on the PRD schema for misuse_reports collection.
    """
    
    id: Optional[str] = Field(None, alias="_id", description="MongoDB ObjectId as string")
    user_id: str = Field(..., description="ID of the user flagged for misuse")
    detection_date: datetime = Field(..., description="When the misuse was detected")
    misuse_type: MisuseType = Field(..., description="Type of misuse detected")
    severity_level: SeverityLevel = Field(..., description="Severity level of the misuse")
    evidence_data: EvidenceData = Field(..., description="Evidence supporting the detection")
    admin_reviewed: bool = Field(default=False, description="Whether an admin has reviewed this report")
    action_taken: Optional[str] = Field(None, description="Action taken by admin (if any)")
    ai_analysis_metadata: AIAnalysisMetadata = Field(..., description="AI analysis metadata")
    reviewed_at: Optional[datetime] = Field(None, description="When the report was reviewed by admin")
    
    class Config:
        """Pydantic configuration"""
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        
    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "MisuseReportModel":
        """
        Create a MisuseReportModel from MongoDB document
        
        Args:
            data: MongoDB document dictionary
            
        Returns:
            MisuseReportModel instance
        """
        if "_id" in data:
            data["_id"] = str(data["_id"])
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        
        # Convert ticket_ids in evidence_data to strings
        if "evidence_data" in data and "ticket_ids" in data["evidence_data"]:
            data["evidence_data"]["ticket_ids"] = [
                str(tid) for tid in data["evidence_data"]["ticket_ids"]
            ]
        
        return cls(**data)
    
    def to_mongo(self) -> Dict[str, Any]:
        """
        Convert to MongoDB document format
        
        Returns:
            Dictionary suitable for MongoDB storage
        """
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Convert string IDs back to ObjectIds for MongoDB
        if "_id" in data and data["_id"]:
            data["_id"] = ObjectId(data["_id"])
        if "user_id" in data:
            data["user_id"] = ObjectId(data["user_id"])
        
        # Convert ticket_ids in evidence_data to ObjectIds
        if "evidence_data" in data and "ticket_ids" in data["evidence_data"]:
            data["evidence_data"]["ticket_ids"] = [
                ObjectId(tid) for tid in data["evidence_data"]["ticket_ids"] if tid
            ]
        
        return data


class MisuseReportCreateSchema(BaseModel):
    """Schema for creating a new misuse report"""
    user_id: str = Field(..., description="ID of the user flagged for misuse")
    misuse_type: MisuseType = Field(..., description="Type of misuse detected")
    severity_level: SeverityLevel = Field(..., description="Severity level of the misuse")
    evidence_data: EvidenceData = Field(..., description="Evidence supporting the detection")
    ai_analysis_metadata: AIAnalysisMetadata = Field(..., description="AI analysis metadata")


class MisuseReportResponseSchema(BaseModel):
    """Schema for misuse report API responses"""
    id: str = Field(..., description="Report ID")
    user_id: str = Field(..., description="ID of the user flagged for misuse")
    detection_date: datetime = Field(..., description="When the misuse was detected")
    misuse_type: MisuseType = Field(..., description="Type of misuse detected")
    severity_level: SeverityLevel = Field(..., description="Severity level of the misuse")
    evidence_data: EvidenceData = Field(..., description="Evidence supporting the detection")
    admin_reviewed: bool = Field(..., description="Whether an admin has reviewed this report")
    action_taken: Optional[str] = Field(None, description="Action taken by admin (if any)")
    ai_analysis_metadata: AIAnalysisMetadata = Field(..., description="AI analysis metadata")
    reviewed_at: Optional[datetime] = Field(None, description="When the report was reviewed by admin")


class MisuseReportUpdateSchema(BaseModel):
    """Schema for updating a misuse report (admin actions)"""
    admin_reviewed: Optional[bool] = Field(None, description="Mark as reviewed")
    action_taken: Optional[str] = Field(None, description="Action taken by admin")


class MisuseReportListResponseSchema(BaseModel):
    """Schema for paginated misuse report list responses"""
    reports: List[MisuseReportResponseSchema] = Field(..., description="List of misuse reports")
    total_count: int = Field(..., description="Total number of reports")
    unreviewed_count: int = Field(..., description="Number of unreviewed reports")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of reports per page")
