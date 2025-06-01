"""
Misuse Reports Service

This service handles saving and managing misuse detection results in the misuse_reports collection.
Provides functionality to create, retrieve, and manage misuse reports with proper deduplication.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bson import ObjectId
from app.core.database import get_database
from app.models.misuse_report import MisuseReportModel

logger = logging.getLogger(__name__)


class MisuseReportsService:
    """Service for managing misuse reports in MongoDB"""

    def __init__(self):
        self.db = None
        self.collection = None

    def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            self.db = get_database()
            self.collection = self.db["misuse_reports"]
    
    async def save_misuse_report(self, detection_result: Dict[str, Any]) -> Optional[str]:
        """
        Save a misuse detection result to the misuse_reports collection.
        Only saves if misuse was actually detected.

        Args:
            detection_result: Result from detect_misuse_for_user function

        Returns:
            str: Report ID if saved, None if no misuse detected or already exists
        """
        self._ensure_db_connection()
        try:
            # Only save if misuse was detected
            if not detection_result.get("misuse_detected", False):
                logger.debug(f"No misuse detected for user {detection_result.get('user_id')}, skipping report creation")
                return None
            
            user_id = detection_result.get("user_id")
            if not user_id:
                logger.error("Missing user_id in detection result")
                return None
            
            # Check for existing report today to avoid duplicates
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            existing_report = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "detection_date": {
                    "$gte": today_start,
                    "$lt": today_end
                }
            })
            
            if existing_report:
                logger.info(f"Misuse report already exists for user {user_id} today, skipping")
                return str(existing_report["_id"])
            
            # Create misuse report document
            report_doc = self._create_report_document(detection_result)
            
            # Insert into database
            result = await self.collection.insert_one(report_doc)
            report_id = str(result.inserted_id)
            
            logger.info(f"Created misuse report {report_id} for user {user_id}")
            return report_id
            
        except Exception as e:
            logger.error(f"Error saving misuse report: {str(e)}")
            return None
    
    def _create_report_document(self, detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a misuse report document from detection result.
        
        Args:
            detection_result: Result from detect_misuse_for_user function
            
        Returns:
            Dict containing the report document
        """
        user_id = detection_result.get("user_id")
        patterns = detection_result.get("patterns", [])
        metadata = detection_result.get("analysis_metadata", {})
        
        # Determine misuse type and severity from patterns
        misuse_type = self._determine_misuse_type(patterns)
        severity_level = self._determine_severity_level(patterns, detection_result.get("confidence_score", 0.5))
        
        # Extract evidence data
        evidence_data = {
            "ticket_ids": [ObjectId(tid) for tid in metadata.get("tickets_analyzed", []) if tid],
            "content_samples": metadata.get("content_samples", []),
            "pattern_analysis": f"Detected patterns: {', '.join(patterns)}"
        }
        
        # Create AI analysis metadata
        ai_analysis_metadata = {
            "detection_confidence": detection_result.get("confidence_score", 0.5),
            "model_reasoning": metadata.get("reasoning", "Pattern-based analysis"),
            "analysis_timestamp": detection_result.get("analysis_date", datetime.utcnow())
        }
        
        return {
            "user_id": ObjectId(user_id),
            "detection_date": datetime.utcnow(),
            "misuse_type": misuse_type,
            "severity_level": severity_level,
            "evidence_data": evidence_data,
            "admin_reviewed": False,
            "action_taken": None,
            "ai_analysis_metadata": ai_analysis_metadata
        }
    
    def _determine_misuse_type(self, patterns: List[str]) -> str:
        """
        Determine the primary misuse type from detected patterns.
        
        Args:
            patterns: List of detected pattern names
            
        Returns:
            str: Primary misuse type
        """
        # Priority order for misuse types
        if "abusive_language" in patterns:
            return "abusive_language"
        elif "jailbreak_attempt" in patterns:
            return "jailbreak_attempt"
        elif "duplicate_titles" in patterns:
            return "duplicate_tickets"
        elif "high_volume" in patterns or "short_descriptions" in patterns:
            return "spam_content"
        else:
            return "spam_content"  # Default fallback
    
    def _determine_severity_level(self, patterns: List[str], confidence: float) -> str:
        """
        Determine severity level based on patterns and confidence.
        
        Args:
            patterns: List of detected pattern names
            confidence: Detection confidence score
            
        Returns:
            str: Severity level (low, medium, high)
        """
        # High severity patterns
        high_severity_patterns = ["abusive_language", "jailbreak_attempt"]
        
        # Medium severity patterns
        medium_severity_patterns = ["high_volume", "duplicate_titles"]
        
        if any(pattern in patterns for pattern in high_severity_patterns):
            return "high"
        elif any(pattern in patterns for pattern in medium_severity_patterns) and confidence > 0.7:
            return "medium"
        else:
            return "low"
    
    async def get_reports_by_user(self, user_id: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get misuse reports for a specific user.

        Args:
            user_id: User ID to get reports for
            days_back: Number of days to look back

        Returns:
            List of misuse report documents
        """
        self._ensure_db_connection()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            cursor = self.collection.find({
                "user_id": ObjectId(user_id),
                "detection_date": {"$gte": cutoff_date}
            }).sort("detection_date", -1)
            
            reports = await cursor.to_list(length=None)
            
            # Convert ObjectIds to strings for JSON serialization
            for report in reports:
                report["_id"] = str(report["_id"])
                report["user_id"] = str(report["user_id"])
                if "evidence_data" in report and "ticket_ids" in report["evidence_data"]:
                    report["evidence_data"]["ticket_ids"] = [
                        str(tid) for tid in report["evidence_data"]["ticket_ids"]
                    ]
            
            return reports
            
        except Exception as e:
            logger.error(f"Error getting reports for user {user_id}: {str(e)}")
            return []
    
    async def get_all_unreviewed_reports(self) -> List[Dict[str, Any]]:
        """
        Get all unreviewed misuse reports for admin dashboard.

        Returns:
            List of unreviewed misuse report documents
        """
        self._ensure_db_connection()
        try:
            cursor = self.collection.find({
                "admin_reviewed": False
            }).sort("detection_date", -1)
            
            reports = await cursor.to_list(length=None)
            
            # Convert ObjectIds to strings for JSON serialization
            for report in reports:
                report["_id"] = str(report["_id"])
                report["user_id"] = str(report["user_id"])
                if "evidence_data" in report and "ticket_ids" in report["evidence_data"]:
                    report["evidence_data"]["ticket_ids"] = [
                        str(tid) for tid in report["evidence_data"]["ticket_ids"]
                    ]
            
            return reports
            
        except Exception as e:
            logger.error(f"Error getting unreviewed reports: {str(e)}")
            return []

    async def get_all_reports(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """
        Get all misuse reports (both reviewed and unreviewed) with pagination.

        Args:
            page: Page number (1-based)
            limit: Number of reports per page

        Returns:
            Dict containing paginated reports and metadata
        """
        self._ensure_db_connection()
        try:
            # Calculate skip value for pagination
            skip = (page - 1) * limit

            # Get total count
            total_count = await self.collection.count_documents({})

            # Get unreviewed count
            unreviewed_count = await self.collection.count_documents({"admin_reviewed": False})

            # Get paginated reports sorted by detection date (newest first)
            cursor = self.collection.find({}).sort("detection_date", -1).skip(skip).limit(limit)
            reports = await cursor.to_list(length=limit)

            # Convert ObjectIds to strings for JSON serialization
            for report in reports:
                report["_id"] = str(report["_id"])
                report["user_id"] = str(report["user_id"])
                if "evidence_data" in report and "ticket_ids" in report["evidence_data"]:
                    report["evidence_data"]["ticket_ids"] = [
                        str(tid) for tid in report["evidence_data"]["ticket_ids"]
                    ]

            logger.info(f"Retrieved {len(reports)} misuse reports (page {page}, total: {total_count})")
            return {
                "reports": reports,
                "total_count": total_count,
                "unreviewed_count": unreviewed_count,
                "page": page,
                "limit": limit,
                "total_pages": (total_count + limit - 1) // limit
            }

        except Exception as e:
            logger.error(f"Error getting all misuse reports: {str(e)}")
            return {
                "reports": [],
                "total_count": 0,
                "unreviewed_count": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0
            }

    async def mark_report_reviewed(self, report_id: str, action_taken: Optional[str] = None) -> bool:
        """
        Mark a misuse report as reviewed by admin.

        Args:
            report_id: ID of the report to mark as reviewed
            action_taken: Optional description of action taken

        Returns:
            bool: True if successfully updated
        """
        self._ensure_db_connection()
        try:
            update_data = {
                "admin_reviewed": True,
                "reviewed_at": datetime.utcnow()
            }
            
            if action_taken:
                update_data["action_taken"] = action_taken
            
            result = await self.collection.update_one(
                {"_id": ObjectId(report_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Marked misuse report {report_id} as reviewed")
                return True
            else:
                logger.warning(f"No report found with ID {report_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error marking report {report_id} as reviewed: {str(e)}")
            return False


# Global service instance
misuse_reports_service = MisuseReportsService()
