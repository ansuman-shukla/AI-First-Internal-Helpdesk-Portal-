"""
Notification service for the helpdesk system

This service handles all notification-related operations including creation,
retrieval, updates, and management of user notifications.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.notification import NotificationModel
from app.schemas.notification import (
    NotificationType, 
    NotificationCreateSchema,
    NotificationSchema,
    NotificationListResponse,
    NotificationCountResponse
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for handling notification operations"""
    
    def __init__(self):
        self.db = None
        self.collection_name = "notifications"
    
    async def _get_collection(self):
        """Get the notifications collection"""
        if self.db is None:
            self.db = get_database()
        return self.db[self.collection_name]
    
    async def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: NotificationType,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a new notification
        
        Args:
            user_id: ID of the user to receive the notification
            title: Notification title
            message: Notification message content
            notification_type: Type of notification
            data: Optional additional data
            
        Returns:
            str: Notification ID if successful, None otherwise
        """
        try:
            # Create notification model
            notification = NotificationModel(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                data=data
            )
            
            # Insert into database
            collection = await self._get_collection()
            result = await collection.insert_one(notification.to_dict())
            
            if result.inserted_id:
                logger.info(
                    f"Created notification {notification.notification_id} for user {user_id} "
                    f"(type: {notification_type.value})"
                )
                return notification.notification_id
            else:
                logger.error(f"Failed to insert notification for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating notification for user {user_id}: {str(e)}")
            return None
    
    async def get_user_notifications(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False
    ) -> NotificationListResponse:
        """
        Get notifications for a user with pagination
        
        Args:
            user_id: ID of the user
            page: Page number (1-based)
            limit: Number of notifications per page
            unread_only: Whether to return only unread notifications
            
        Returns:
            NotificationListResponse: Paginated notification list
        """
        try:
            collection = await self._get_collection()
            
            # Build query
            query = {"user_id": user_id}
            if unread_only:
                query["read"] = False
            
            # Calculate skip value
            skip = (page - 1) * limit
            
            # Get total count
            total = await collection.count_documents(query)
            
            # Get notifications with pagination
            cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            
            # Convert to notification models and schemas
            notifications = []
            for doc in docs:
                try:
                    notification_model = NotificationModel.from_dict(doc)
                    notification_schema = NotificationSchema(
                        id=str(doc["_id"]),
                        notification_id=notification_model.notification_id,
                        user_id=notification_model.user_id,
                        title=notification_model.title,
                        message=notification_model.message,
                        type=notification_model.type,
                        read=notification_model.read,
                        data=notification_model.data,
                        created_at=notification_model.created_at,
                        read_at=notification_model.read_at
                    )
                    notifications.append(notification_schema)
                except Exception as e:
                    logger.error(f"Error converting notification document: {str(e)}")
                    continue
            
            # Get unread count
            unread_count = await collection.count_documents({
                "user_id": user_id,
                "read": False
            })
            
            # Calculate pagination info
            has_next = (skip + limit) < total
            
            logger.debug(
                f"Retrieved {len(notifications)} notifications for user {user_id} "
                f"(page {page}, total: {total}, unread: {unread_count})"
            )
            
            return NotificationListResponse(
                notifications=notifications,
                total=total,
                page=page,
                limit=limit,
                has_next=has_next,
                unread_count=unread_count
            )
            
        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {str(e)}")
            return NotificationListResponse()
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """
        Mark a notification as read
        
        Args:
            notification_id: ID of the notification
            user_id: ID of the user (for security)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            collection = await self._get_collection()
            
            # Update notification
            result = await collection.update_one(
                {
                    "notification_id": notification_id,
                    "user_id": user_id,
                    "read": False  # Only update if currently unread
                },
                {
                    "$set": {
                        "read": True,
                        "read_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Marked notification {notification_id} as read for user {user_id}")
                return True
            else:
                logger.debug(f"Notification {notification_id} not found or already read")
                return False
                
        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
            return False
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """
        Mark all notifications as read for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            int: Number of notifications marked as read
        """
        try:
            collection = await self._get_collection()
            
            # Update all unread notifications for the user
            result = await collection.update_many(
                {
                    "user_id": user_id,
                    "read": False
                },
                {
                    "$set": {
                        "read": True,
                        "read_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Marked {result.modified_count} notifications as read for user {user_id}")
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read for user {user_id}: {str(e)}")
            return 0
    
    async def get_unread_count(self, user_id: str) -> NotificationCountResponse:
        """
        Get notification counts for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            NotificationCountResponse: Notification counts
        """
        try:
            collection = await self._get_collection()
            
            # Get unread count
            unread_count = await collection.count_documents({
                "user_id": user_id,
                "read": False
            })
            
            # Get total count
            total_count = await collection.count_documents({
                "user_id": user_id
            })
            
            logger.debug(f"User {user_id} has {unread_count} unread notifications out of {total_count} total")
            
            return NotificationCountResponse(
                unread_count=unread_count,
                total_count=total_count
            )
            
        except Exception as e:
            logger.error(f"Error getting notification counts for user {user_id}: {str(e)}")
            return NotificationCountResponse()
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """
        Delete a notification
        
        Args:
            notification_id: ID of the notification
            user_id: ID of the user (for security)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            collection = await self._get_collection()
            
            result = await collection.delete_one({
                "notification_id": notification_id,
                "user_id": user_id
            })
            
            if result.deleted_count > 0:
                logger.info(f"Deleted notification {notification_id} for user {user_id}")
                return True
            else:
                logger.debug(f"Notification {notification_id} not found for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting notification {notification_id}: {str(e)}")
            return False


# Global notification service instance
notification_service = NotificationService()
