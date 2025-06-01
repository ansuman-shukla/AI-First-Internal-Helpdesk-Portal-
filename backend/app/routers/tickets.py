from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List
from app.schemas.ticket import (
    TicketCreateSchema,
    TicketUpdateSchema,
    TicketSchema,
    TicketUserInfo,
    TicketStatus,
    TicketDepartment,
)
from app.schemas.message import (
    MessageCreateSchema,
    MessageSchema,
    MessageFeedback,
    MessageRole,
    MessageType
)
from app.services.ticket_service import TicketService
from app.services.message_service import MessageService
from app.routers.auth import get_current_user
from app.core.auth import require_admin
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])
ticket_service = TicketService()
message_service = MessageService()


@router.post("/", response_model=TicketSchema, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreateSchema, current_user: dict = Depends(get_current_user)
):
    """
    Create a new ticket

    - **title**: Ticket title (required, max 200 chars)
    - **description**: Ticket description (required, max 2000 chars)
    - **urgency**: Ticket urgency level (optional, defaults to "medium")

    Sets status = "open", created_at, updated_at, misuse_flag=false automatically.
    """
    logger.info(f"Creating ticket for user {current_user['user_id']}")

    try:
        # Create ticket using service
        ticket_model = await ticket_service.create_ticket(
            ticket_data, current_user["user_id"]
        )

        # Convert to response schema
        ticket_response = TicketSchema(
            id=str(ticket_model._id),
            ticket_id=ticket_model.ticket_id,
            title=ticket_model.title,
            description=ticket_model.description,
            urgency=ticket_model.urgency,
            status=ticket_model.status,
            department=ticket_model.department,
            assignee_id=(
                str(ticket_model.assignee_id) if ticket_model.assignee_id else None
            ),
            user_id=str(ticket_model.user_id),
            created_at=ticket_model.created_at,
            updated_at=ticket_model.updated_at,
            closed_at=ticket_model.closed_at,
            misuse_flag=ticket_model.misuse_flag,
            feedback=ticket_model.feedback,
        )

        logger.info(f"Successfully created ticket {ticket_model.ticket_id}")
        return ticket_response

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"Validation error creating ticket: {error_message}")

        # Handle content flagged errors specially
        if error_message.startswith("CONTENT_FLAGGED:"):
            # Parse the error message: CONTENT_FLAGGED:content_type:user_message
            parts = error_message.split(":", 2)
            if len(parts) == 3:
                content_type = parts[1]  # profanity, spam, inappropriate
                user_message = parts[2]

                # Return a 422 status with detailed error info for frontend
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error_type": "content_flagged",
                        "content_type": content_type,
                        "message": user_message,
                        "title": ticket_data.title,
                        "description": ticket_data.description
                    }
                )

        # Handle other validation errors
        if "rate limit" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_message
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
    except Exception as e:
        logger.error(f"Unexpected error creating ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/", response_model=dict)
