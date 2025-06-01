"""
Scheduler Service

This service manages background job scheduling using APScheduler.
Handles the daily misuse detection job and provides manual trigger capabilities.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app.services.daily_misuse_job import daily_misuse_job_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing background job scheduling"""
    
    def __init__(self):
        """Initialize the scheduler service"""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        
        # Configuration from environment variables
        self.misuse_detection_enabled = os.getenv("MISUSE_DETECTION_ENABLED", "true").lower() == "true"
        self.misuse_detection_schedule = os.getenv("MISUSE_DETECTION_SCHEDULE", "0 2 * * *")  # Daily at 2 AM
        self.misuse_detection_window_hours = int(os.getenv("MISUSE_DETECTION_WINDOW_HOURS", "24"))
        
        logger.info(f"Scheduler configuration - Enabled: {self.misuse_detection_enabled}, "
                   f"Schedule: {self.misuse_detection_schedule}, Window: {self.misuse_detection_window_hours}h")
    
    async def start_scheduler(self):
        """Start the APScheduler and add scheduled jobs"""
        try:
            if self.scheduler is not None:
                logger.warning("Scheduler is already running")
                return
            
            logger.info("Starting APScheduler")
            
            # Create scheduler instance
            self.scheduler = AsyncIOScheduler()
            
            # Add event listeners
            self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
            
            # Add scheduled jobs if enabled
            if self.misuse_detection_enabled:
                await self._add_daily_misuse_job()
            else:
                logger.info("Misuse detection scheduling is disabled")

            # Add trending topics cache refresh job (always enabled)
            await self._add_trending_topics_refresh_job()
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("APScheduler started successfully")

        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}")
            raise e

    async def _add_trending_topics_refresh_job(self):
        """Add the daily trending topics cache refresh job"""
        try:
            # Schedule trending topics refresh at 3:00 AM daily
            self.scheduler.add_job(
                func=self._run_trending_topics_refresh,
                trigger=CronTrigger(hour=3, minute=0),
                id="trending_topics_refresh",
                name="Daily Trending Topics Cache Refresh",
                replace_existing=True
            )

            logger.info("Added daily trending topics cache refresh job (3:00 AM)")

        except Exception as e:
            logger.error(f"Failed to add trending topics refresh job: {str(e)}")
            raise e
    
    async def stop_scheduler(self):
        """Stop the APScheduler gracefully"""
        try:
            if self.scheduler is None:
                logger.warning("Scheduler is not running")
                return
            
            logger.info("Stopping APScheduler")
            
            # Shutdown the scheduler
            self.scheduler.shutdown(wait=True)
            self.scheduler = None
            self.is_running = False
            
            logger.info("APScheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
            raise e
    
    async def _add_daily_misuse_job(self):
        """Add the daily misuse detection job to the scheduler"""
        try:
            # Parse cron schedule
            cron_parts = self.misuse_detection_schedule.split()
            if len(cron_parts) != 5:
                raise ValueError(f"Invalid cron schedule: {self.misuse_detection_schedule}")
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # Create cron trigger
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            # Add the job
            self.scheduler.add_job(
                func=self._run_daily_misuse_detection,
                trigger=trigger,
                id="daily_misuse_detection",
                name="Daily Misuse Detection Job",
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )
            
            logger.info(f"Added daily misuse detection job with schedule: {self.misuse_detection_schedule}")
            
        except Exception as e:
            logger.error(f"Error adding daily misuse job: {str(e)}")
            raise e
    
    async def _run_daily_misuse_detection(self):
        """Execute the daily misuse detection job"""
        try:
            logger.info("Executing scheduled daily misuse detection job")
            
            # Run the misuse detection job
            result = await daily_misuse_job_service.run_daily_misuse_detection(
                window_hours=self.misuse_detection_window_hours
            )
            
            # Log the result
            stats = result.get("statistics", {})
            logger.info(
                f"Daily misuse detection completed - "
                f"Processed: {stats.get('users_processed', 0)}, "
                f"Misuse detected: {stats.get('misuse_detected', 0)}, "
                f"Reports created: {stats.get('reports_created', 0)}, "
                f"Errors: {stats.get('errors', 0)}"
            )
            
        except Exception as e:
            logger.error(f"Error in scheduled daily misuse detection: {str(e)}")
            raise e

    async def _run_trending_topics_refresh(self):
        """Execute the daily trending topics cache refresh job"""
        try:
            logger.info("Executing scheduled trending topics cache refresh job")

            # Import the cache service
            from app.services.trending_topics_cache import trending_topics_cache_service

            # Refresh cache for common configurations
            refresh_configs = [
                {"days": 30, "limit": 10},  # Default dashboard config
                {"days": 7, "limit": 10},   # Weekly view
                {"days": 90, "limit": 10},  # Quarterly view
            ]

            total_refreshed = 0
            for config in refresh_configs:
                try:
                    result = await trending_topics_cache_service.refresh_trending_topics_cache(
                        days=config["days"],
                        limit=config["limit"]
                    )

                    topics_count = len(result.get("trending_topics", []))
                    tickets_analyzed = result.get("total_tickets_analyzed", 0)

                    logger.info(
                        f"Refreshed trending topics cache for {config['days']} days: "
                        f"{topics_count} topics from {tickets_analyzed} tickets"
                    )
                    total_refreshed += 1

                except Exception as e:
                    logger.error(f"Error refreshing cache for {config}: {str(e)}")

            logger.info(f"Trending topics cache refresh completed - {total_refreshed}/{len(refresh_configs)} configurations refreshed")

        except Exception as e:
            logger.error(f"Error in scheduled trending topics refresh: {str(e)}")
            raise e
    
    async def trigger_manual_misuse_detection(self, window_hours: Optional[int] = None) -> Dict[str, Any]:
        """
        Manually trigger misuse detection job (for testing/admin use)
        
        Args:
            window_hours: Optional custom time window (defaults to configured value)
            
        Returns:
            Dict containing job execution result
        """
        try:
            if window_hours is None:
                window_hours = self.misuse_detection_window_hours
            
            logger.info(f"Manually triggering misuse detection job with {window_hours}h window")
            
            # Run the misuse detection job
            result = await daily_misuse_job_service.run_daily_misuse_detection(window_hours)
            
            logger.info("Manual misuse detection job completed")
            return result
            
        except Exception as e:
            logger.error(f"Error in manual misuse detection: {str(e)}")
            return {
                "job_type": "manual_misuse_detection",
                "status": f"Error: {str(e)}",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "statistics": {
                    "users_processed": 0,
                    "misuse_detected": 0,
                    "reports_created": 0,
                    "errors": 1
                }
            }
    
    async def schedule_one_time_misuse_detection(self, run_at: datetime, window_hours: Optional[int] = None) -> str:
        """
        Schedule a one-time misuse detection job at a specific time
        
        Args:
            run_at: When to run the job
            window_hours: Optional custom time window
            
        Returns:
            str: Job ID
        """
        try:
            if self.scheduler is None:
                raise RuntimeError("Scheduler is not running")
            
            if window_hours is None:
                window_hours = self.misuse_detection_window_hours
            
            # Create a unique job ID
            job_id = f"one_time_misuse_detection_{int(run_at.timestamp())}"
            
            # Add the job
            self.scheduler.add_job(
                func=lambda: daily_misuse_job_service.run_daily_misuse_detection(window_hours),
                trigger=DateTrigger(run_date=run_at),
                id=job_id,
                name=f"One-time Misuse Detection at {run_at}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled one-time misuse detection job {job_id} for {run_at}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error scheduling one-time misuse detection: {str(e)}")
            raise e
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get the current status of the scheduler
        
        Returns:
            Dict containing scheduler status information
        """
        try:
            if self.scheduler is None:
                return {
                    "running": False,
                    "jobs": [],
                    "configuration": {
                        "misuse_detection_enabled": self.misuse_detection_enabled,
                        "schedule": self.misuse_detection_schedule,
                        "window_hours": self.misuse_detection_window_hours
                    }
                }
            
            # Get job information
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
            
            return {
                "running": self.is_running,
                "jobs": jobs,
                "configuration": {
                    "misuse_detection_enabled": self.misuse_detection_enabled,
                    "schedule": self.misuse_detection_schedule,
                    "window_hours": self.misuse_detection_window_hours
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {str(e)}")
            return {
                "running": False,
                "error": str(e),
                "configuration": {
                    "misuse_detection_enabled": self.misuse_detection_enabled,
                    "schedule": self.misuse_detection_schedule,
                    "window_hours": self.misuse_detection_window_hours
                }
            }
    
    def _job_executed_listener(self, event):
        """Listener for successful job executions"""
        logger.info(f"Job {event.job_id} executed successfully")
    
    def _job_error_listener(self, event):
        """Listener for job execution errors"""
        logger.error(f"Job {event.job_id} failed with error: {event.exception}")


# Global scheduler service instance
scheduler_service = SchedulerService()
