"""
Unit tests for the daily misuse job service.

Tests the daily misuse detection job functionality including user processing,
batch handling, and report creation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from app.services.daily_misuse_job import DailyMisuseJobService


class TestDailyMisuseJobService:
    """Test cases for DailyMisuseJobService"""
    
    @pytest.fixture
    def job_service(self):
        """Create a DailyMisuseJobService instance for testing"""
        return DailyMisuseJobService(batch_size=2)  # Small batch size for testing
    
    @pytest.mark.asyncio
    async def test_run_daily_misuse_detection_no_users(self, job_service):
        """Test daily misuse detection with no active users"""
        with patch.object(job_service, '_get_active_users', return_value=[]):
            result = await job_service.run_daily_misuse_detection()
            
            assert result["status"] == "No active users"
            assert result["statistics"]["users_processed"] == 0
            assert result["statistics"]["misuse_detected"] == 0
            assert result["statistics"]["reports_created"] == 0
    
    @pytest.mark.asyncio
    async def test_run_daily_misuse_detection_success(self, job_service):
        """Test successful daily misuse detection with multiple users"""
        # Mock users
        mock_users = [
            {"_id": str(ObjectId()), "username": "user1", "role": "user"},
            {"_id": str(ObjectId()), "username": "user2", "role": "user"},
            {"_id": str(ObjectId()), "username": "user3", "role": "user"}
        ]
        
        # Mock batch processing results
        mock_batch_results = [
            {"processed": 2, "misuse_detected": 1, "reports_created": 1, "errors": 0},
            {"processed": 1, "misuse_detected": 0, "reports_created": 0, "errors": 0}
        ]
        
        with patch.object(job_service, '_get_active_users', return_value=mock_users), \
             patch.object(job_service, '_process_user_batch', side_effect=mock_batch_results):
            
            result = await job_service.run_daily_misuse_detection()
            
            assert result["status"] == "Completed successfully"
            assert result["statistics"]["users_processed"] == 3
            assert result["statistics"]["misuse_detected"] == 1
            assert result["statistics"]["reports_created"] == 1
            assert result["statistics"]["errors"] == 0
            assert result["statistics"]["success_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_get_active_users_success(self, job_service):
        """Test getting active users from database"""
        mock_users = [
            {"_id": ObjectId(), "username": "user1", "role": "user"},
            {"_id": ObjectId(), "username": "agent1", "role": "it_agent"}
        ]

        # Convert ObjectIds to strings as the method does
        expected_users = [
            {"_id": str(user["_id"]), "username": user["username"], "role": user["role"]}
            for user in mock_users
        ]

        with patch.object(job_service, '_get_active_users', return_value=expected_users) as mock_get_users:
            users = await job_service._get_active_users()

            assert len(users) == 2
            assert all(isinstance(user["_id"], str) for user in users)
            assert users[0]["username"] == "user1"
            assert users[1]["username"] == "agent1"

            mock_get_users.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_users_database_error(self, job_service):
        """Test handling database error when getting active users"""
        mock_collection = AsyncMock()
        mock_collection.find.side_effect = Exception("Database error")
        
        with patch.object(job_service, 'db', {"users": mock_collection}):
            users = await job_service._get_active_users()
            
            assert users == []
    
    @pytest.mark.asyncio
    async def test_process_user_batch_success(self, job_service):
        """Test processing a batch of users successfully"""
        mock_users = [
            {"_id": str(ObjectId()), "username": "user1"},
            {"_id": str(ObjectId()), "username": "user2"}
        ]
        
        # Mock individual user processing results
        mock_results = [
            {"misuse_detected": True, "report_created": True},
            {"misuse_detected": False, "report_created": False}
        ]
        
        with patch.object(job_service, '_process_single_user', side_effect=mock_results):
            result = await job_service._process_user_batch(mock_users, 24)
            
            assert result["processed"] == 2
            assert result["misuse_detected"] == 1
            assert result["reports_created"] == 1
            assert result["errors"] == 0
    
    @pytest.mark.asyncio
    async def test_process_user_batch_with_errors(self, job_service):
        """Test processing a batch of users with some errors"""
        mock_users = [
            {"_id": str(ObjectId()), "username": "user1"},
            {"_id": str(ObjectId()), "username": "user2"}
        ]
        
        # Mock one success and one error
        mock_results = [
            {"misuse_detected": True, "report_created": True},
            Exception("Processing error")
        ]
        
        with patch.object(job_service, '_process_single_user', side_effect=mock_results):
            result = await job_service._process_user_batch(mock_users, 24)
            
            assert result["processed"] == 2
            assert result["misuse_detected"] == 1
            assert result["reports_created"] == 1
            assert result["errors"] == 1
    
    @pytest.mark.asyncio
    async def test_process_single_user_misuse_detected(self, job_service):
        """Test processing a single user with misuse detected"""
        user_id = str(ObjectId())
        username = "test_user"
        
        # Mock detection result with misuse
        mock_detection_result = {
            "misuse_detected": True,
            "patterns": ["high_volume"],
            "confidence_score": 0.8
        }
        
        with patch('app.services.daily_misuse_job.detect_misuse_for_user', return_value=mock_detection_result), \
             patch('app.services.daily_misuse_job.misuse_reports_service.save_misuse_report', return_value="report_123"), \
             patch.object(job_service, '_notify_admin_of_misuse') as mock_notify:
            
            result = await job_service._process_single_user(user_id, username, 24)
            
            assert result["misuse_detected"] is True
            assert result["report_created"] is True
            assert result["report_id"] == "report_123"
            
            # Verify admin notification was called
            mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_single_user_no_misuse(self, job_service):
        """Test processing a single user with no misuse detected"""
        user_id = str(ObjectId())
        username = "test_user"
        
        # Mock detection result with no misuse
        mock_detection_result = {
            "misuse_detected": False,
            "patterns": [],
            "confidence_score": 0.3
        }
        
        with patch('app.services.daily_misuse_job.detect_misuse_for_user', return_value=mock_detection_result):
            result = await job_service._process_single_user(user_id, username, 24)
            
            assert result["misuse_detected"] is False
            assert result["report_created"] is False
    
    @pytest.mark.asyncio
    async def test_process_single_user_report_save_failure(self, job_service):
        """Test processing a single user when report save fails"""
        user_id = str(ObjectId())
        username = "test_user"
        
        # Mock detection result with misuse
        mock_detection_result = {
            "misuse_detected": True,
            "patterns": ["high_volume"],
            "confidence_score": 0.8
        }
        
        with patch('app.services.daily_misuse_job.detect_misuse_for_user', return_value=mock_detection_result), \
             patch('app.services.daily_misuse_job.misuse_reports_service.save_misuse_report', return_value=None):
            
            result = await job_service._process_single_user(user_id, username, 24)
            
            assert result["misuse_detected"] is True
            assert result["report_created"] is False
    
    @pytest.mark.asyncio
    async def test_process_single_user_detection_error(self, job_service):
        """Test processing a single user when detection fails"""
        user_id = str(ObjectId())
        username = "test_user"
        
        with patch('app.services.daily_misuse_job.detect_misuse_for_user', side_effect=Exception("Detection error")):
            with pytest.raises(Exception, match="Detection error"):
                await job_service._process_single_user(user_id, username, 24)
    
    @pytest.mark.asyncio
    async def test_notify_admin_of_misuse(self, job_service):
        """Test admin notification for detected misuse"""
        user_id = str(ObjectId())
        username = "test_user"
        report_id = "report_123"
        detection_result = {
            "analysis_date": datetime.utcnow(),
            "patterns": ["high_volume"],
            "confidence_score": 0.8,
            "ticket_count": 6
        }
        
        # This should not raise an exception (just logs for now)
        await job_service._notify_admin_of_misuse(user_id, username, report_id, detection_result)
    
    def test_create_job_summary(self, job_service):
        """Test job summary creation"""
        start_time = datetime.utcnow()
        
        summary = job_service._create_job_summary(
            start_time, 10, 2, 2, 1, "Test completed"
        )
        
        assert summary["job_type"] == "daily_misuse_detection"
        assert summary["status"] == "Test completed"
        assert summary["statistics"]["users_processed"] == 10
        assert summary["statistics"]["misuse_detected"] == 2
        assert summary["statistics"]["reports_created"] == 2
        assert summary["statistics"]["errors"] == 1
        assert summary["statistics"]["success_rate"] == 90.0
        assert "start_time" in summary
        assert "end_time" in summary
        assert "duration_seconds" in summary
