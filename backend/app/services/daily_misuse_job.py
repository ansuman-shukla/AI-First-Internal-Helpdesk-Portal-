"""
Daily Misuse Detection Job Service

This service handles the scheduled daily misuse detection job that runs for all users.
Processes users in batches, detects misuse patterns, saves reports, and notifies admins.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.core.database import get_database
from app.services.ai.misuse_detector import detect_misuse_for_user
from app.services.misuse_reports_service import misuse_reports_service
from app.services.webhook_service import webhook_service

logger = logging.getLogger(__name__)


class DailyMisuseJobService:
    """Service for running daily misuse detection jobs"""

    def __init__(self, batch_size: int = 15):
        """
        Initialize the daily misuse job service

        Args:
            batch_size: Number of users to process in each batch
        """
        self.batch_size = batch_size
        self.db = None

    def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            self.db = get_database()
        
    async def run_daily_misuse_detection(self, window_hours: int = 24) -> Dict[str, Any]:
        """
        Run misuse detection for all active users in the system.
        
        Args:
            window_hours: Time window for analysis (default: 24 hours)
            
        Returns:
            Dict containing job execution summary
        """
        job_start_time = datetime.utcnow()
        logger.info(f"Starting daily misuse detection job at {job_start_time}")
        
        try:
            # Get all active users
            users = await self._get_active_users()
            total_users = len(users)
            
            if total_users == 0:
                logger.info("No active users found, skipping misuse detection")
                return self._create_job_summary(job_start_time, 0, 0, 0, 0, "No active users")
            
            logger.info(f"Processing {total_users} users in batches of {self.batch_size}")
            
            # Process users in batches
            processed_count = 0
            misuse_detected_count = 0
            reports_created_count = 0
            error_count = 0
            
            for i in range(0, total_users, self.batch_size):
                batch = users[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (total_users + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} users)")
                
                batch_results = await self._process_user_batch(batch, window_hours)
                
                processed_count += batch_results["processed"]
                misuse_detected_count += batch_results["misuse_detected"]
                reports_created_count += batch_results["reports_created"]
                error_count += batch_results["errors"]
                
                # Small delay between batches to avoid overwhelming the system
                if i + self.batch_size < total_users:
                    await asyncio.sleep(1)
            
            job_end_time = datetime.utcnow()
            job_duration = (job_end_time - job_start_time).total_seconds()
            
            logger.info(
                f"Daily misuse detection job completed in {job_duration:.2f}s - "
                f"Processed: {processed_count}, Misuse detected: {misuse_detected_count}, "
                f"Reports created: {reports_created_count}, Errors: {error_count}"
            )
            
            return self._create_job_summary(
                job_start_time, processed_count, misuse_detected_count, 
                reports_created_count, error_count, "Completed successfully"
            )
            
        except Exception as e:
            logger.error(f"Fatal error in daily misuse detection job: {str(e)}")
            return self._create_job_summary(
                job_start_time, 0, 0, 0, 1, f"Fatal error: {str(e)}"
            )
    
    async def _get_active_users(self) -> List[Dict[str, Any]]:
        """
        Get all active users from the database.

        Returns:
            List of user documents with _id and username
        """
        self._ensure_db_connection()
        try:
            users_collection = self.db["users"]
            
            # Get all active users (excluding admins for now)
            cursor = users_collection.find(
                {
                    "is_active": True,
                    "role": {"$in": ["user", "it_agent", "hr_agent"]}
                },
                {"_id": 1, "username": 1, "role": 1}
            )
            
            users = await cursor.to_list(length=None)
            
            # Convert ObjectIds to strings
            for user in users:
                user["_id"] = str(user["_id"])
            
            logger.debug(f"Found {len(users)} active users")
            return users
            
        except Exception as e:
            logger.error(f"Error getting active users: {str(e)}")
            return []
    
    async def _process_user_batch(self, users: List[Dict[str, Any]], window_hours: int) -> Dict[str, int]:
        """
        Process a batch of users for misuse detection.
        
        Args:
            users: List of user documents
            window_hours: Time window for analysis
            
        Returns:
            Dict with batch processing statistics
        """
        processed = 0
        misuse_detected = 0
        reports_created = 0
        errors = 0
        
        # Process users concurrently within the batch
        tasks = []
        for user in users:
            task = self._process_single_user(user["_id"], user.get("username", "unknown"), window_hours)
            tasks.append(task)
        
        # Wait for all tasks in the batch to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            processed += 1
            
            if isinstance(result, Exception):
                logger.error(f"Error processing user {users[i]['_id']}: {str(result)}")
                errors += 1
            elif result:
                if result.get("misuse_detected"):
                    misuse_detected += 1
                if result.get("report_created"):
                    reports_created += 1
        
        return {
            "processed": processed,
            "misuse_detected": misuse_detected,
            "reports_created": reports_created,
            "errors": errors
        }
    
    async def _process_single_user(self, user_id: str, username: str, window_hours: int) -> Optional[Dict[str, Any]]:
        """
        Process misuse detection for a single user.
        
        Args:
            user_id: User ID to process
            username: Username for logging
            window_hours: Time window for analysis
            
        Returns:
            Dict with processing result or None if error
        """
        try:
            logger.debug(f"Processing misuse detection for user {username} ({user_id})")
            
            # Run misuse detection
            detection_result = await detect_misuse_for_user(user_id, window_hours)
            
            if not detection_result:
                logger.warning(f"No detection result for user {user_id}")
                return {"misuse_detected": False, "report_created": False}
            
            misuse_detected = detection_result.get("misuse_detected", False)
            
            if misuse_detected:
                logger.info(f"Misuse detected for user {username} ({user_id})")
                
                # Save misuse report
                report_id = await misuse_reports_service.save_misuse_report(detection_result)
                
                if report_id:
                    logger.info(f"Created misuse report {report_id} for user {user_id}")
                    
                    # Fire webhook notification for admin
                    await self._notify_admin_of_misuse(user_id, username, report_id, detection_result)
                    
                    return {"misuse_detected": True, "report_created": True, "report_id": report_id}
                else:
                    logger.warning(f"Failed to create misuse report for user {user_id}")
                    return {"misuse_detected": True, "report_created": False}
            else:
                logger.debug(f"No misuse detected for user {username} ({user_id})")
                return {"misuse_detected": False, "report_created": False}
                
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {str(e)}")
            raise e
    
    async def _notify_admin_of_misuse(self, user_id: str, username: str, report_id: str, detection_result: Dict[str, Any]):
        """
        Notify admins of detected misuse via webhook.
        
        Args:
            user_id: User ID with detected misuse
            username: Username for notification
            report_id: Created report ID
            detection_result: Misuse detection result
        """
        try:
            # Create webhook payload for misuse detection
            webhook_payload = {
                "event_type": "misuse_detected",
                "user_id": user_id,
                "username": username,
                "report_id": report_id,
                "detection_date": detection_result.get("analysis_date", datetime.utcnow()).isoformat(),
                "patterns": detection_result.get("patterns", []),
                "confidence_score": detection_result.get("confidence_score", 0.0),
                "ticket_count": detection_result.get("ticket_count", 0)
            }
            
            # Fire webhook (this would be implemented in webhook_service)
            # For now, just log the notification
            logger.info(f"Admin notification: Misuse detected for user {username} - Report: {report_id}")
            logger.debug(f"Webhook payload: {webhook_payload}")
            
            # TODO: Implement actual webhook firing when webhook endpoint is available
            # await webhook_service.fire_misuse_detected_webhook(webhook_payload)
            
        except Exception as e:
            logger.error(f"Error notifying admin of misuse for user {user_id}: {str(e)}")
    
    def _create_job_summary(self, start_time: datetime, processed: int, misuse_detected: int, 
                           reports_created: int, errors: int, status: str) -> Dict[str, Any]:
        """
        Create a summary of the job execution.
        
        Args:
            start_time: Job start time
            processed: Number of users processed
            misuse_detected: Number of users with misuse detected
            reports_created: Number of reports created
            errors: Number of errors encountered
            status: Job status message
            
        Returns:
            Dict containing job summary
        """
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "job_type": "daily_misuse_detection",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "status": status,
            "statistics": {
                "users_processed": processed,
                "misuse_detected": misuse_detected,
                "reports_created": reports_created,
                "errors": errors,
                "success_rate": (processed - errors) / max(processed, 1) * 100
            }
        }


# Global service instance
daily_misuse_job_service = DailyMisuseJobService()
