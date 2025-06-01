"""
WebSocket Chat Router

This module provides WebSocket endpoints for real-time chat functionality
within tickets, including authentication and message broadcasting.
"""

import logging
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from bson import ObjectId

from app.services.websocket_manager import connection_manager
from app.services.message_service import message_service
from app.services.ticket_service import ticket_service
from app.services.auth_service import decode_access_token
from app.services.webhook_service import fire_message_sent_webhook
from app.schemas.message import MessageRole, MessageType, MessageFeedback, WebSocketMessageSchema
from app.schemas.user import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket-chat"])


async def authenticate_websocket_user(token: str) -> Dict[str, Any]:
    """
    Authenticate user from WebSocket token

    Args:
        token: JWT token

    Returns:
        Dict containing user info

    Raises:
        HTTPException: If authentication fails
    """
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        user_id = payload.get("user_id")  # This is the actual ObjectId string
        user_role = payload.get("role")

        if not username or not user_id or not user_role:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return {
            "username": username,
            "user_id": user_id,  # Now using the actual ObjectId string
            "user_role": user_role
        }
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def verify_ticket_access(user_id: str, user_role: str, ticket_id: str) -> bool:
    """
    Verify if user has access to the ticket
    
    Args:
        user_id: ID of the user
        user_role: Role of the user
        ticket_id: ID of the ticket
        
    Returns:
        bool: True if user has access
    """
    try:
        # Get ticket with role-based access control
        ticket = await ticket_service.get_ticket_by_id_with_role(
            ticket_id, user_id, UserRole(user_role)
        )
        return ticket is not None
    except Exception as e:
        logger.error(f"Error verifying ticket access: {e}")
        return False


