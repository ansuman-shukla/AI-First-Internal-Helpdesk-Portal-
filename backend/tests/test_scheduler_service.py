"""
Unit tests for the scheduler service.

Tests the scheduler service functionality including starting/stopping scheduler,
job scheduling, and manual triggers.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import os

from app.services.scheduler_service import SchedulerService


class TestSchedulerService:
    """Test cases for SchedulerService"""
    
    @pytest.fixture
    def scheduler_service(self):
        """Create a SchedulerService instance for testing"""
        # Mock environment variables
        with patch.dict(os.environ, {
            "MISUSE_DETECTION_ENABLED": "true",
            "MISUSE_DETECTION_SCHEDULE": "0 2 * * *",
            "MISUSE_DETECTION_WINDOW_HOURS": "24"
        }):
            return SchedulerService()
    
    @pytest.fixture
    def disabled_scheduler_service(self):
        """Create a SchedulerService instance with scheduling disabled"""
        with patch.dict(os.environ, {
            "MISUSE_DETECTION_ENABLED": "false",
            "MISUSE_DETECTION_SCHEDULE": "0 2 * * *",
            "MISUSE_DETECTION_WINDOW_HOURS": "24"
        }):
            return SchedulerService()
    
    def test_scheduler_service_initialization(self, scheduler_service):
        """Test scheduler service initialization with default config"""
        assert scheduler_service.misuse_detection_enabled is True
        assert scheduler_service.misuse_detection_schedule == "0 2 * * *"
        assert scheduler_service.misuse_detection_window_hours == 24
        assert scheduler_service.scheduler is None
        assert scheduler_service.is_running is False
    
    def test_scheduler_service_initialization_disabled(self, disabled_scheduler_service):
        """Test scheduler service initialization with disabled config"""
        assert disabled_scheduler_service.misuse_detection_enabled is False
    
    @pytest.mark.asyncio
    async def test_start_scheduler_success(self, scheduler_service):
        """Test successfully starting the scheduler"""
        with patch('app.services.scheduler_service.AsyncIOScheduler') as mock_scheduler_class:
            mock_scheduler = AsyncMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            await scheduler_service.start_scheduler()
            
            assert scheduler_service.scheduler == mock_scheduler
            assert scheduler_service.is_running is True
            
            # Verify scheduler was configured and started
            mock_scheduler.add_listener.assert_called()
            mock_scheduler.add_job.assert_called_once()
            mock_scheduler.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_scheduler_disabled(self, disabled_scheduler_service):
        """Test starting scheduler when misuse detection is disabled"""
        with patch('app.services.scheduler_service.AsyncIOScheduler') as mock_scheduler_class:
            mock_scheduler = AsyncMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            await disabled_scheduler_service.start_scheduler()
            
            assert disabled_scheduler_service.scheduler == mock_scheduler
            assert disabled_scheduler_service.is_running is True
            
            # Verify no job was added when disabled
            mock_scheduler.add_job.assert_not_called()
            mock_scheduler.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(self, scheduler_service):
        """Test starting scheduler when it's already running"""
        scheduler_service.scheduler = AsyncMock()
        
        await scheduler_service.start_scheduler()
        
        # Should not create a new scheduler
        assert isinstance(scheduler_service.scheduler, AsyncMock)
    
    @pytest.mark.asyncio
    async def test_start_scheduler_error(self, scheduler_service):
        """Test handling error when starting scheduler"""
        with patch('app.services.scheduler_service.AsyncIOScheduler', side_effect=Exception("Scheduler error")):
            with pytest.raises(Exception, match="Scheduler error"):
                await scheduler_service.start_scheduler()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_success(self, scheduler_service):
        """Test successfully stopping the scheduler"""
        mock_scheduler = AsyncMock()
        scheduler_service.scheduler = mock_scheduler
        scheduler_service.is_running = True
        
        await scheduler_service.stop_scheduler()
        
        assert scheduler_service.scheduler is None
        assert scheduler_service.is_running is False
        
        mock_scheduler.shutdown.assert_called_once_with(wait=True)
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self, scheduler_service):
        """Test stopping scheduler when it's not running"""
        await scheduler_service.stop_scheduler()
        
        # Should not raise an error
        assert scheduler_service.scheduler is None
        assert scheduler_service.is_running is False
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_error(self, scheduler_service):
        """Test handling error when stopping scheduler"""
        mock_scheduler = AsyncMock()
        mock_scheduler.shutdown.side_effect = Exception("Shutdown error")
        scheduler_service.scheduler = mock_scheduler
        
        with pytest.raises(Exception, match="Shutdown error"):
            await scheduler_service.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_trigger_manual_misuse_detection_success(self, scheduler_service):
        """Test successfully triggering manual misuse detection"""
        mock_result = {
            "job_type": "manual_misuse_detection",
            "status": "Completed successfully",
            "statistics": {"users_processed": 5, "misuse_detected": 1}
        }
        
        with patch('app.services.scheduler_service.daily_misuse_job_service.run_daily_misuse_detection', 
                   return_value=mock_result) as mock_job:
            
            result = await scheduler_service.trigger_manual_misuse_detection()
            
            assert result == mock_result
            mock_job.assert_called_once_with(24)  # Default window hours
    
    @pytest.mark.asyncio
    async def test_trigger_manual_misuse_detection_custom_window(self, scheduler_service):
        """Test triggering manual misuse detection with custom window"""
        mock_result = {"status": "Completed"}
        
        with patch('app.services.scheduler_service.daily_misuse_job_service.run_daily_misuse_detection', 
                   return_value=mock_result) as mock_job:
            
            result = await scheduler_service.trigger_manual_misuse_detection(48)
            
            assert result == mock_result
            mock_job.assert_called_once_with(48)
    
    @pytest.mark.asyncio
    async def test_trigger_manual_misuse_detection_error(self, scheduler_service):
        """Test handling error in manual misuse detection"""
        with patch('app.services.scheduler_service.daily_misuse_job_service.run_daily_misuse_detection', 
                   side_effect=Exception("Job error")):
            
            result = await scheduler_service.trigger_manual_misuse_detection()
            
            assert result["status"] == "Error: Job error"
            assert result["statistics"]["errors"] == 1
    
    @pytest.mark.asyncio
    async def test_schedule_one_time_misuse_detection_success(self, scheduler_service):
        """Test scheduling a one-time misuse detection job"""
        mock_scheduler = AsyncMock()
        scheduler_service.scheduler = mock_scheduler
        
        run_at = datetime.utcnow() + timedelta(hours=1)
        
        job_id = await scheduler_service.schedule_one_time_misuse_detection(run_at)
        
        assert job_id.startswith("one_time_misuse_detection_")
        mock_scheduler.add_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_schedule_one_time_misuse_detection_no_scheduler(self, scheduler_service):
        """Test scheduling one-time job when scheduler is not running"""
        with pytest.raises(RuntimeError, match="Scheduler is not running"):
            run_at = datetime.utcnow() + timedelta(hours=1)
            await scheduler_service.schedule_one_time_misuse_detection(run_at)
    
    @pytest.mark.asyncio
    async def test_schedule_one_time_misuse_detection_error(self, scheduler_service):
        """Test handling error when scheduling one-time job"""
        mock_scheduler = AsyncMock()
        mock_scheduler.add_job.side_effect = Exception("Scheduling error")
        scheduler_service.scheduler = mock_scheduler
        
        with pytest.raises(Exception, match="Scheduling error"):
            run_at = datetime.utcnow() + timedelta(hours=1)
            await scheduler_service.schedule_one_time_misuse_detection(run_at)
    
    def test_get_scheduler_status_not_running(self, scheduler_service):
        """Test getting scheduler status when not running"""
        status = scheduler_service.get_scheduler_status()
        
        assert status["running"] is False
        assert status["jobs"] == []
        assert status["configuration"]["misuse_detection_enabled"] is True
        assert status["configuration"]["schedule"] == "0 2 * * *"
        assert status["configuration"]["window_hours"] == 24
    
    def test_get_scheduler_status_running(self, scheduler_service):
        """Test getting scheduler status when running"""
        mock_job = MagicMock()
        mock_job.id = "daily_misuse_detection"
        mock_job.name = "Daily Misuse Detection Job"
        mock_job.next_run_time = datetime.utcnow() + timedelta(hours=1)
        mock_job.trigger = "cron"
        
        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.return_value = [mock_job]
        
        scheduler_service.scheduler = mock_scheduler
        scheduler_service.is_running = True
        
        status = scheduler_service.get_scheduler_status()
        
        assert status["running"] is True
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["id"] == "daily_misuse_detection"
        assert status["jobs"][0]["name"] == "Daily Misuse Detection Job"
        assert status["jobs"][0]["next_run"] is not None
    
    def test_get_scheduler_status_error(self, scheduler_service):
        """Test handling error when getting scheduler status"""
        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.side_effect = Exception("Status error")
        scheduler_service.scheduler = mock_scheduler
        
        status = scheduler_service.get_scheduler_status()
        
        assert status["running"] is False
        assert "error" in status
        assert status["error"] == "Status error"
    
    @pytest.mark.asyncio
    async def test_run_daily_misuse_detection_job(self, scheduler_service):
        """Test the scheduled daily misuse detection job execution"""
        mock_result = {
            "statistics": {
                "users_processed": 10,
                "misuse_detected": 2,
                "reports_created": 2,
                "errors": 0
            }
        }
        
        with patch('app.services.scheduler_service.daily_misuse_job_service.run_daily_misuse_detection', 
                   return_value=mock_result) as mock_job:
            
            await scheduler_service._run_daily_misuse_detection()
            
            mock_job.assert_called_once_with(window_hours=24)
    
    @pytest.mark.asyncio
    async def test_run_daily_misuse_detection_job_error(self, scheduler_service):
        """Test handling error in scheduled daily misuse detection job"""
        with patch('app.services.scheduler_service.daily_misuse_job_service.run_daily_misuse_detection', 
                   side_effect=Exception("Job execution error")):
            
            with pytest.raises(Exception, match="Job execution error"):
                await scheduler_service._run_daily_misuse_detection()
    
    def test_job_executed_listener(self, scheduler_service):
        """Test job executed event listener"""
        mock_event = MagicMock()
        mock_event.job_id = "test_job"
        
        # Should not raise an exception
        scheduler_service._job_executed_listener(mock_event)
    
    def test_job_error_listener(self, scheduler_service):
        """Test job error event listener"""
        mock_event = MagicMock()
        mock_event.job_id = "test_job"
        mock_event.exception = Exception("Test error")
        
        # Should not raise an exception
        scheduler_service._job_error_listener(mock_event)
