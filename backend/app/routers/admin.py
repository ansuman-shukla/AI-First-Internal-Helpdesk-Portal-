"""
Admin Router

Provides admin-only endpoints for system management including misuse detection,
reports management, manual job triggers, and system health monitoring.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.security import HTTPBearer
from app.core.auth import require_admin
from app.services.scheduler_service import scheduler_service
from app.services.misuse_reports_service import misuse_reports_service
from app.services.analytics_service import analytics_service
from app.services.user_service import user_service
from app.services.document_service import document_service
from app.services.user_violation_service import user_violation_service
from app.models.misuse_report import MisuseReportResponseSchema
from app.models.user_violation import (
    UserViolationResponseSchema,
    UserViolationSummarySchema
)
from app.schemas.document import DocumentCategory, DocumentUploadResponse, KnowledgeBaseStats
from app.core.database import ping_mongodb
from app.services.ai.startup import health_check as ai_health_check, get_ai_services_status
from app.services.webhook_service import webhook_health_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer()


@router.post("/trigger-misuse-detection", status_code=status.HTTP_200_OK)
async def trigger_manual_misuse_detection(
    window_hours: Optional[int] = Query(None, description="Time window in hours (default: 24)"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Manually trigger misuse detection job for all users.
    
    This endpoint allows admins to manually run the misuse detection job
    for testing purposes or on-demand analysis.
    
    Args:
        window_hours: Optional time window in hours (defaults to configured value)
        current_user: Current authenticated admin user
        
    Returns:
        Dict containing job execution results
    """
    try:
        logger.info(f"Admin {current_user['username']} triggered manual misuse detection")

        # Trigger the manual misuse detection job
        result = await scheduler_service.trigger_manual_misuse_detection(window_hours)

        logger.info(f"Manual misuse detection completed for admin {current_user['username']}")
        return {
            "message": "Misuse detection job completed",
            "triggered_by": current_user["username"],
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error in manual misuse detection trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger misuse detection: {str(e)}"
        )