async def get_tickets(
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    department_filter: Optional[TicketDepartment] = Query(None, alias="department"),
    search: Optional[str] = Query(None, description="Search in ticket title and description"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Number of tickets per page"),
    current_user: dict = Depends(get_current_user),
):
    """
    Query tickets with role-based access control and optional filters

    - **Users**: Can only see their own tickets
    - **IT Agents**: Can see IT department tickets and tickets assigned to them
    - **HR Agents**: Can see HR department tickets and tickets assigned to them
    - **Admins**: Can see all tickets
    - **status**: Filter by ticket status (optional)
    - **department**: Filter by department (optional)
    - **search**: Search in ticket title and description (optional)
    - **page**: Page number (default: 1)
    - **limit**: Number of tickets per page (default: 10, max: 100)

    Returns tickets with pagination information.
    """
    from app.schemas.user import UserRole

    user_role = UserRole(current_user["role"])
    logger.info(
        f"Getting tickets for user {current_user['user_id']} with role {user_role.value}"
    )
    logger.info(
        f"Filters - status: {status_filter}, department: {department_filter}, search: {search}, page: {page}, limit: {limit}"
    )

    try:
        # Get tickets using role-based service method
        result = await ticket_service.get_tickets(
            user_id=current_user["user_id"],
            user_role=user_role,
            status=status_filter,
            department=department_filter,
            search=search,
            page=page,
            limit=limit,
        )

        # Convert tickets to response schemas
        tickets_response = []
        for ticket_model in result["tickets"]:
            # Create user_info if available
            user_info = None
            if hasattr(ticket_model, 'user_info') and ticket_model.user_info:
                user_info = TicketUserInfo(**ticket_model.user_info)

            ticket_schema = TicketSchema(
                id=str(ticket_model._id),
                ticket_id=ticket_model.ticket_id,
                title=ticket_model.title,
                description=ticket_model.description,
                urgency=ticket_model.urgency,
                status=ticket_model.status,
                department=ticket_model.department,
                assignee_id=(
                    str(ticket_model.assignee_id) if ticket_model.assignee_id else None
                ),
                user_id=str(ticket_model.user_id),
                user_info=user_info,
                created_at=ticket_model.created_at,
                updated_at=ticket_model.updated_at,
                closed_at=ticket_model.closed_at,
                misuse_flag=ticket_model.misuse_flag,
                feedback=ticket_model.feedback,
            )
            tickets_response.append(ticket_schema)

        response = {
            "tickets": tickets_response,
            "total_count": result["total_count"],
            "page": result["page"],
            "limit": result["limit"],
            "total_pages": result["total_pages"],
        }

        logger.info(
            f"Successfully retrieved {len(tickets_response)} tickets for user {current_user['user_id']} with role {user_role.value}"
        )
        return response

    except Exception as e:
        logger.error(
            f"Error getting tickets for user {current_user['user_id']} with role {user_role.value}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/{ticket_id}", response_model=TicketSchema)
async def get_ticket_by_id(
    ticket_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get a single ticket by ID with role-based access control

    Returns ticket details. Message retrieval will be implemented in Phase 4.
    - **Users**: Can only access their own tickets
    - **IT Agents**: Can access IT department tickets and tickets assigned to them
    - **HR Agents**: Can access HR department tickets and tickets assigned to them
    - **Admins**: Can access all tickets
    """
    from app.schemas.user import UserRole

    user_role = UserRole(current_user["role"])
    logger.info(
        f"Getting ticket {ticket_id} for user {current_user['user_id']} with role {user_role.value}"
    )

    try:
        # Get ticket using role-based service method
        ticket_model = await ticket_service.get_ticket_by_id_with_role(
            ticket_id=ticket_id, user_id=current_user["user_id"], user_role=user_role
        )

        if not ticket_model:
            # Check if ticket exists at all
            from app.core.database import get_database
            db = get_database()
            collection = db["tickets"]
            ticket_exists = await collection.find_one({"ticket_id": ticket_id})

            if not ticket_exists:
                logger.warning(f"Ticket {ticket_id} does not exist in database")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ticket {ticket_id} not found"
                )
            else:
                logger.warning(
                    f"Ticket {ticket_id} exists but not accessible for user {current_user['user_id']} with role {user_role.value}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this ticket"
                )

        # Convert to response schema
        ticket_response = TicketSchema(
            id=str(ticket_model._id),
            ticket_id=ticket_model.ticket_id,
            title=ticket_model.title,
            description=ticket_model.description,
            urgency=ticket_model.urgency,
            status=ticket_model.status,
            department=ticket_model.department,
            assignee_id=(
                str(ticket_model.assignee_id) if ticket_model.assignee_id else None
            ),
            user_id=str(ticket_model.user_id),
            created_at=ticket_model.created_at,
            updated_at=ticket_model.updated_at,
            closed_at=ticket_model.closed_at,
            misuse_flag=ticket_model.misuse_flag,
            feedback=ticket_model.feedback,
        )

        logger.info(
            f"Successfully retrieved ticket {ticket_id} for user {current_user['user_id']} with role {user_role.value}"
        )
        return ticket_response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/{ticket_id}", response_model=TicketSchema)
async def update_ticket(
    ticket_id: str,
    update_data: TicketUpdateSchema,
    current_user: dict = Depends(get_current_user),
):
    """
    Update a ticket with role-based access control

    - **Users**: Can edit title, description, urgency if status = "open" and they own the ticket
    - **IT Agents**: Can update status, department, feedback, title, description, and urgency for IT tickets
    - **HR Agents**: Can update status, department, feedback, title, description, and urgency for HR tickets
    - **Admins**: Can update any ticket
    """
    from app.schemas.user import UserRole

    user_role = UserRole(current_user["role"])
    logger.info(f"Updating ticket {ticket_id} for user {current_user['user_id']} with role {user_role.value}")
    logger.info(f"Update data received: {update_data.model_dump()}")

    try:
        # Update ticket using service with role-based access
        updated_ticket = await ticket_service.update_ticket_with_role(
            ticket_id=ticket_id,
            user_id=current_user["user_id"],
            user_role=user_role,
            update_data=update_data,
        )

        if not updated_ticket:
            # Check if ticket exists at all
            from app.core.database import get_database
            db = get_database()
            collection = db["tickets"]
            ticket_exists = await collection.find_one({"ticket_id": ticket_id})

            if not ticket_exists:
                logger.warning(f"Ticket {ticket_id} does not exist in database")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ticket {ticket_id} not found"
                )
            else:
                logger.warning(
                    f"Ticket {ticket_id} exists but not accessible by user {current_user['user_id']} with role {user_role.value}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to edit this ticket"
                )

        # Convert to response schema
        ticket_response = TicketSchema(
            id=str(updated_ticket._id),
            ticket_id=updated_ticket.ticket_id,
            title=updated_ticket.title,
            description=updated_ticket.description,
            urgency=updated_ticket.urgency,
            status=updated_ticket.status,
            department=updated_ticket.department,
            assignee_id=(
                str(updated_ticket.assignee_id) if updated_ticket.assignee_id else None
            ),
            user_id=str(updated_ticket.user_id),
            created_at=updated_ticket.created_at,
            updated_at=updated_ticket.updated_at,
            closed_at=updated_ticket.closed_at,
            misuse_flag=updated_ticket.misuse_flag,
            feedback=updated_ticket.feedback,
        )

        logger.info(f"Successfully updated ticket {ticket_id}")
        logger.info(f"Returning updated ticket data: {ticket_response.model_dump()}")
        return ticket_response

    except ValueError as e:
        logger.warning(f"Validation error updating ticket {ticket_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Message endpoints for Phase 4

@router.get("/{ticket_id}/messages", response_model=dict)
async def get_ticket_messages(
    ticket_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=100, description="Number of messages per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get messages for a specific ticket with pagination

    - **Users**: Can only access messages for their own tickets
    - **IT Agents**: Can access messages for IT department tickets and tickets assigned to them
    - **HR Agents**: Can access messages for HR department tickets and tickets assigned to them
    - **Admins**: Can access messages for all tickets
    """
    from app.schemas.user import UserRole

    user_role = UserRole(current_user["role"])
    logger.info(f"Getting messages for ticket {ticket_id} by user {current_user['user_id']} with role {user_role.value}")

    try:
        # First verify ticket access using existing ticket service
        ticket_model = await ticket_service.get_ticket_by_id_with_role(
            ticket_id=ticket_id,
            user_id=current_user["user_id"],
            user_role=user_role
        )

        if not ticket_model:
            logger.warning(f"Ticket {ticket_id} not found or not accessible for user {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found or access denied"
            )

        # Calculate skip for pagination
        skip = (page - 1) * limit

        # Get messages using the ticket's MongoDB _id
        messages = await message_service.get_ticket_messages(
            ticket_id=str(ticket_model._id),  # Use MongoDB _id, not ticket_id string
            limit=limit,
            skip=skip,
            sort_order=1  # Oldest first
        )

        # Convert to response format
        messages_response = []
        for message in messages:
            message_dict = {
                "id": str(message._id),
                "ticket_id": str(message.ticket_id),
                "sender_id": str(message.sender_id),
                "sender_role": message.sender_role.value,
                "message_type": message.message_type.value,
                "content": message.content,
                "isAI": message.isAI,
                "feedback": message.feedback.value,
                "timestamp": message.timestamp.isoformat()
            }
            messages_response.append(message_dict)

        # Check if there are more messages
        total_messages = await message_service.get_message_count_for_ticket(str(ticket_model._id))
        has_more = (skip + len(messages)) < total_messages

        response = {
            "messages": messages_response,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_messages,
                "has_more": has_more
            }
        }

        logger.info(f"Successfully retrieved {len(messages)} messages for ticket {ticket_id}")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting messages for ticket {ticket_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{ticket_id}/messages", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_message(
    ticket_id: str,
    message_data: MessageCreateSchema,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a message in a ticket

    - **Users**: Can send messages in their own tickets
    - **IT Agents**: Can send messages in IT department tickets and tickets assigned to them
    - **HR Agents**: Can send messages in HR department tickets and tickets assigned to them
    - **Admins**: Can send messages in all tickets
    """
    from app.schemas.user import UserRole

    user_role = UserRole(current_user["role"])
    logger.info(f"Sending message to ticket {ticket_id} by user {current_user['user_id']} with role {user_role.value}")

    try:
        # First verify ticket access
        ticket_model = await ticket_service.get_ticket_by_id_with_role(
            ticket_id=ticket_id,
            user_id=current_user["user_id"],
            user_role=user_role
        )

        if not ticket_model:
            logger.warning(f"Ticket {ticket_id} not found or not accessible for user {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found or access denied"
            )

        # Convert user role to message role
        message_role = MessageRole(user_role.value)

        # Save message using the ticket's MongoDB _id
        saved_message = await message_service.save_message(
            ticket_id=str(ticket_model._id),  # Use MongoDB _id, not ticket_id string
            sender_id=current_user["user_id"],
            sender_role=message_role,
            content=message_data.content,
            message_type=message_data.message_type,
            isAI=message_data.isAI,
            feedback=message_data.feedback
        )

        # Convert to response format
        message_response = {
            "id": str(saved_message._id),
            "ticket_id": ticket_id,  # Use the original ticket_id string for consistency
            "sender_id": str(saved_message.sender_id),
            "sender_role": saved_message.sender_role.value,
            "message_type": saved_message.message_type.value,
            "content": saved_message.content,
            "isAI": saved_message.isAI,
            "feedback": saved_message.feedback.value,
            "timestamp": saved_message.timestamp.isoformat()
        }

        # Broadcast message to WebSocket clients
        try:
            from app.services.websocket_manager import connection_manager

            broadcast_data = {
                "type": "new_message",
                "message": message_response
            }

            await connection_manager.broadcast_to_ticket(ticket_id, broadcast_data)
            logger.debug(f"Broadcasted HTTP message to WebSocket clients for ticket {ticket_id}")

        except Exception as broadcast_error:
            logger.warning(f"Failed to broadcast HTTP message to WebSocket clients: {broadcast_error}")

        # Fire webhook for message sent
        try:
            from app.services.webhook_service import fire_message_sent_webhook

            webhook_success = await fire_message_sent_webhook(saved_message)
            if webhook_success:
                logger.debug(f"Message sent webhook fired successfully - Message: {saved_message._id}")
            else:
                logger.warning(f"Message sent webhook failed - Message: {saved_message._id}")
        except Exception as webhook_error:
            logger.warning(f"Error firing message sent webhook: {webhook_error}")

        logger.info(f"Successfully sent message to ticket {ticket_id}")
        return {"message": message_response}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error sending message to ticket {ticket_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{ticket_id}/messages/{message_id}/feedback", response_model=dict)
async def update_message_feedback(
    ticket_id: str,
    message_id: str,
    feedback_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update feedback for a specific message

    - **Users**: Can update feedback for messages in their own tickets
    - **IT Agents**: Can update feedback for messages in IT department tickets and tickets assigned to them
    - **HR Agents**: Can update feedback for messages in HR department tickets and tickets assigned to them
    - **Admins**: Can update feedback for messages in all tickets
    """
    from app.schemas.user import UserRole

    user_role = UserRole(current_user["role"])
    logger.info(f"Updating feedback for message {message_id} in ticket {ticket_id} by user {current_user['user_id']}")

    try:
        # First verify ticket access
        ticket_model = await ticket_service.get_ticket_by_id_with_role(
            ticket_id=ticket_id,
            user_id=current_user["user_id"],
            user_role=user_role
        )

        if not ticket_model:
            logger.warning(f"Ticket {ticket_id} not found or not accessible for user {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found or access denied"
            )

        # Validate feedback value
        feedback_value = feedback_data.get("feedback")
        if not feedback_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback value is required"
            )

        try:
            feedback = MessageFeedback(feedback_value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid feedback value. Must be one of: {[f.value for f in MessageFeedback]}"
            )

        # Update message feedback
        success = await message_service.update_message_feedback(message_id, feedback)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        logger.info(f"Successfully updated feedback for message {message_id} to {feedback.value}")
        return {"message": "Feedback updated successfully", "feedback": feedback.value}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating feedback for message {message_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: str,
    current_user: dict = Depends(require_admin)
):
    """
    Delete a ticket (Admin only)

    Only administrators can delete tickets. This operation is irreversible.

    Args:
        ticket_id: The ID of the ticket to delete
        current_user: Current authenticated admin user

    Returns:
        204 No Content on successful deletion

    Raises:
        403 Forbidden: If user is not an admin
        404 Not Found: If ticket doesn't exist
        500 Internal Server Error: If deletion fails
    """
    logger.info(f"Admin {current_user['user_id']} attempting to delete ticket {ticket_id}")

    try:
        # Attempt to delete the ticket
        success = await ticket_service.delete_ticket(ticket_id)

        if not success:
            logger.warning(f"Ticket {ticket_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        logger.info(f"Successfully deleted ticket {ticket_id} by admin {current_user['user_id']}")
        return  # 204 No Content response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting ticket {ticket_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