@router.websocket("/chat/{ticket_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    ticket_id: str,
    token: Optional[str] = Query(None, description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time chat within a ticket
    
    This endpoint handles:
    - User authentication via JWT token
    - Ticket access verification
    - Real-time message broadcasting
    - Connection management
    
    Args:
        websocket: WebSocket connection
        ticket_id: ID of the ticket to join
        token: JWT authentication token (required)
    """
    connection_id = None
    
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=4001, reason="Authentication token required")
            return
        
        try:
            user_info = await authenticate_websocket_user(token)
            user_id = user_info["user_id"]
            user_role = user_info["user_role"]
        except HTTPException:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
        
        # Verify ticket access
        has_access = await verify_ticket_access(user_id, user_role, ticket_id)
        if not has_access:
            await websocket.close(code=4003, reason="Access denied to ticket")
            return
        
        # Connect to WebSocket manager
        connection_id = await connection_manager.connect(
            websocket=websocket,
            user_id=user_id,
            user_role=user_role,
            ticket_id=ticket_id,
            username=f"User_{user_id[:8]}"  # TODO: Get actual username from user service
        )
        
        logger.info(f"WebSocket connected - User: {user_id}, Ticket: {ticket_id}")
        
        # Send connection confirmation
        await connection_manager.send_personal_message(
            connection_id,
            {
                "type": "connection_established",
                "ticket_id": ticket_id,
                "user_id": user_id,
                "connection_id": connection_id,
                "timestamp": connection_manager.active_connections[connection_id].__dict__.get("connected_at", "")
            }
        )
        
        # Main message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Validate message structure
                try:
                    ws_message = WebSocketMessageSchema(**message_data)
                except Exception as e:
                    logger.warning(f"Invalid message format from {user_id}: {e}")
                    await connection_manager.send_personal_message(
                        connection_id,
                        {
                            "type": "error",
                            "message": "Invalid message format",
                            "timestamp": connection_manager.active_connections[connection_id].__dict__.get("connected_at", "")
                        }
                    )
                    continue
                
                # Handle different message types
                await handle_websocket_message(
                    ws_message, user_id, user_role, connection_id
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected - User: {user_id}, Ticket: {ticket_id}")
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {user_id}")
                try:
                    await connection_manager.send_personal_message(
                        connection_id,
                        {
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": connection_manager.active_connections[connection_id].__dict__.get("connected_at", "")
                        }
                    )
                except Exception as send_error:
                    logger.error(f"Failed to send error message to {user_id}: {send_error}")
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {user_id}: {e}")
                try:
                    await connection_manager.send_personal_message(
                        connection_id,
                        {
                            "type": "error",
                            "message": "Internal server error",
                            "timestamp": connection_manager.active_connections[connection_id].__dict__.get("connected_at", "")
                        }
                    )
                except Exception as send_error:
                    logger.error(f"Failed to send error message to {user_id}: {send_error}")
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.close(code=4000, reason="Internal server error")
            except:
                pass
    
    finally:
        # Clean up connection
        if connection_id:
            await connection_manager.disconnect(connection_id, "Connection closed")


async def handle_websocket_message(
    ws_message: WebSocketMessageSchema,
    user_id: str,
    user_role: str,
    connection_id: str
):
    """
    Handle different types of WebSocket messages
    
    Args:
        ws_message: Validated WebSocket message
        user_id: ID of the sender
        user_role: Role of the sender
        connection_id: WebSocket connection ID
    """
    try:
        if ws_message.type == "chat":
            await handle_chat_message(ws_message, user_id, user_role, connection_id)
        elif ws_message.type == "typing":
            await handle_typing_indicator(ws_message, user_id, connection_id)
        elif ws_message.type == "ping":
            await handle_ping_message(ws_message, connection_id)
        else:
            logger.warning(f"Unknown message type: {ws_message.type}")
            await connection_manager.send_personal_message(
                connection_id,
                {
                    "type": "error",
                    "message": f"Unknown message type: {ws_message.type}",
                    "timestamp": connection_manager.active_connections[connection_id].__dict__.get("connected_at", "")
                }
            )
    
    except Exception as e:
        logger.error(f"Error handling message type {ws_message.type}: {e}")
        raise


async def handle_chat_message(
    ws_message: WebSocketMessageSchema,
    user_id: str,
    user_role: str,
    connection_id: str
):
    """Handle chat messages - save to DB and broadcast"""
    if not ws_message.content:
        raise ValueError("Chat message content is required")

    # Get ticket to get the MongoDB _id
    ticket = await ticket_service.get_ticket_by_id_with_role(
        ws_message.ticket_id, user_id, UserRole(user_role)
    )
    if not ticket:
        raise ValueError("Ticket not found or access denied")

    # Convert user role to MessageRole
    message_role = MessageRole(user_role)
    message_type = ws_message.message_type or MessageType.USER_MESSAGE

    # Save message to database using ticket's MongoDB _id
    saved_message = await message_service.save_message(
        ticket_id=str(ticket._id),  # Use MongoDB _id, not ticket_id string
        sender_id=user_id,
        sender_role=message_role,
        content=ws_message.content,
        message_type=message_type,
        isAI=ws_message.isAI or False,
        feedback=ws_message.feedback or MessageFeedback.NONE
    )
    
    # Prepare broadcast message
    broadcast_data = {
        "type": "new_message",
        "message": {
            "id": str(saved_message._id),
            "ticket_id": ws_message.ticket_id,
            "sender_id": user_id,
            "sender_role": user_role,
            "message_type": message_type.value,
            "content": ws_message.content,
            "isAI": ws_message.isAI or False,
            "feedback": (ws_message.feedback or MessageFeedback.NONE).value,
            "timestamp": saved_message.timestamp.isoformat()
        }
    }
    
    # Broadcast to all users in the ticket room
    await connection_manager.broadcast_to_ticket(
        ws_message.ticket_id,
        broadcast_data
    )
    
    logger.info(f"Chat message saved and broadcasted - Ticket: {ws_message.ticket_id}")

    # Fire webhook for message sent
    try:
        webhook_success = await fire_message_sent_webhook(saved_message)
        if webhook_success:
            logger.debug(f"Message sent webhook fired successfully - Message: {saved_message._id}")
        else:
            logger.warning(f"Message sent webhook failed - Message: {saved_message._id}")
    except Exception as e:
        logger.error(f"Error firing message sent webhook: {e}")


async def handle_typing_indicator(
    ws_message: WebSocketMessageSchema,
    user_id: str,
    connection_id: str
):
    """Handle typing indicators"""
    typing_data = {
        "type": "typing",
        "ticket_id": ws_message.ticket_id,
        "user_id": user_id,
        "timestamp": connection_manager.active_connections[connection_id].__dict__.get("connected_at", "")
    }
    
    # Broadcast typing indicator to other users in the room
    await connection_manager.broadcast_to_ticket(
        ws_message.ticket_id,
        typing_data,
        exclude_user_id=user_id
    )


async def handle_ping_message(ws_message: WebSocketMessageSchema, connection_id: str):
    """Handle ping messages for connection health check"""
    pong_data = {
        "type": "pong",
        "ticket_id": ws_message.ticket_id,
        "timestamp": connection_manager.active_connections[connection_id].__dict__.get("connected_at", "")
    }
    
    await connection_manager.send_personal_message(connection_id, pong_data)