@router.get("/misuse-reports")
async def get_misuse_reports(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of reports per page"),
    unreviewed_only: bool = Query(False, description="Show only unreviewed reports"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get paginated list of misuse reports for admin dashboard.
    
    Args:
        page: Page number (1-based)
        limit: Number of reports per page
        unreviewed_only: If True, show only unreviewed reports
        current_user: Current authenticated admin user
        
    Returns:
        Paginated list of misuse reports
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting misuse reports - Page: {page}, Limit: {limit}")
        
        if unreviewed_only:
            # Get only unreviewed reports
            reports = await misuse_reports_service.get_all_unreviewed_reports()
            total_count = len(reports)
            unreviewed_count = total_count

            # Apply pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_reports = reports[start_idx:end_idx]
        else:
            # Get all reports (both reviewed and unreviewed) with pagination
            result = await misuse_reports_service.get_all_reports(page, limit)
            paginated_reports = result["reports"]
            total_count = result["total_count"]
            unreviewed_count = result["unreviewed_count"]
        
        # Convert to response schema and add user names
        report_responses = []
        for report in paginated_reports:
            # Get user information
            user_name = "Unknown User"
            try:
                user = await user_service.get_user_by_id(report["user_id"])
                if user:
                    user_name = user.username
            except Exception as e:
                logger.warning(f"Failed to get user name for user_id {report['user_id']}: {str(e)}")

            # Create a modified report dict with user_name
            report_with_user = report.copy()
            report_with_user["user_name"] = user_name

            report_response = MisuseReportResponseSchema(
                id=report["_id"],
                user_id=report["user_id"],
                detection_date=report["detection_date"],
                misuse_type=report["misuse_type"],
                severity_level=report["severity_level"],
                evidence_data=report["evidence_data"],
                admin_reviewed=report["admin_reviewed"],
                action_taken=report.get("action_taken"),
                ai_analysis_metadata=report["ai_analysis_metadata"],
                reviewed_at=report.get("reviewed_at")
            )

            # Add user_name to the response (we'll need to modify the schema or use model_dump)
            report_dict = report_response.model_dump()
            report_dict["user_name"] = user_name
            report_responses.append(report_dict)
        
        # Return as dict since we modified the reports to include user_name
        return {
            "reports": report_responses,
            "total_count": total_count,
            "unreviewed_count": unreviewed_count,
            "page": page,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error getting misuse reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get misuse reports: {str(e)}"
        )


@router.post("/misuse-reports/{report_id}/mark-reviewed", status_code=status.HTTP_200_OK)
async def mark_misuse_report_reviewed(
    report_id: str,
    action_taken: Optional[str] = Query(None, description="Action taken by admin"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Mark a misuse report as reviewed by admin.
    
    Args:
        report_id: ID of the misuse report to mark as reviewed
        action_taken: Optional description of action taken
        current_user: Current authenticated admin user
        
    Returns:
        Dict containing success message
    """
    try:
        logger.info(f"Admin {current_user['username']} marking report {report_id} as reviewed")

        # Mark the report as reviewed
        success = await misuse_reports_service.mark_report_reviewed(report_id, action_taken)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Misuse report {report_id} not found"
            )

        logger.info(f"Report {report_id} marked as reviewed by admin {current_user['username']}")
        return {
            "message": "Misuse report marked as reviewed",
            "report_id": report_id,
            "reviewed_by": current_user["username"],
            "action_taken": action_taken
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking report {report_id} as reviewed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark report as reviewed: {str(e)}"
        )


@router.get("/scheduler-status", status_code=status.HTTP_200_OK)
async def get_scheduler_status(
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get the current status of the scheduler service.

    Args:
        current_user: Current authenticated admin user

    Returns:
        Dict containing scheduler status information
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting scheduler status")

        status = scheduler_service.get_scheduler_status()

        return {
            "message": "Scheduler status retrieved",
            "requested_by": current_user["username"],
            "scheduler_status": status
        }

    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}"
        )


@router.get("/system-management", status_code=status.HTTP_200_OK)
async def get_system_management_status(
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get comprehensive system health and management information.

    This endpoint provides a complete overview of all system components including:
    - Database connectivity and status
    - AI services health and configuration
    - Scheduler service status
    - Webhook system health
    - Overall system health summary

    Args:
        current_user: Current authenticated admin user

    Returns:
        Dict containing comprehensive system management information
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting system management status")

        # Initialize system status response
        system_status = {
            "message": "System management status retrieved",
            "requested_by": current_user["username"],
            "timestamp": None,
            "overall_health": "healthy",
            "components": {
                "database": {"status": "unknown", "details": {}},
                "ai_services": {"status": "unknown", "details": {}},
                "scheduler": {"status": "unknown", "details": {}},
                "webhooks": {"status": "unknown", "details": {}}
            },
            "summary": {
                "total_components": 4,
                "healthy_components": 0,
                "unhealthy_components": 0,
                "error_components": 0
            }
        }

        # Add timestamp
        from datetime import datetime, timezone
        system_status["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Check Database Health
        logger.debug("Checking database health...")
        try:
            db_ping_result = await ping_mongodb()
            if db_ping_result["connected"]:
                system_status["components"]["database"]["status"] = "healthy"
                system_status["components"]["database"]["details"] = {
                    "connected": True,
                    "database_name": str(db_ping_result["database_name"]),
                    "ping_ok": bool(db_ping_result.get("ping_response", {}).get("ok", False))
                }
                system_status["summary"]["healthy_components"] += 1
                logger.debug("Database health check: HEALTHY")
            else:
                system_status["components"]["database"]["status"] = "unhealthy"
                system_status["components"]["database"]["details"] = {
                    "connected": False,
                    "error": str(db_ping_result.get("error", "Unknown error"))
                }
                system_status["summary"]["unhealthy_components"] += 1
                system_status["overall_health"] = "unhealthy"
                logger.warning(f"Database health check: UNHEALTHY - {db_ping_result.get('error', 'Unknown error')}")
        except Exception as e:
            system_status["components"]["database"]["status"] = "error"
            system_status["components"]["database"]["details"] = {"error": str(e)}
            system_status["summary"]["error_components"] += 1
            system_status["overall_health"] = "unhealthy"
            logger.error(f"Database health check failed: {str(e)}")

        # Check AI Services Health
        logger.debug("Checking AI services health...")
        try:
            ai_health_status = ai_health_check()
            ai_services_status = get_ai_services_status()

            if ai_health_status.get("healthy", False):
                system_status["components"]["ai_services"]["status"] = "healthy"
                system_status["summary"]["healthy_components"] += 1
                logger.debug("AI services health check: HEALTHY")
            else:
                system_status["components"]["ai_services"]["status"] = "unhealthy"
                system_status["summary"]["unhealthy_components"] += 1
                system_status["overall_health"] = "unhealthy"
                logger.warning("AI services health check: UNHEALTHY")

            # Simplify AI status for JSON serialization
            system_status["components"]["ai_services"]["details"] = {
                "healthy": bool(ai_health_status.get("healthy", False)),
                "config_valid": bool(ai_services_status.get("ai_config_valid", False)),
                "vector_store_initialized": bool(ai_services_status.get("vector_store_initialized", False)),
                "services_available": {
                    "hsa": bool(ai_services_status.get("services_available", {}).get("hsa", False)),
                    "routing": bool(ai_services_status.get("services_available", {}).get("routing", False)),
                    "rag": bool(ai_services_status.get("services_available", {}).get("rag", False))
                }
            }
        except Exception as e:
            system_status["components"]["ai_services"]["status"] = "error"
            system_status["components"]["ai_services"]["details"] = {"error": str(e)}
            system_status["summary"]["error_components"] += 1
            system_status["overall_health"] = "unhealthy"
            logger.error(f"AI services health check failed: {str(e)}")

        # Check Scheduler Health
        logger.debug("Checking scheduler health...")
        try:
            scheduler_status = scheduler_service.get_scheduler_status()

            if scheduler_status.get("running", False):
                system_status["components"]["scheduler"]["status"] = "healthy"
                system_status["summary"]["healthy_components"] += 1
                logger.debug("Scheduler health check: HEALTHY")
            else:
                system_status["components"]["scheduler"]["status"] = "unhealthy"
                system_status["summary"]["unhealthy_components"] += 1
                system_status["overall_health"] = "unhealthy"
                logger.warning("Scheduler health check: UNHEALTHY - Not running")

            # Simplify scheduler status for JSON serialization
            jobs_info = []
            for job in scheduler_status.get("jobs", []):
                jobs_info.append({
                    "id": str(job.get("id", "")),
                    "name": str(job.get("name", "")),
                    "next_run": str(job.get("next_run", "")) if job.get("next_run") else None
                })

            system_status["components"]["scheduler"]["details"] = {
                "running": bool(scheduler_status.get("running", False)),
                "jobs_count": len(jobs_info),
                "jobs": jobs_info,
                "misuse_detection_enabled": bool(scheduler_status.get("configuration", {}).get("misuse_detection_enabled", False))
            }
        except Exception as e:
            system_status["components"]["scheduler"]["status"] = "error"
            system_status["components"]["scheduler"]["details"] = {"error": str(e)}
            system_status["summary"]["error_components"] += 1
            system_status["overall_health"] = "unhealthy"
            logger.error(f"Scheduler health check failed: {str(e)}")

        # Check Webhook Health
        logger.debug("Checking webhook health...")
        try:
            webhook_healthy = await webhook_health_check()

            if webhook_healthy:
                system_status["components"]["webhooks"]["status"] = "healthy"
                system_status["components"]["webhooks"]["details"] = {
                    "responding": True,
                    "health_check_passed": True
                }
                system_status["summary"]["healthy_components"] += 1
                logger.debug("Webhook health check: HEALTHY")
            else:
                system_status["components"]["webhooks"]["status"] = "unhealthy"
                system_status["components"]["webhooks"]["details"] = {
                    "responding": False,
                    "health_check_passed": False
                }
                system_status["summary"]["unhealthy_components"] += 1
                system_status["overall_health"] = "unhealthy"
                logger.warning("Webhook health check: UNHEALTHY - Not responding")
        except Exception as e:
            system_status["components"]["webhooks"]["status"] = "error"
            system_status["components"]["webhooks"]["details"] = {"error": str(e)}
            system_status["summary"]["error_components"] += 1
            system_status["overall_health"] = "unhealthy"
            logger.error(f"Webhook health check failed: {str(e)}")

        # Log final system health summary
        logger.info(f"System management status completed for admin {current_user['username']} - "
                   f"Overall: {system_status['overall_health']}, "
                   f"Healthy: {system_status['summary']['healthy_components']}/{system_status['summary']['total_components']}")

        return system_status

    except Exception as e:
        logger.error(f"Error getting system management status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system management status: {str(e)}"
        )


# Analytics Endpoints

@router.get("/analytics/overview", status_code=status.HTTP_200_OK)
async def get_analytics_overview(
    days: Optional[int] = Query(None, ge=1, le=365, description="Number of days to analyze (None for all-time)"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get comprehensive analytics overview for admin dashboard.

    Args:
        days: Number of days to analyze (None for all-time)
        current_user: Current authenticated admin user

    Returns:
        Dict containing comprehensive analytics overview
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting analytics overview for {days or 'all-time'} days")

        overview = await analytics_service.get_overview_analytics(days)

        return {
            "message": "Analytics overview retrieved successfully",
            "requested_by": current_user["username"],
            "analytics": overview
        }

    except Exception as e:
        logger.error(f"Error getting analytics overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics overview: {str(e)}"
        )


@router.get("/analytics/trending-topics", status_code=status.HTTP_200_OK)
async def get_trending_topics(
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of topics to return"),
    force_refresh: bool = Query(False, description="Force refresh cache"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get trending topics from cache or fresh analysis.

    This endpoint now uses caching to avoid expensive LLM analysis on every request.
    Topics are cached for 24 hours and refreshed via scheduled jobs.

    Args:
        days: Number of days to analyze
        limit: Maximum number of topics to return
        force_refresh: Force refresh even if cache is valid (default: False)
        current_user: Current authenticated admin user

    Returns:
        Dict containing trending topics analysis (cached or fresh)
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting trending topics for {days} days (force_refresh: {force_refresh})")

        topics = await analytics_service.get_trending_topics(days, limit, force_refresh)

        return {
            "message": "Trending topics retrieved successfully",
            "requested_by": current_user["username"],
            "topics_analysis": topics,
            "cache_info": {
                "from_cache": topics.get("from_cache", False),
                "cache_refresh": topics.get("cache_refresh", False),
                "force_refresh_requested": force_refresh
            }
        }

    except Exception as e:
        logger.error(f"Error getting trending topics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending topics: {str(e)}"
        )


@router.post("/analytics/trending-topics/refresh", status_code=status.HTTP_200_OK)
async def refresh_trending_topics_cache(
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of topics to return"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Manually refresh trending topics cache.

    This endpoint allows admins to manually trigger a cache refresh for trending topics.
    Useful for testing or when immediate updates are needed.

    Args:
        days: Number of days to analyze
        limit: Maximum number of topics to return
        current_user: Current authenticated admin user

    Returns:
        Dict containing refresh status and fresh trending topics
    """
    try:
        logger.info(f"Admin {current_user['username']} manually refreshing trending topics cache for {days} days")

        from app.services.trending_topics_cache import trending_topics_cache_service

        # Force refresh the cache
        topics = await trending_topics_cache_service.refresh_trending_topics_cache(days, limit)

        return {
            "message": "Trending topics cache refreshed successfully",
            "requested_by": current_user["username"],
            "refresh_timestamp": topics.get("generated_at"),
            "topics_analysis": topics
        }

    except Exception as e:
        logger.error(f"Error refreshing trending topics cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh trending topics cache: {str(e)}"
        )


@router.get("/analytics/trending-topics/cache-status", status_code=status.HTTP_200_OK)
async def get_trending_topics_cache_status(
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get trending topics cache status.

    This endpoint provides information about the current state of the trending topics cache,
    including cache entries, expiration times, and cache statistics.

    Args:
        current_user: Current authenticated admin user

    Returns:
        Dict containing cache status information
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting trending topics cache status")

        from app.services.trending_topics_cache import trending_topics_cache_service

        cache_status = await trending_topics_cache_service.get_cache_status()

        return {
            "message": "Trending topics cache status retrieved successfully",
            "requested_by": current_user["username"],
            "cache_status": cache_status
        }

    except Exception as e:
        logger.error(f"Error getting trending topics cache status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending topics cache status: {str(e)}"
        )


@router.delete("/analytics/trending-topics/cache", status_code=status.HTTP_200_OK)
async def clear_trending_topics_cache(
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Clear trending topics cache.

    This endpoint allows admins to clear all trending topics cache entries.
    The next request for trending topics will trigger a fresh analysis.

    Args:
        current_user: Current authenticated admin user

    Returns:
        Dict containing clear operation status
    """
    try:
        logger.info(f"Admin {current_user['username']} clearing trending topics cache")

        from app.services.trending_topics_cache import trending_topics_cache_service

        success = await trending_topics_cache_service.clear_cache()

        if success:
            return {
                "message": "Trending topics cache cleared successfully",
                "requested_by": current_user["username"],
                "cleared_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear trending topics cache"
            )

    except Exception as e:
        logger.error(f"Error clearing trending topics cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear trending topics cache: {str(e)}"
        )


@router.get("/analytics/flagged-users", status_code=status.HTTP_200_OK)
async def get_flagged_users_analytics(
    days: Optional[int] = Query(None, ge=1, le=365, description="Number of days to analyze (None for all-time)"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get analytics about flagged users and their violations.

    Args:
        days: Number of days to analyze (None for all-time)
        current_user: Current authenticated admin user

    Returns:
        Dict containing flagged users analytics
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting flagged users analytics for {days or 'all-time'} days")

        flagged_analytics = await analytics_service.get_flagged_users_analytics(days)

        return {
            "message": "Flagged users analytics retrieved successfully",
            "requested_by": current_user["username"],
            "flagged_users_analytics": flagged_analytics
        }

    except Exception as e:
        logger.error(f"Error getting flagged users analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get flagged users analytics: {str(e)}"
        )


@router.get("/analytics/user-activity", status_code=status.HTTP_200_OK)
async def get_user_activity_analytics(
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get user activity analytics including most active users.

    Args:
        days: Number of days to analyze
        current_user: Current authenticated admin user

    Returns:
        Dict containing user activity analytics
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting user activity analytics for {days} days")

        activity_analytics = await analytics_service.get_user_activity_analytics(days)

        return {
            "message": "User activity analytics retrieved successfully",
            "requested_by": current_user["username"],
            "user_activity_analytics": activity_analytics
        }

    except Exception as e:
        logger.error(f"Error getting user activity analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user activity analytics: {str(e)}"
        )


@router.get("/analytics/resolution-times", status_code=status.HTTP_200_OK)
async def get_resolution_time_analytics(
    days: Optional[int] = Query(None, ge=1, le=365, description="Number of days to analyze (None for all-time)"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get resolution time analytics by department.

    Args:
        days: Number of days to analyze (None for all-time)
        current_user: Current authenticated admin user

    Returns:
        Dict containing resolution time analytics
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting resolution time analytics for {days or 'all-time'} days")

        # Get resolution stats from overview analytics
        overview = await analytics_service.get_overview_analytics(days)
        resolution_stats = overview.get("resolution_statistics", {})

        return {
            "message": "Resolution time analytics retrieved successfully",
            "requested_by": current_user["username"],
            "period": f"Last {days} days" if days else "All time",
            "resolution_analytics": resolution_stats
        }

    except Exception as e:
        logger.error(f"Error getting resolution time analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resolution time analytics: {str(e)}"
        )


@router.get("/analytics/ticket-volume", status_code=status.HTTP_200_OK)
async def get_ticket_volume_analytics(
    days: Optional[int] = Query(None, ge=1, le=365, description="Number of days to analyze (None for all-time)"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get ticket volume analytics by status, department, and urgency.

    Args:
        days: Number of days to analyze (None for all-time)
        current_user: Current authenticated admin user

    Returns:
        Dict containing ticket volume analytics
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting ticket volume analytics for {days or 'all-time'} days")

        # Get ticket stats from overview analytics
        overview = await analytics_service.get_overview_analytics(days)
        ticket_stats = overview.get("ticket_statistics", {})

        return {
            "message": "Ticket volume analytics retrieved successfully",
            "requested_by": current_user["username"],
            "period": f"Last {days} days" if days else "All time",
            "ticket_volume_analytics": ticket_stats
        }

    except Exception as e:
        logger.error(f"Error getting ticket volume analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ticket volume analytics: {str(e)}"
        )


@router.get("/analytics/dashboard-metrics", status_code=status.HTTP_200_OK)
async def get_dashboard_metrics(
    days: Optional[int] = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard metrics for interactive visualizations.

    Args:
        days: Number of days to analyze
        current_user: Current authenticated admin user

    Returns:
        Dict containing dashboard metrics optimized for charts
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting dashboard metrics for {days} days")

        dashboard_metrics = await analytics_service.get_dashboard_metrics(days)

        return {
            "message": "Dashboard metrics retrieved successfully",
            "requested_by": current_user["username"],
            "dashboard_metrics": dashboard_metrics
        }

    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard metrics: {str(e)}"
        )


@router.get("/analytics/time-series", status_code=status.HTTP_200_OK)
async def get_time_series_analytics(
    days: Optional[int] = Query(30, ge=7, le=365, description="Number of days to analyze"),
    granularity: str = Query("daily", regex="^(daily|weekly|monthly)$", description="Time granularity"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get time-series analytics for trend visualization.

    Args:
        days: Number of days to analyze
        granularity: Time granularity (daily, weekly, monthly)
        current_user: Current authenticated admin user

    Returns:
        Dict containing time-series data for charts
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting time-series analytics for {days} days with {granularity} granularity")

        time_series_data = await analytics_service.get_time_series_analytics(days, granularity)

        return {
            "message": "Time-series analytics retrieved successfully",
            "requested_by": current_user["username"],
            "time_series_analytics": time_series_data
        }

    except Exception as e:
        logger.error(f"Error getting time-series analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get time-series analytics: {str(e)}"
        )


@router.get("/analytics/performance-metrics", status_code=status.HTTP_200_OK)
async def get_performance_metrics(
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get performance metrics for agents and departments.

    Args:
        days: Number of days to analyze
        current_user: Current authenticated admin user

    Returns:
        Dict containing performance metrics
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting performance metrics for {days} days")

        performance_metrics = await analytics_service.get_performance_metrics(days)

        return {
            "message": "Performance metrics retrieved successfully",
            "requested_by": current_user["username"],
            "performance_metrics": performance_metrics
        }

    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/misuse-reports/{report_id}", response_model=MisuseReportResponseSchema)
async def get_misuse_report_by_id(
    report_id: str,
    current_user: dict = Depends(require_admin)
) -> MisuseReportResponseSchema:
    """
    Get a specific misuse report by ID.
    
    Args:
        report_id: ID of the misuse report to retrieve
        current_user: Current authenticated admin user
        
    Returns:
        Misuse report details
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting misuse report {report_id}")
        
        # TODO: Implement get_report_by_id method in misuse_reports_service
        # For now, return a placeholder error
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Get report by ID not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting misuse report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get misuse report: {str(e)}"
        )


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: DocumentCategory = Form(...),
    current_user: dict = Depends(require_admin)
) -> DocumentUploadResponse:
    """
    Upload a document to the knowledge base.

    This endpoint allows admins to upload documents (PDF, DOCX, PPTX, TXT)
    that will be processed, chunked, and stored in the vector database
    for RAG functionality.

    Args:
        file: The document file to upload
        category: Document category for organization
        current_user: Current authenticated admin user

    Returns:
        DocumentUploadResponse with processing results
    """
    try:
        logger.info(f"Admin {current_user['username']} uploading document: {file.filename}")

        result = await document_service.upload_document(
            file=file,
            category=category,
            uploaded_by=current_user["username"]
        )

        logger.info(f"Document uploaded successfully: {file.filename} -> {result.vectors_stored} vectors")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload failed: {str(e)}"
        )


@router.get("/documents/stats", response_model=KnowledgeBaseStats, status_code=status.HTTP_200_OK)
async def get_knowledge_base_stats(
    current_user: dict = Depends(require_admin)
) -> KnowledgeBaseStats:
    """
    Get statistics about the knowledge base.

    Args:
        current_user: Current authenticated admin user

    Returns:
        Knowledge base statistics including document counts, categories, and storage info
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting knowledge base stats")

        stats = await document_service.get_knowledge_base_stats()

        logger.debug(f"Knowledge base stats retrieved: {stats.total_documents} documents, {stats.total_vectors} vectors")
        return stats

    except Exception as e:
        logger.error(f"Failed to get knowledge base stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get knowledge base statistics: {str(e)}"
        )


# User Violation Endpoints

@router.get("/user-violations/flagged-users", status_code=status.HTTP_200_OK)
async def get_flagged_users(
    days: Optional[int] = Query(None, ge=1, le=365, description="Number of days to analyze (None for all-time)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of users to return"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get summary of users who have attempted to create tickets with inappropriate content.

    Args:
        days: Number of days to analyze (None for all-time)
        limit: Maximum number of users to return
        current_user: Current authenticated admin user

    Returns:
        Dict containing flagged users summary
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting flagged users for {days or 'all-time'} days")

        flagged_users = await user_violation_service.get_flagged_users_summary(days, limit)

        return {
            "message": "Flagged users retrieved successfully",
            "requested_by": current_user["username"],
            "period": f"Last {days} days" if days else "All time",
            "flagged_users": flagged_users,
            "total_count": len(flagged_users)
        }

    except Exception as e:
        logger.error(f"Error getting flagged users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get flagged users: {str(e)}"
        )


@router.get("/user-violations/user/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_violations(
    user_id: str,
    days: Optional[int] = Query(None, ge=1, le=365, description="Number of days to analyze (None for all-time)"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get all violations for a specific user.

    Args:
        user_id: User ID to get violations for
        days: Number of days to analyze (None for all-time)
        current_user: Current authenticated admin user

    Returns:
        Dict containing user violations
    """
    try:
        logger.info(f"Admin {current_user['username']} requesting violations for user {user_id}")

        violations = await user_violation_service.get_user_violations(user_id, days)

        # Get user information
        user = await user_service.get_user_by_id(user_id)
        username = user.username if user else "Unknown User"

        # Convert to response format
        violation_responses = []
        for violation in violations:
            violation_dict = violation.model_dump()
            violation_responses.append(violation_dict)

        return {
            "message": "User violations retrieved successfully",
            "requested_by": current_user["username"],
            "user_id": user_id,
            "username": username,
            "period": f"Last {days} days" if days else "All time",
            "violations": violation_responses,
            "total_count": len(violation_responses)
        }

    except Exception as e:
        logger.error(f"Error getting violations for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user violations: {str(e)}"
        )


@router.post("/user-violations/{violation_id}/mark-reviewed", status_code=status.HTTP_200_OK)
async def mark_violation_reviewed(
    violation_id: str,
    action_taken: str = Query(..., description="Action taken by admin"),
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Mark a user violation as reviewed by admin.

    Args:
        violation_id: ID of the violation to mark as reviewed
        action_taken: Description of action taken by admin
        current_user: Current authenticated admin user

    Returns:
        Dict containing success message
    """
    try:
        logger.info(f"Admin {current_user['username']} marking violation {violation_id} as reviewed")

        success = await user_violation_service.mark_violation_reviewed(violation_id, action_taken)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User violation {violation_id} not found"
            )

        logger.info(f"Violation {violation_id} marked as reviewed by admin {current_user['username']}")
        return {
            "message": "User violation marked as reviewed",
            "violation_id": violation_id,
            "reviewed_by": current_user["username"],
            "action_taken": action_taken
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking violation {violation_id} as reviewed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark violation as reviewed: {str(e)}"
        )
