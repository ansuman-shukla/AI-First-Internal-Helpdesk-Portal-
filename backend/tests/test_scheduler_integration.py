"""
Integration tests for the scheduler and misuse detection workflow.

Tests the complete workflow from scheduler trigger to misuse report creation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from app.services.scheduler_service import SchedulerService
from app.services.daily_misuse_job import DailyMisuseJobService
from app.services.misuse_reports_service import MisuseReportsService


class TestSchedulerIntegration:
    """Integration test cases for scheduler workflow"""
    
    @pytest.fixture
    def mock_database(self):
        """Mock database collections"""
        mock_db = {
            "users": AsyncMock(),
            "tickets": AsyncMock(),
            "misuse_reports": AsyncMock()
        }
        return mock_db
    
    @pytest.mark.asyncio
    async def test_complete_misuse_detection_workflow(self, mock_database):
        """Test the complete workflow from scheduler trigger to report creation"""
        
        # Setup mock data
        mock_users = [
            {"_id": str(ObjectId()), "username": "user1", "role": "user"},
            {"_id": str(ObjectId()), "username": "user2", "role": "user"}
        ]
        
        mock_tickets_user1 = [
            {
                "_id": ObjectId(),
                "title": "Help me",
                "description": "I need help",
                "created_at": datetime.utcnow() - timedelta(hours=2)
            },
            {
                "_id": ObjectId(),
                "title": "Help me",  # Duplicate title
                "description": "I need help again",
                "created_at": datetime.utcnow() - timedelta(hours=1)
            }
        ]
        
        mock_tickets_user2 = []  # No tickets for user2
        
        # Mock detection results
        mock_detection_result_user1 = {
            "misuse_detected": True,
            "patterns": ["duplicate_titles"],
            "user_id": mock_users[0]["_id"],
            "analysis_date": datetime.utcnow(),
            "ticket_count": 2,
            "confidence_score": 0.8,
            "analysis_metadata": {
                "tickets_analyzed": [str(ticket["_id"]) for ticket in mock_tickets_user1],
                "content_samples": ["Help me", "Help me"],
                "reasoning": "Duplicate titles detected"
            }
        }
        
        mock_detection_result_user2 = {
            "misuse_detected": False,
            "patterns": [],
            "user_id": mock_users[1]["_id"],
            "analysis_date": datetime.utcnow(),
            "ticket_count": 0,
            "confidence_score": 0.5,
            "analysis_metadata": {
                "tickets_analyzed": [],
                "reasoning": "No tickets to analyze"
            }
        }
        
        # Mock misuse report insertion
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_database["misuse_reports"].insert_one.return_value = mock_insert_result
        mock_database["misuse_reports"].find_one.return_value = None  # No existing report

        # Create service instances
        job_service = DailyMisuseJobService(batch_size=2)
        reports_service = MisuseReportsService()

        # Mock the database connections
        job_service.db = mock_database
        reports_service.db = mock_database
        reports_service.collection = mock_database["misuse_reports"]

        with patch('app.services.daily_misuse_job.detect_misuse_for_user') as mock_detect, \
             patch.object(job_service, '_get_active_users', return_value=mock_users) as mock_get_users, \
             patch('app.services.daily_misuse_job.misuse_reports_service.save_misuse_report', return_value="report_123") as mock_save_report:
            # Configure mock to return different results for different users
            mock_detect.side_effect = [mock_detection_result_user1, mock_detection_result_user2]

            # Run the daily misuse detection job
            result = await job_service.run_daily_misuse_detection()
            
            # Verify job execution results
            assert result["status"] == "Completed successfully"
            assert result["statistics"]["users_processed"] == 2
            assert result["statistics"]["misuse_detected"] == 1
            assert result["statistics"]["reports_created"] == 1
            assert result["statistics"]["errors"] == 0
            
            # Verify detect_misuse_for_user was called for each user
            assert mock_detect.call_count == 2
            mock_detect.assert_any_call(mock_users[0]["_id"], 24)
            mock_detect.assert_any_call(mock_users[1]["_id"], 24)

            # Verify save_misuse_report was called for user1 only (user with misuse detected)
            mock_save_report.assert_called_once_with(mock_detection_result_user1)
    
    @pytest.mark.asyncio
    async def test_scheduler_manual_trigger_integration(self):
        """Test manual trigger through scheduler service"""
        
        # Mock the daily job service
        mock_job_result = {
            "job_type": "manual_misuse_detection",
            "status": "Completed successfully",
            "statistics": {
                "users_processed": 3,
                "misuse_detected": 1,
                "reports_created": 1,
                "errors": 0
            }
        }
        
        with patch.dict('os.environ', {
            "MISUSE_DETECTION_ENABLED": "true",
            "MISUSE_DETECTION_SCHEDULE": "0 2 * * *",
            "MISUSE_DETECTION_WINDOW_HOURS": "24"
        }):
            scheduler_service = SchedulerService()
            
            with patch('app.services.scheduler_service.daily_misuse_job_service.run_daily_misuse_detection', 
                       return_value=mock_job_result) as mock_job:
                
                # Trigger manual misuse detection
                result = await scheduler_service.trigger_manual_misuse_detection()
                
                # Verify the result
                assert result == mock_job_result
                mock_job.assert_called_once_with(24)
    
    @pytest.mark.asyncio
    async def test_scheduler_manual_trigger_custom_window(self):
        """Test manual trigger with custom time window"""
        
        mock_job_result = {"status": "Completed"}
        
        with patch.dict('os.environ', {
            "MISUSE_DETECTION_ENABLED": "true",
            "MISUSE_DETECTION_WINDOW_HOURS": "24"
        }):
            scheduler_service = SchedulerService()
            
            with patch('app.services.scheduler_service.daily_misuse_job_service.run_daily_misuse_detection', 
                       return_value=mock_job_result) as mock_job:
                
                # Trigger with custom 48-hour window
                result = await scheduler_service.trigger_manual_misuse_detection(48)
                
                assert result == mock_job_result
                mock_job.assert_called_once_with(48)
    
    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, mock_database):
        """Test error handling throughout the workflow"""
        
        # Setup mock users
        mock_users = [
            {"_id": str(ObjectId()), "username": "user1", "role": "user"},
            {"_id": str(ObjectId()), "username": "user2", "role": "user"}
        ]
        
        # Setup database mocks
        mock_users_cursor = AsyncMock()
        mock_users_cursor.to_list.return_value = mock_users
        mock_database["users"].find.return_value = mock_users_cursor
        
        # Create service instance
        job_service = DailyMisuseJobService(batch_size=2)
        job_service.db = mock_database
        
        with patch('app.services.daily_misuse_job.detect_misuse_for_user') as mock_detect:
            # Configure mock to raise error for first user, succeed for second
            mock_detect.side_effect = [
                Exception("Detection failed for user1"),
                {"misuse_detected": False, "patterns": [], "user_id": mock_users[1]["_id"]}
            ]
            
            # Run the job
            result = await job_service.run_daily_misuse_detection()
            
            # Verify partial success
            assert result["status"] == "Completed successfully"
            assert result["statistics"]["users_processed"] == 2
            assert result["statistics"]["errors"] == 1
            assert result["statistics"]["success_rate"] == 50.0
    
    @pytest.mark.asyncio
    async def test_batch_processing_workflow(self, mock_database):
        """Test batch processing with multiple batches"""
        
        # Create 5 users to test batch processing (batch size = 2)
        mock_users = [
            {"_id": str(ObjectId()), "username": f"user{i}", "role": "user"}
            for i in range(5)
        ]
        
        # Setup database mocks
        mock_users_cursor = AsyncMock()
        mock_users_cursor.to_list.return_value = mock_users
        mock_database["users"].find.return_value = mock_users_cursor
        
        # Create service instance with small batch size
        job_service = DailyMisuseJobService(batch_size=2)
        job_service.db = mock_database
        
        # Mock detection results (no misuse for simplicity)
        mock_detection_results = [
            {"misuse_detected": False, "patterns": [], "user_id": user["_id"]}
            for user in mock_users
        ]
        
        with patch('app.services.daily_misuse_job.detect_misuse_for_user', 
                   side_effect=mock_detection_results) as mock_detect:
            
            # Run the job
            result = await job_service.run_daily_misuse_detection()
            
            # Verify all users were processed
            assert result["statistics"]["users_processed"] == 5
            assert mock_detect.call_count == 5
            
            # Verify batch processing (should be 3 batches: 2+2+1)
            # This is implicit in the successful processing of all users
    
    @pytest.mark.asyncio
    async def test_duplicate_report_prevention(self, mock_database):
        """Test that duplicate reports are not created for the same user on the same day"""
        
        user_id = str(ObjectId())
        mock_users = [{"_id": user_id, "username": "user1", "role": "user"}]
        
        # Setup database mocks
        mock_users_cursor = AsyncMock()
        mock_users_cursor.to_list.return_value = mock_users
        mock_database["users"].find.return_value = mock_users_cursor
        
        # Mock existing report for today
        existing_report = {"_id": ObjectId(), "user_id": ObjectId(user_id)}
        mock_database["misuse_reports"].find_one.return_value = existing_report
        
        # Create service instances
        job_service = DailyMisuseJobService(batch_size=1)
        reports_service = MisuseReportsService()
        
        job_service.db = mock_database
        reports_service.db = mock_database
        reports_service.collection = mock_database["misuse_reports"]
        
        # Mock detection result with misuse
        mock_detection_result = {
            "misuse_detected": True,
            "patterns": ["high_volume"],
            "user_id": user_id,
            "analysis_date": datetime.utcnow(),
            "confidence_score": 0.8,
            "analysis_metadata": {"reasoning": "Test"}
        }
        
        with patch('app.services.daily_misuse_job.detect_misuse_for_user', 
                   return_value=mock_detection_result):
            
            # Run the job
            result = await job_service.run_daily_misuse_detection()
            
            # Verify job completed but no new report was created
            assert result["statistics"]["misuse_detected"] == 1
            assert result["statistics"]["reports_created"] == 1  # Existing report ID returned
            
            # Verify no insert was attempted
            mock_database["misuse_reports"].insert_one.assert_not_called()
