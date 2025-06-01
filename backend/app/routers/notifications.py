"""
Notification endpoints for the helpdesk system

This module provides REST API endpoints for notification management
including retrieving, marking as read, and managing user notifications.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional

from app.routers.auth import get_current_user
from app.services.notification_service import notification_service
from app.schemas.notification import (
    NotificationListResponse,
    NotificationCountResponse,
    NotificationUpdateSchema
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(20, ge=1, le=100, description="Number of notifications per page"),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get notifications for the current user with pagination
    
    This endpoint returns a paginated list of notifications for the authenticated user.
    Notifications are sorted by creation date (newest first).
    
    Args:
        page: Page number (1-based)
        limit: Number of notifications per page (1-100)
        unread_only: Whether to return only unread notifications
        current_user: Current authenticated user
        
    Returns:
        NotificationListResponse: Paginated list of notifications with metadata
    """
    try:
        user_id = current_user["user_id"]
        
        logger.info(
            f"Getting notifications for user {user_id} "
            f"(page: {page}, limit: {limit}, unread_only: {unread_only})"
        )
        
        # Get notifications from service
        result = await notification_service.get_user_notifications(
            user_id=user_id,
            page=page,
            limit=limit,
            unread_only=unread_only
        )
        
        logger.debug(
            f"Retrieved {len(result.notifications)} notifications for user {user_id} "
            f"(total: {result.total}, unread: {result.unread_count})"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting notifications for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notifications"
        )


@router.get("/unread-count", response_model=NotificationCountResponse)
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """
    Get notification counts for the current user
    
    This endpoint returns the count of unread and total notifications
    for the authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        NotificationCountResponse: Notification counts
    """
    try:
        user_id = current_user["user_id"]
        
        logger.debug(f"Getting notification counts for user {user_id}")
        
        # Get counts from service
        result = await notification_service.get_unread_count(user_id)
        
        logger.debug(
            f"User {user_id} has {result.unread_count} unread notifications "
            f"out of {result.total_count} total"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting notification counts for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification counts"
        )


@router.put("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a specific notification as read
    
    This endpoint marks a single notification as read for the authenticated user.
    Only the owner of the notification can mark it as read.
    
    Args:
        notification_id: ID of the notification to mark as read
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
    """
    try:
        user_id = current_user["user_id"]
        
        logger.info(f"Marking notification {notification_id} as read for user {user_id}")
        
        # Mark notification as read
        success = await notification_service.mark_as_read(notification_id, user_id)
        
        if success:
            logger.info(f"Successfully marked notification {notification_id} as read")
            return {"message": "Notification marked as read", "notification_id": notification_id}
        else:
            logger.warning(f"Notification {notification_id} not found or already read")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or already read"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )


@router.put("/mark-all-read")
async def mark_all_notifications_as_read(current_user: dict = Depends(get_current_user)):
    """
    Mark all notifications as read for the current user
    
    This endpoint marks all unread notifications as read for the authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Success message with count of notifications marked as read
    """
    try:
        user_id = current_user["user_id"]
        
        logger.info(f"Marking all notifications as read for user {user_id}")
        
        # Mark all notifications as read
        count = await notification_service.mark_all_as_read(user_id)
        
        logger.info(f"Marked {count} notifications as read for user {user_id}")
        
        return {
            "message": f"Marked {count} notifications as read",
            "count": count
        }
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark all notifications as read"
        )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a specific notification
    
    This endpoint deletes a notification for the authenticated user.
    Only the owner of the notification can delete it.
    
    Args:
        notification_id: ID of the notification to delete
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
    """
    try:
        user_id = current_user["user_id"]
        
        logger.info(f"Deleting notification {notification_id} for user {user_id}")
        
        # Delete notification
        success = await notification_service.delete_notification(notification_id, user_id)
        
        if success:
            logger.info(f"Successfully deleted notification {notification_id}")
            return {"message": "Notification deleted", "notification_id": notification_id}
        else:
            logger.warning(f"Notification {notification_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification"
        )
