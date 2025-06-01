"""
Webhook Service

This module provides functionality to fire internal webhooks
for various events in the helpdesk system.
"""

import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

from app.models.message import MessageModel
from app.schemas.webhook import MessageSentPayload

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for firing internal webhooks"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize webhook service
        
        Args:
            base_url: Base URL for the API (for internal webhook calls)
        """
        self.base_url = base_url.rstrip("/")
        self.webhook_base_url = f"{self.base_url}/internal/webhook"

    async def fire_message_sent_webhook(self, message: MessageModel) -> bool:
        """
        Fire webhook for message sent event
        
        Args:
            message: The message that was sent
            
        Returns:
            bool: True if webhook was fired successfully
        """
        try:
            # Prepare webhook payload
            payload = MessageSentPayload(
                message_id=str(message._id),
                ticket_id=str(message.ticket_id),
                sender_id=str(message.sender_id),
                sender_role=message.sender_role.value,
                message_type=message.message_type.value,
                content=message.content,
                isAI=message.isAI,
                feedback=message.feedback.value,
                timestamp=message.timestamp
            )
            
            # Fire webhook
            webhook_url = f"{self.webhook_base_url}/on_message_sent"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload.model_dump(mode='json'),
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(
                        f"Successfully fired message sent webhook - "
                        f"Message: {message._id}, Ticket: {message.ticket_id}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Webhook returned non-200 status: {response.status_code} - "
                        f"Message: {message._id}"
                    )
                    return False
                    
        except httpx.TimeoutException:
            logger.error(f"Webhook timeout for message {message._id}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Webhook request error for message {message._id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error firing webhook for message {message._id}: {e}")
            return False

    async def fire_ticket_created_webhook(self, ticket_data: Dict[str, Any]) -> bool:
        """
        Fire webhook for ticket created event
        
        Args:
            ticket_data: Dictionary containing ticket information
            
        Returns:
            bool: True if webhook was fired successfully
        """
        try:
            webhook_url = f"{self.webhook_base_url}/on_ticket_created"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=ticket_data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully fired ticket created webhook - Ticket: {ticket_data.get('ticket_id')}")
                    return True
                else:
                    logger.warning(f"Ticket webhook returned non-200 status: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error firing ticket created webhook: {e}")
            return False

    async def fire_misuse_detected_webhook(self, misuse_data: Dict[str, Any]) -> bool:
        """
        Fire webhook for misuse detected event
        
        Args:
            misuse_data: Dictionary containing misuse detection information
            
        Returns:
            bool: True if webhook was fired successfully
        """
        try:
            webhook_url = f"{self.webhook_base_url}/on_misuse_detected"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=misuse_data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully fired misuse detected webhook - User: {misuse_data.get('user_id')}")
                    return True
                else:
                    logger.warning(f"Misuse webhook returned non-200 status: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error firing misuse detected webhook: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if webhook system is healthy
        
        Returns:
            bool: True if webhook system is responding
        """
        try:
            webhook_url = f"{self.webhook_base_url}/health"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(webhook_url, timeout=5.0)
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Webhook health check failed: {e}")
            return False


# Global webhook service instance
webhook_service = WebhookService("http://localhost:8000")


# Convenience functions for easy import and use
async def fire_message_sent_webhook(message: MessageModel) -> bool:
    """
    Convenience function to fire message sent webhook
    
    Args:
        message: The message that was sent
        
    Returns:
        bool: True if webhook was fired successfully
    """
    return await webhook_service.fire_message_sent_webhook(message)


async def fire_ticket_created_webhook(ticket_data: Dict[str, Any]) -> bool:
    """
    Convenience function to fire ticket created webhook
    
    Args:
        ticket_data: Dictionary containing ticket information
        
    Returns:
        bool: True if webhook was fired successfully
    """
    return await webhook_service.fire_ticket_created_webhook(ticket_data)


async def fire_misuse_detected_webhook(misuse_data: Dict[str, Any]) -> bool:
    """
    Convenience function to fire misuse detected webhook
    
    Args:
        misuse_data: Dictionary containing misuse detection information
        
    Returns:
        bool: True if webhook was fired successfully
    """
    return await webhook_service.fire_misuse_detected_webhook(misuse_data)


async def webhook_health_check() -> bool:
    """
    Convenience function to check webhook system health
    
    Returns:
        bool: True if webhook system is responding
    """
    return await webhook_service.health_check()
