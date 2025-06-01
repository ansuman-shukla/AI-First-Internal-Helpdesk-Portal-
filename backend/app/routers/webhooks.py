"""
Webhook endpoints for internal system notifications

This module provides stub webhook endpoints for handling internal system events
such as ticket creation and misuse detection.
"""


from fastapi import APIRouter, HTTPException, status
from typing import Optional, Dict, Any
import logging
import json
from datetime import datetime

from app.services.notification_service import notification_service
from app.services.user_service import user_service
from app.services.ticket_service import ticket_service
from app.schemas.notification import NotificationType
from app.schemas.webhook import TicketCreatedPayload, MisuseDetectedPayload, MessageSentPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/webhook", tags=["webhooks"])


@router.post("/on_ticket_created", status_code=status.HTTP_200_OK)
async def on_ticket_created(payload: TicketCreatedPayload):
    """
    Webhook endpoint called when a new ticket is created

    This webhook creates notifications for relevant agents when a new ticket is created.
    Agents in the ticket's department will receive notifications about new tickets.
    """
    logger.info(f"🎫 Webhook: Ticket created - {payload.ticket_id}")
    logger.info(f"📋 Payload details: Department={payload.department}, Misuse={payload.misuse_flag}")

    # Log the full payload for debugging
    logger.debug(f"Ticket creation payload: {payload.model_dump_json()}")

    # Create notifications for agents
    try:
        if payload.misuse_flag:
            logger.warning(
                f"Ticket {payload.ticket_id} flagged for misuse - requires admin review"
            )

            # Get all admin users and create notifications for them
            admin_users = await user_service.get_users_by_role("admin")
            for admin_user in admin_users:
                await notification_service.create_notification(
                    user_id=str(admin_user._id),
                    title="Ticket Flagged for Misuse",
                    message=f"Ticket {payload.ticket_id} has been flagged for potential misuse and requires review.",
                    notification_type=NotificationType.MISUSE_DETECTED,
                    data={
                        "ticket_id": payload.ticket_id,
                        "misuse_flag": True,
                        "urgency": payload.urgency
                    }
                )
            logger.info(f"Created misuse notifications for {len(admin_users)} admin users")
        else:
            logger.info(
                f"Ticket {payload.ticket_id} successfully routed to {payload.department} department"
            )

            # Get agents for the specific department and create notifications
            department_role = f"{payload.department.lower()}_agent"
            logger.info(f"🔍 Looking for agents with role: {department_role}")

            department_agents = await user_service.get_users_by_role(department_role)
            logger.info(f"👥 Found {len(department_agents)} agents for department {payload.department}")

            notification_title = f"New {payload.urgency.upper()} Priority Ticket"
            notification_message = f"New ticket {payload.ticket_id} assigned to {payload.department} department: {payload.title}"

            # Create notifications for all agents in the department
            for i, agent in enumerate(department_agents, 1):
                logger.info(f"📧 Creating notification {i}/{len(department_agents)} for agent {agent.username} (ID: {agent._id})")

                notification_id = await notification_service.create_notification(
                    user_id=str(agent._id),
                    title=notification_title,
                    message=notification_message,
                    notification_type=NotificationType.TICKET_CREATED,
                    data={
                        "ticket_id": payload.ticket_id,
                        "department": payload.department,
                        "urgency": payload.urgency,
                        "status": payload.status
                    }
                )

                if notification_id:
                    logger.info(f"✅ Successfully created notification {notification_id} for agent {agent.username}")
                else:
                    logger.error(f"❌ Failed to create notification for agent {agent.username}")

            logger.info(f"🎯 Created ticket notifications for {len(department_agents)} {department_role} users")

            # ADMIN NOTIFICATIONS: Admins should receive notifications for ALL ticket creations
            logger.info(f"🔍 Getting admin users for ticket creation notification")
            admin_users = await user_service.get_users_by_role("admin")
            logger.info(f"👥 Found {len(admin_users)} admin users")

            admin_notification_title = f"New {payload.urgency.upper()} Priority Ticket Created"
            admin_notification_message = f"New ticket {payload.ticket_id} created in {payload.department} department: {payload.title}"

            # Create notifications for all admin users
            for i, admin in enumerate(admin_users, 1):
                logger.info(f"📧 Creating admin notification {i}/{len(admin_users)} for admin {admin.username} (ID: {admin._id})")

                admin_notification_id = await notification_service.create_notification(
                    user_id=str(admin._id),
                    title=admin_notification_title,
                    message=admin_notification_message,
                    notification_type=NotificationType.TICKET_CREATED,
                    data={
                        "ticket_id": payload.ticket_id,
                        "department": payload.department,
                        "urgency": payload.urgency,
                        "status": payload.status,
                        "admin_notification": True  # Flag to distinguish admin notifications
                    }
                )

                if admin_notification_id:
                    logger.info(f"✅ Successfully created admin notification {admin_notification_id} for admin {admin.username}")
                else:
                    logger.error(f"❌ Failed to create admin notification for admin {admin.username}")

            logger.info(f"🎯 Created admin ticket notifications for {len(admin_users)} admin users")

        logger.info(f"Successfully created notifications for ticket {payload.ticket_id}")

    except Exception as e:
        logger.error(f"Error creating notifications for ticket {payload.ticket_id}: {str(e)}")
        # Don't fail the webhook if notification creation fails

    return {
        "status": "success",
        "message": f"Ticket creation webhook processed for {payload.ticket_id}",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/on_misuse_detected", status_code=status.HTTP_200_OK)
async def on_misuse_detected(payload: MisuseDetectedPayload):
    """
    Webhook endpoint called when misuse is detected

    This webhook creates notifications for administrators when misuse is detected.
    Admins will receive alerts about users who have been flagged for potential misuse.
    """
    logger.warning(f"Webhook: Misuse detected for user {payload.user_id}")

    # Log the full payload for debugging
    logger.debug(f"Misuse detection payload: {payload.model_dump_json()}")

    # Create notification for admins about misuse detection
    try:
        logger.warning(
            f"Misuse detected - User: {payload.user_id}, "
            f"Ticket: {payload.ticket_id}, Type: {payload.misuse_type}"
        )

        # Get all admin users and create notifications for them
        admin_users = await user_service.get_users_by_role("admin")

        notification_title = "User Misuse Detected"
        notification_message = (
            f"User {payload.user_id} has been flagged for potential misuse "
            f"(Type: {payload.misuse_type}). Please review their activity."
        )

        # Create notifications for all admin users
        for admin_user in admin_users:
            await notification_service.create_notification(
                user_id=str(admin_user._id),
                title=notification_title,
                message=notification_message,
                notification_type=NotificationType.MISUSE_DETECTED,
                data={
                    "user_id": payload.user_id,
                    "ticket_id": payload.ticket_id,
                    "misuse_type": payload.misuse_type,
                    "detection_date": payload.detection_date
                }
            )

        logger.info(f"Created misuse detection notifications for {len(admin_users)} admin users")

    except Exception as e:
        logger.error(f"Error creating misuse detection notification: {str(e)}")
        # Don't fail the webhook if notification creation fails

    return {
        "status": "success",
        "message": f"Misuse detection webhook processed for user {payload.user_id}",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/on_message_sent", status_code=status.HTTP_200_OK)
async def on_message_sent(payload: MessageSentPayload):
    """
    Webhook endpoint called when a message is sent in a ticket

    This webhook creates notifications for relevant users when a new message is sent.
    Users involved in the ticket conversation will receive notifications about new messages.
    """
    logger.info(
        f"Webhook: Message sent - Ticket: {payload.ticket_id}, "
        f"Sender: {payload.sender_id} ({payload.sender_role}), "
        f"AI: {payload.isAI}"
    )

    # Log the full payload for debugging
    logger.debug(f"Message sent payload: {payload.model_dump_json()}")

    # Create notifications for message recipients
    try:
        # Get all participants in the ticket (creator and assignee)
        participants = await ticket_service.get_ticket_participants(payload.ticket_id)

        # Don't notify the sender of their own message
        sender_id_str = str(payload.sender_id)
        recipients = [p for p in participants if p != sender_id_str]

        if not recipients:
            logger.debug(f"No recipients to notify for message in ticket {payload.ticket_id}")
        else:
            # Determine notification title and message based on sender role
            if payload.isAI:
                notification_title = "AI Response Received"
                notification_message = f"AI assistant has responded to your ticket {payload.ticket_id}"
            elif payload.sender_role in ["it_agent", "hr_agent", "admin"]:
                notification_title = "Agent Response Received"
                notification_message = f"An agent has responded to your ticket {payload.ticket_id}"
            else:
                notification_title = "New Message Received"
                notification_message = f"New message received in ticket {payload.ticket_id}"

            # Create notifications for all recipients
            for recipient_id in recipients:
                await notification_service.create_notification(
                    user_id=recipient_id,
                    title=notification_title,
                    message=notification_message,
                    notification_type=NotificationType.MESSAGE_RECEIVED,
                    data={
                        "ticket_id": payload.ticket_id,
                        "message_id": payload.message_id,
                        "sender_id": payload.sender_id,
                        "sender_role": payload.sender_role,
                        "isAI": payload.isAI,
                        "message_type": payload.message_type
                    }
                )

            logger.info(f"Created message notifications for {len(recipients)} recipients in ticket {payload.ticket_id}")

    except Exception as e:
        logger.error(f"Error creating message notification for ticket {payload.ticket_id}: {str(e)}")
        # Don't fail the webhook if notification creation fails

    return {
        "status": "success",
        "message": f"Message webhook processed for ticket {payload.ticket_id}",
        "timestamp": datetime.utcnow().isoformat()
    }


# Health check endpoint for webhook system
@router.get("/health", status_code=status.HTTP_200_OK)
async def webhook_health():
    """Health check endpoint for webhook system"""
    return {
        "status": "healthy",
        "service": "webhook-system",
        "timestamp": datetime.utcnow().isoformat()
    }
