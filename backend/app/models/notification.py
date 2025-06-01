"""
Notification model for the helpdesk system

This module defines the NotificationModel class for handling notification data
and database operations.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
from app.schemas.notification import NotificationType

logger = logging.getLogger(__name__)


class NotificationModel:
    """
    Model class for handling notification data and operations
    
    This class provides methods for creating, updating, and managing
    notification documents in MongoDB.
    """
    
    def __init__(
        self,
        user_id: str,
        title: str,
        message: str,
        type: NotificationType,
        data: Optional[Dict[str, Any]] = None,
        notification_id: Optional[str] = None,
        read: bool = False,
        created_at: Optional[datetime] = None,
        read_at: Optional[datetime] = None,
        _id: Optional[ObjectId] = None
    ):
        """
        Initialize a notification model
        
        Args:
            user_id: ID of the user to receive the notification
            title: Notification title
            message: Notification message content
            type: Type of notification
            data: Optional additional data as JSON object
            notification_id: Unique notification identifier (auto-generated if None)
            read: Whether the notification has been read
            created_at: When the notification was created (auto-set if None)
            read_at: When the notification was marked as read
            _id: MongoDB ObjectId
        """
        self._id = _id
        self.user_id = user_id
        self.title = title.strip() if title else ""
        self.message = message.strip() if message else ""
        self.type = type
        self.data = data or {}
        self.read = read
        self.created_at = created_at or datetime.utcnow()
        self.read_at = read_at
        
        # Auto-generate notification ID if not provided
        if notification_id:
            self.notification_id = notification_id
        else:
            self.notification_id = self._generate_notification_id()
        
        logger.debug(f"Created notification model: {self.notification_id} for user {self.user_id}")
    
    def _generate_notification_id(self) -> str:
        """
        Generate a unique notification ID
        
        Returns:
            str: Unique notification ID in format "NOT-<timestamp>-<random>"
        """
        import random
        import string
        
        timestamp = int(self.created_at.timestamp())
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        notification_id = f"NOT-{timestamp}-{random_suffix}"
        
        logger.debug(f"Generated notification ID: {notification_id}")
        return notification_id
    
    def mark_as_read(self) -> None:
        """
        Mark the notification as read
        """
        if not self.read:
            self.read = True
            self.read_at = datetime.utcnow()
            logger.info(f"Marked notification {self.notification_id} as read")
        else:
            logger.debug(f"Notification {self.notification_id} already marked as read")
    
    def mark_as_unread(self) -> None:
        """
        Mark the notification as unread
        """
        if self.read:
            self.read = False
            self.read_at = None
            logger.info(f"Marked notification {self.notification_id} as unread")
        else:
            logger.debug(f"Notification {self.notification_id} already marked as unread")
    
    def update_data(self, new_data: Dict[str, Any]) -> None:
        """
        Update the notification's additional data
        
        Args:
            new_data: New data to merge with existing data
        """
        if self.data is None:
            self.data = {}
        
        self.data.update(new_data)
        logger.debug(f"Updated data for notification {self.notification_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the notification model to a dictionary for MongoDB storage
        
        Returns:
            dict: Dictionary representation of the notification
        """
        doc = {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "type": self.type.value if isinstance(self.type, NotificationType) else self.type,
            "read": self.read,
            "data": self.data,
            "created_at": self.created_at,
            "read_at": self.read_at
        }
        
        if self._id:
            doc["_id"] = self._id
        
        logger.debug(f"Converted notification {self.notification_id} to dict")
        return doc
    
    @classmethod
    def from_dict(cls, doc: Dict[str, Any]) -> 'NotificationModel':
        """
        Create a notification model from a MongoDB document
        
        Args:
            doc: MongoDB document dictionary
            
        Returns:
            NotificationModel: Notification model instance
        """
        try:
            # Convert type string back to enum
            notification_type = doc.get("type")
            if isinstance(notification_type, str):
                notification_type = NotificationType(notification_type)
            
            notification = cls(
                _id=doc.get("_id"),
                notification_id=doc.get("notification_id"),
                user_id=doc.get("user_id"),
                title=doc.get("title", ""),
                message=doc.get("message", ""),
                type=notification_type,
                data=doc.get("data"),
                read=doc.get("read", False),
                created_at=doc.get("created_at"),
                read_at=doc.get("read_at")
            )
            
            logger.debug(f"Created notification model from dict: {notification.notification_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification model from dict: {str(e)}")
            raise ValueError(f"Invalid notification document: {str(e)}")
    
    def __str__(self) -> str:
        """String representation of the notification"""
        return f"Notification({self.notification_id}, {self.type.value}, {self.user_id})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the notification"""
        return (
            f"NotificationModel(notification_id='{self.notification_id}', "
            f"user_id='{self.user_id}', type='{self.type.value}', "
            f"read={self.read}, created_at='{self.created_at}')"
        )
