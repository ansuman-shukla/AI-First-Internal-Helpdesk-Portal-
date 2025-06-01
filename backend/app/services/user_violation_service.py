"""
User Violation Service

Service for tracking and managing users who attempt to create tickets
with inappropriate content. Helps identify repeat offenders and patterns.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.core.database import get_database
from app.models.user_violation import (
    UserViolationModel,
    UserViolationCreateSchema,
    ViolationType,
    ViolationSeverity
)
from app.services.user_service import user_service
import logging

logger = logging.getLogger(__name__)


class UserViolationService:
    """Service for managing user content violations"""
    
    def __init__(self):
        self.collection_name = "user_violations"
    
    async def record_violation(
        self,
        user_id: str,
        violation_data: UserViolationCreateSchema
    ) -> str:
        """
        Record a new user violation for inappropriate content attempt.
        
        Args:
            user_id: ID of the user who attempted inappropriate content
            violation_data: Details of the violation
            
        Returns:
            str: ID of the created violation record
        """
        try:
            logger.info(f"Recording violation for user {user_id}: {violation_data.violation_type}")
            
            db = get_database()
            if db is None:
                raise Exception("Database connection not available")
            
            collection = db[self.collection_name]
            
            # Create violation model
            violation = UserViolationModel(
                user_id=user_id,
                violation_type=violation_data.violation_type,
                severity=violation_data.severity,
                attempted_title=violation_data.attempted_title,
                attempted_description=violation_data.attempted_description,
                detection_reason=violation_data.detection_reason,
                detection_confidence=violation_data.detection_confidence,
                created_at=datetime.utcnow(),
                admin_reviewed=False
            )
            
            # Insert into database
            violation_dict = violation.to_dict()
            result = await collection.insert_one(violation_dict)
            violation_id = str(result.inserted_id)
            
            logger.info(f"Violation recorded with ID: {violation_id}")
            
            # Check if user should be escalated
            await self._check_escalation(user_id)
            
            return violation_id
            
        except Exception as e:
            logger.error(f"Error recording violation for user {user_id}: {str(e)}")
            raise
    
    async def get_user_violations(
        self,
        user_id: str,
        days: Optional[int] = None
    ) -> List[UserViolationModel]:
        """
        Get all violations for a specific user.
        
        Args:
            user_id: User ID to get violations for
            days: Optional number of days to look back
            
        Returns:
            List of user violations
        """
        try:
            db = get_database()
            if db is None:
                return []
            
            collection = db[self.collection_name]
            
            # Build query
            query = {"user_id": ObjectId(user_id)}
            
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query["created_at"] = {"$gte": cutoff_date}
            
            # Get violations
            cursor = collection.find(query).sort("created_at", -1)
            violations = []
            
            async for doc in cursor:
                violations.append(UserViolationModel.from_dict(doc))
            
            logger.debug(f"Found {len(violations)} violations for user {user_id}")
            return violations
            
        except Exception as e:
            logger.error(f"Error getting violations for user {user_id}: {str(e)}")
            return []
    
    async def get_flagged_users_summary(
        self,
        days: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get summary of users with violations.
        
        Args:
            days: Optional number of days to look back
            limit: Maximum number of users to return
            
        Returns:
            List of user violation summaries
        """
        try:
            db = get_database()
            if db is None:
                return []
            
            collection = db[self.collection_name]
            
            # Build date filter
            date_filter = {}
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                date_filter = {"created_at": {"$gte": cutoff_date}}
            
            # Aggregation pipeline
            pipeline = [
                {"$match": date_filter},
                {
                    "$group": {
                        "_id": "$user_id",
                        "total_violations": {"$sum": 1},
                        "violation_types": {"$addToSet": "$violation_type"},
                        "latest_violation": {"$max": "$created_at"},
                        "unreviewed_count": {
                            "$sum": {"$cond": [{"$eq": ["$admin_reviewed", False]}, 1, 0]}
                        },
                        "high_severity_count": {
                            "$sum": {"$cond": [{"$in": ["$severity", ["high", "critical"]]}, 1, 0]}
                        }
                    }
                },
                {"$sort": {"total_violations": -1}},
                {"$limit": limit}
            ]
            
            results = await collection.aggregate(pipeline).to_list(limit)
            
            # Enrich with user information
            summaries = []
            for result in results:
                user_id = str(result["_id"])
                user = await user_service.get_user_by_id(user_id)
                
                # Calculate risk level
                risk_level = self._calculate_risk_level(
                    result["total_violations"],
                    result["high_severity_count"],
                    result["unreviewed_count"]
                )
                
                summary = {
                    "user_id": user_id,
                    "username": user.username if user else "Unknown",
                    "total_violations": result["total_violations"],
                    "violation_types": result["violation_types"],
                    "latest_violation": result["latest_violation"],
                    "unreviewed_count": result["unreviewed_count"],
                    "risk_level": risk_level
                }
                summaries.append(summary)
            
            logger.info(f"Generated summary for {len(summaries)} flagged users")
            return summaries
            
        except Exception as e:
            logger.error(f"Error getting flagged users summary: {str(e)}")
            return []
    
    async def mark_violation_reviewed(
        self,
        violation_id: str,
        admin_action: str
    ) -> bool:
        """
        Mark a violation as reviewed by admin.
        
        Args:
            violation_id: ID of the violation to mark as reviewed
            admin_action: Action taken by admin
            
        Returns:
            bool: True if successfully updated
        """
        try:
            db = get_database()
            if db is None:
                return False
            
            collection = db[self.collection_name]
            
            result = await collection.update_one(
                {"_id": ObjectId(violation_id)},
                {
                    "$set": {
                        "admin_reviewed": True,
                        "action_taken": admin_action,
                        "reviewed_at": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Violation {violation_id} marked as reviewed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error marking violation {violation_id} as reviewed: {str(e)}")
            return False
    
    def _calculate_risk_level(
        self,
        total_violations: int,
        high_severity_count: int,
        unreviewed_count: int
    ) -> str:
        """Calculate risk level based on violation patterns"""
        
        # Critical: 5+ violations or 2+ high severity
        if total_violations >= 5 or high_severity_count >= 2:
            return "critical"
        
        # High: 3+ violations or 1+ high severity with unreviewed
        if total_violations >= 3 or (high_severity_count >= 1 and unreviewed_count > 0):
            return "high"
        
        # Medium: 2+ violations or any unreviewed
        if total_violations >= 2 or unreviewed_count > 0:
            return "medium"
        
        # Low: 1 violation
        return "low"
    
    async def _check_escalation(self, user_id: str) -> None:
        """Check if user should be escalated based on violation history"""
        try:
            # Get recent violations (last 7 days)
            recent_violations = await self.get_user_violations(user_id, days=7)
            
            if len(recent_violations) >= 3:
                logger.warning(f"User {user_id} has {len(recent_violations)} violations in 7 days - escalation needed")
                # TODO: Implement escalation logic (notifications, user suspension, etc.)
            
        except Exception as e:
            logger.error(f"Error checking escalation for user {user_id}: {str(e)}")


# Global service instance
user_violation_service = UserViolationService()
