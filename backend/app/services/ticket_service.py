from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from bson import ObjectId
from app.core.database import get_database
from app.models.ticket import TicketModel
from app.schemas.ticket import (
    TicketCreateSchema,
    TicketUpdateSchema,
    TicketStatus,
    TicketDepartment,
)
from app.schemas.user import UserRole
from app.services.ai.hsa import check_harmful, check_harmful_detailed
from app.services.ai.routing import assign_department
from app.services.webhook_service import fire_ticket_created_webhook
from app.services.user_service import user_service
from app.services.user_violation_service import user_violation_service
from app.models.user_violation import (
    UserViolationCreateSchema,
    ViolationType,
    ViolationSeverity
)
import logging

logger = logging.getLogger(__name__)


class TicketService:
    """Service for ticket database operations"""

    def __init__(self):
        self.collection_name = "tickets"

    async def create_ticket(
        self, ticket_data: TicketCreateSchema, user_id: str
    ) -> TicketModel:
        """
        Create a new ticket with AI-powered HSA filtering and department routing

        Args:
            ticket_data: Ticket creation data
            user_id: ID of the user creating the ticket

        Returns:
            Created ticket model

        Raises:
            ValueError: If rate limit exceeded or validation fails
        """
        logger.info(f"Creating ticket for user {user_id}")

        # Check rate limiting (5 tickets per 24 hours) - DISABLED FOR TESTING
        # await self._check_rate_limit(user_id)

        # Step 1: HSA (Harmful/Spam Analysis) check
        logger.info(f"Running HSA check for ticket: '{ticket_data.title[:50]}...'")
        hsa_result = check_harmful_detailed(ticket_data.title, ticket_data.description)

        if hsa_result["is_harmful"]:
            # If harmful content detected, record violation and return error with details for user to fix
            logger.warning(f"Harmful content detected in ticket: '{ticket_data.title[:50]}...' - {hsa_result['reason']}")

            # Determine the type of harmful content for user-friendly message
            reason_lower = hsa_result['reason'].lower()
            if any(word in reason_lower for word in ['profanity', 'inappropriate language', 'offensive']):
                content_type = "profanity"
                violation_type = ViolationType.PROFANITY
                user_message = "Your ticket contains inappropriate language or profanity. Please revise your content and try again."
            elif any(word in reason_lower for word in ['spam', 'promotional', 'marketing', 'advertisement']):
                content_type = "spam"
                violation_type = ViolationType.SPAM
                user_message = "Your ticket appears to contain spam or promotional content. Please ensure your request is work-related and try again."
            else:
                content_type = "inappropriate"
                violation_type = ViolationType.INAPPROPRIATE
                user_message = "Your ticket content is not appropriate for the helpdesk system. Please revise and try again."

            # Determine severity based on confidence and content type
            confidence = hsa_result.get('confidence', 0.5)
            if confidence >= 0.9 or violation_type == ViolationType.PROFANITY:
                severity = ViolationSeverity.HIGH
            elif confidence >= 0.7:
                severity = ViolationSeverity.MEDIUM
            else:
                severity = ViolationSeverity.LOW

            # Record the violation attempt
            try:
                violation_data = UserViolationCreateSchema(
                    user_id=user_id,
                    violation_type=violation_type,
                    severity=severity,
                    attempted_title=ticket_data.title,
                    attempted_description=ticket_data.description,
                    detection_reason=hsa_result['reason'],
                    detection_confidence=confidence
                )

                violation_id = await user_violation_service.record_violation(user_id, violation_data)
                logger.info(f"Recorded violation {violation_id} for user {user_id} attempting inappropriate content")

            except Exception as violation_error:
                logger.error(f"Failed to record violation for user {user_id}: {str(violation_error)}")
                # Don't fail the HSA check if violation recording fails

            # Raise a specific exception that the API can catch and return to frontend
            raise ValueError(f"CONTENT_FLAGGED:{content_type}:{user_message}")

        # Initialize ticket with base values (only reached if content is safe)
        ticket_status = TicketStatus.OPEN
        ticket_department = None
        misuse_flag = False

        # Step 2: Auto-routing for safe content
        logger.info(f"Running department routing for ticket: '{ticket_data.title[:50]}...'")
        assigned_dept = assign_department(ticket_data.title, ticket_data.description)

        # Convert string to enum
        if assigned_dept == "IT":
            ticket_department = TicketDepartment.IT
        elif assigned_dept == "HR":
            ticket_department = TicketDepartment.HR

        # Set status to ASSIGNED for routed tickets
        ticket_status = TicketStatus.ASSIGNED
        logger.info(f"Ticket routed to {assigned_dept} department")

        db = get_database()
        collection = db[self.collection_name]

        # Create ticket model with AI-determined values
        ticket_model = TicketModel(
            title=ticket_data.title,
            description=ticket_data.description,
            urgency=ticket_data.urgency,
            user_id=ObjectId(user_id),
            status=ticket_status,
            department=ticket_department,
            misuse_flag=misuse_flag,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        try:
            # Insert ticket into database
            result = await collection.insert_one(ticket_model.to_dict())
            ticket_model._id = result.inserted_id

            logger.info(
                f"Successfully created ticket {ticket_model.ticket_id} for user {user_id} "
                f"(status: {ticket_status.value}, department: {ticket_department.value if ticket_department else None}, "
                f"misuse_flag: {misuse_flag})"
            )

            # Fire webhook for ticket creation to trigger notifications
            try:
                webhook_payload = {
                    "ticket_id": ticket_model.ticket_id,
                    "user_id": user_id,
                    "title": ticket_model.title,
                    "description": ticket_model.description,
                    "urgency": ticket_model.urgency.value,
                    "status": ticket_model.status.value,
                    "department": ticket_model.department.value if ticket_model.department else None,
                    "misuse_flag": ticket_model.misuse_flag,
                    "created_at": ticket_model.created_at.isoformat()
                }

                webhook_success = await fire_ticket_created_webhook(webhook_payload)
                if webhook_success:
                    logger.info(f"Successfully fired ticket creation webhook for ticket {ticket_model.ticket_id}")
                else:
                    logger.warning(f"Failed to fire ticket creation webhook for ticket {ticket_model.ticket_id}")

            except Exception as webhook_error:
                logger.error(f"Error firing ticket creation webhook for ticket {ticket_model.ticket_id}: {str(webhook_error)}")
                # Don't fail ticket creation if webhook fails

            return ticket_model

        except Exception as e:
            logger.error(f"Failed to create ticket for user {user_id}: {str(e)}")
            raise ValueError(f"Failed to create ticket: {str(e)}")

    async def _check_rate_limit(self, user_id: str) -> None:
        """
        Check if user has exceeded rate limit of 5 tickets per 24 hours

        Args:
            user_id: User ID to check

        Raises:
            ValueError: If rate limit exceeded
        """
        logger.debug(f"Checking rate limit for user {user_id}")

        db = get_database()
        collection = db[self.collection_name]

        # Calculate 24 hours ago
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)

        # Count tickets created by user in last 24 hours
        ticket_count = await collection.count_documents(
            {
                "user_id": ObjectId(user_id),
                "created_at": {"$gte": twenty_four_hours_ago},
            }
        )

        logger.debug(
            f"User {user_id} has created {ticket_count} tickets in last 24 hours"
        )

        if ticket_count >= 5:
            logger.warning(
                f"Rate limit exceeded for user {user_id}: {ticket_count} tickets in 24h"
            )
            raise ValueError("Rate limit exceeded: Maximum 5 tickets per 24 hours")

    async def get_tickets_by_user(
        self,
        user_id: str,
        status: Optional[TicketStatus] = None,
        department: Optional[TicketDepartment] = None,
        page: int = 1,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Get tickets for a specific user with optional filters and pagination

        Args:
            user_id: User ID to filter by
            status: Optional status filter
            department: Optional department filter
            page: Page number (1-based)
            limit: Number of tickets per page

        Returns:
            Dictionary with tickets, total count, and pagination info
        """
        logger.info(
            f"Getting tickets for user {user_id} with filters: status={status}, department={department}"
        )

        db = get_database()
        collection = db[self.collection_name]

        # Build query
        query = {"user_id": ObjectId(user_id)}

        if status:
            query["status"] = status.value
        if department:
            query["department"] = department.value

        # Calculate pagination
        skip = (page - 1) * limit

        try:
            # Get total count
            total_count = await collection.count_documents(query)

            # Get tickets with pagination
            cursor = (
                collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            )
            tickets_data = await cursor.to_list(length=limit)

            # Convert to ticket models
            tickets = [
                TicketModel.from_dict(ticket_data) for ticket_data in tickets_data
            ]

            logger.info(
                f"Retrieved {len(tickets)} tickets for user {user_id} (page {page})"
            )

            return {
                "tickets": tickets,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": (total_count + limit - 1) // limit,
            }

        except Exception as e:
            logger.error(f"Failed to get tickets for user {user_id}: {str(e)}")
            raise ValueError(f"Failed to retrieve tickets: {str(e)}")

    async def get_ticket_by_id(
        self, ticket_id: str, user_id: str
    ) -> Optional[TicketModel]:
        """
        Get a single ticket by ID, ensuring user has access

        Args:
            ticket_id: Ticket ID to retrieve
            user_id: User ID requesting the ticket

        Returns:
            Ticket model if found and accessible, None otherwise
        """
        logger.info(f"Getting ticket {ticket_id} for user {user_id}")

        db = get_database()
        collection = db[self.collection_name]

        try:
            # Find ticket by ticket_id and user_id
            ticket_data = await collection.find_one(
                {"ticket_id": ticket_id, "user_id": ObjectId(user_id)}
            )

            if not ticket_data:
                logger.warning(
                    f"Ticket {ticket_id} not found or not accessible by user {user_id}"
                )
                return None

            ticket = TicketModel.from_dict(ticket_data)
            logger.info(f"Successfully retrieved ticket {ticket_id} for user {user_id}")
            return ticket

        except Exception as e:
            logger.error(
                f"Failed to get ticket {ticket_id} for user {user_id}: {str(e)}"
            )
            raise ValueError(f"Failed to retrieve ticket: {str(e)}")

    async def update_ticket(
        self, ticket_id: str, user_id: str, update_data: TicketUpdateSchema
    ) -> Optional[TicketModel]:
        """
        Update a ticket with proper permission checks

        Args:
            ticket_id: Ticket ID to update
            user_id: User ID requesting the update
            update_data: Update data

        Returns:
            Updated ticket model if successful, None if not found/accessible

        Raises:
            ValueError: If update is not allowed or validation fails
        """
        logger.info(f"Updating ticket {ticket_id} for user {user_id}")

        db = get_database()
        collection = db[self.collection_name]

        try:
            # First, get the current ticket
            current_ticket_data = await collection.find_one(
                {"ticket_id": ticket_id, "user_id": ObjectId(user_id)}
            )

            if not current_ticket_data:
                logger.warning(
                    f"Ticket {ticket_id} not found or not accessible by user {user_id}"
                )
                return None

            current_ticket = TicketModel.from_dict(current_ticket_data)

            # Check if ticket can be edited (only if status is "open")
            if current_ticket.status != TicketStatus.OPEN:
                logger.warning(
                    f"Cannot edit ticket {ticket_id}: status is {current_ticket.status}, must be 'open'"
                )
                raise ValueError("Can only edit tickets with status 'open'")

            # Build update document
            update_doc = {"updated_at": datetime.now(timezone.utc)}

            # Only allow updating title, description, and urgency for users
            if update_data.title is not None:
                update_doc["title"] = update_data.title
            if update_data.description is not None:
                update_doc["description"] = update_data.description
            if update_data.urgency is not None:
                update_doc["urgency"] = update_data.urgency.value

            # Perform update
            result = await collection.update_one(
                {"ticket_id": ticket_id, "user_id": ObjectId(user_id)},
                {"$set": update_doc},
            )

            if result.modified_count == 0:
                logger.warning(f"No changes made to ticket {ticket_id}")
                return current_ticket

            # Get updated ticket
            updated_ticket_data = await collection.find_one(
                {"ticket_id": ticket_id, "user_id": ObjectId(user_id)}
            )

            updated_ticket = TicketModel.from_dict(updated_ticket_data)
            logger.info(f"Successfully updated ticket {ticket_id} for user {user_id}")
            return updated_ticket

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(
                f"Failed to update ticket {ticket_id} for user {user_id}: {str(e)}"
            )
            raise ValueError(f"Failed to update ticket: {str(e)}")

    async def get_tickets(
        self,
        user_id: str,
        user_role: UserRole,
        status: Optional[TicketStatus] = None,
        department: Optional[TicketDepartment] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Get tickets with role-based access control

        Args:
            user_id: User ID making the request
            user_role: Role of the user (user, it_agent, hr_agent, admin)
            status: Optional status filter
            department: Optional department filter
            search: Optional search query for title and description
            page: Page number (1-based)
            limit: Number of tickets per page

        Returns:
            Dictionary with tickets, total count, and pagination info
        """
        logger.info(f"Getting tickets for user {user_id} with role {user_role.value}")

        db = get_database()
        collection = db[self.collection_name]

        # Build base conditions list for $and query
        conditions = []

        # Add role-based access control
        if user_role == UserRole.USER:
            # Users can only see their own tickets
            conditions.append({"user_id": ObjectId(user_id)})
        elif user_role == UserRole.IT_AGENT:
            # IT agents can see tickets assigned to them or in IT department
            role_condition = {
                "$or": [
                    {"assignee_id": ObjectId(user_id)},
                    {"department": TicketDepartment.IT.value},
                ]
            }
            conditions.append(role_condition)
        elif user_role == UserRole.HR_AGENT:
            # HR agents can see tickets assigned to them or in HR department
            role_condition = {
                "$or": [
                    {"assignee_id": ObjectId(user_id)},
                    {"department": TicketDepartment.HR.value},
                ]
            }
            conditions.append(role_condition)
        elif user_role == UserRole.ADMIN:
            # Admins can see all tickets - no additional conditions needed
            pass
        else:
            logger.warning(f"Unknown user role: {user_role}")
            raise ValueError(f"Invalid user role: {user_role}")

        # Add optional filters as separate conditions
        if status:
            conditions.append({"status": status.value})
        if department:
            conditions.append({"department": department.value})
        if search:
            # Add text search using regex for title and description
            search_regex = {"$regex": search, "$options": "i"}  # Case-insensitive search
            search_condition = {
                "$or": [
                    {"title": search_regex},
                    {"description": search_regex}
                ]
            }
            conditions.append(search_condition)

        # Build final query
        if conditions:
            if len(conditions) == 1:
                query = conditions[0]
            else:
                query = {"$and": conditions}
        else:
            query = {}  # No conditions for admin with no filters

        # Log the final query for debugging
        logger.info(f"Final MongoDB query: {query}")
        logger.info(f"Query conditions count: {len(conditions)}")

        # Calculate pagination
        skip = (page - 1) * limit

        try:
            # Get total count
            total_count = await collection.count_documents(query)
            logger.info(f"Total documents matching query: {total_count}")

            # Get tickets with pagination
            cursor = (
                collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            )
            tickets_data = await cursor.to_list(length=limit)

            # Convert to ticket models
            tickets = [
                TicketModel.from_dict(ticket_data) for ticket_data in tickets_data
            ]

            # For agents and admins, populate user information
            tickets_with_user_info = []
            if user_role in [UserRole.IT_AGENT, UserRole.HR_AGENT, UserRole.ADMIN]:
                # Get unique user IDs from tickets
                user_ids = list(set(str(ticket.user_id) for ticket in tickets))

                # Fetch user information for all unique user IDs
                user_info_map = {}
                for uid in user_ids:
                    try:
                        user_model = await user_service.get_user_by_id(uid)
                        if user_model:
                            user_info_map[uid] = {
                                "user_id": uid,
                                "username": user_model.username,
                                "email": user_model.email
                            }
                    except Exception as e:
                        logger.warning(f"Failed to get user info for {uid}: {e}")
                        user_info_map[uid] = {
                            "user_id": uid,
                            "username": "Unknown User",
                            "email": "unknown@example.com"
                        }

                # Add user info to each ticket
                for ticket in tickets:
                    ticket.user_info = user_info_map.get(str(ticket.user_id))
                    tickets_with_user_info.append(ticket)
            else:
                tickets_with_user_info = tickets

            logger.info(
                f"Retrieved {len(tickets_with_user_info)} tickets for user {user_id} with role {user_role.value} (page {page})"
            )

            return {
                "tickets": tickets_with_user_info,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": (total_count + limit - 1) // limit,
            }

        except Exception as e:
            logger.error(
                f"Failed to get tickets for user {user_id} with role {user_role.value}: {str(e)}"
            )
            raise ValueError(f"Failed to retrieve tickets: {str(e)}")

    async def get_ticket_participants(self, ticket_id: str) -> list[str]:
        """
        Get all user IDs involved in a ticket (creator and assignee)

        Args:
            ticket_id: Ticket ID to get participants for

        Returns:
            List of user IDs (as strings) involved in the ticket
        """
        logger.debug(f"Getting participants for ticket {ticket_id}")

        db = get_database()
        collection = db[self.collection_name]

        try:
            # Find ticket by ticket_id
            ticket_data = await collection.find_one({"ticket_id": ticket_id})

            if not ticket_data:
                logger.warning(f"Ticket {ticket_id} not found for participants lookup")
                return []

            participants = []

            # Add ticket creator
            if ticket_data.get("user_id"):
                participants.append(str(ticket_data["user_id"]))

            # Add assigned agent if exists
            if ticket_data.get("assignee_id"):
                participants.append(str(ticket_data["assignee_id"]))

            # Remove duplicates (in case creator is also assignee)
            participants = list(set(participants))

            logger.debug(f"Found {len(participants)} participants for ticket {ticket_id}: {participants}")
            return participants

        except Exception as e:
            logger.error(f"Error getting participants for ticket {ticket_id}: {str(e)}")
            return []

    async def get_ticket_by_id_with_role(
        self, ticket_id: str, user_id: str, user_role: UserRole
    ) -> Optional[TicketModel]:
        """
        Get a single ticket by ID with role-based access control

        Args:
            ticket_id: Ticket ID to retrieve (can be ticket_id string or MongoDB _id)
            user_id: User ID making the request
            user_role: Role of the user (user, it_agent, hr_agent, admin)

        Returns:
            Ticket model if found and accessible, None otherwise
        """
        logger.info(
            f"Getting ticket {ticket_id} for user {user_id} with role {user_role.value}"
        )

        db = get_database()
        collection = db[self.collection_name]

        try:
            # Try to find by ticket_id first, then by _id if it's a valid ObjectId
            query_conditions = [{"ticket_id": ticket_id}]

            # If ticket_id looks like an ObjectId, also search by _id
            if ObjectId.is_valid(ticket_id):
                query_conditions.append({"_id": ObjectId(ticket_id)})

            # Find ticket using OR condition for ticket_id or _id
            ticket_data = await collection.find_one({"$or": query_conditions})

            if not ticket_data:
                logger.warning(f"Ticket {ticket_id} not found")
                return None

            # Check access permissions based on user role
            if user_role == UserRole.USER:
                # Users can only access their own tickets
                if ticket_data["user_id"] != ObjectId(user_id):
                    logger.warning(
                        f"User {user_id} attempted to access ticket {ticket_id} they don't own"
                    )
                    return None
            elif user_role == UserRole.IT_AGENT:
                # IT agents can access tickets assigned to them or in IT department
                if (
                    ticket_data.get("assignee_id") != ObjectId(user_id)
                    and ticket_data.get("department") != TicketDepartment.IT.value
                ):
                    logger.warning(
                        f"IT agent {user_id} attempted to access ticket {ticket_id} outside their scope"
                    )
                    return None
            elif user_role == UserRole.HR_AGENT:
                # HR agents can access tickets assigned to them or in HR department
                if (
                    ticket_data.get("assignee_id") != ObjectId(user_id)
                    and ticket_data.get("department") != TicketDepartment.HR.value
                ):
                    logger.warning(
                        f"HR agent {user_id} attempted to access ticket {ticket_id} outside their scope"
                    )
                    return None
            elif user_role == UserRole.ADMIN:
                # Admins can access all tickets
                pass
            else:
                logger.warning(f"Unknown user role: {user_role}")
                raise ValueError(f"Invalid user role: {user_role}")

            ticket = TicketModel.from_dict(ticket_data)
            logger.info(
                f"Successfully retrieved ticket {ticket_id} for user {user_id} with role {user_role.value}"
            )
            return ticket

        except Exception as e:
            logger.error(
                f"Failed to get ticket {ticket_id} for user {user_id} with role {user_role.value}: {str(e)}"
            )
            raise ValueError(f"Failed to retrieve ticket: {str(e)}")

    async def update_ticket_with_role(
        self,
        ticket_id: str,
        user_id: str,
        user_role: UserRole,
        update_data: TicketUpdateSchema,
    ) -> Optional[TicketModel]:
        """
        Update a ticket with role-based permission checks

        Args:
            ticket_id: Ticket ID to update
            user_id: User ID requesting the update
            user_role: Role of the user (user, it_agent, hr_agent, admin)
            update_data: Update data

        Returns:
            Updated ticket model if successful, None if not found/accessible

        Raises:
            ValueError: If update is not allowed or validation fails
        """
        logger.info(
            f"Updating ticket {ticket_id} for user {user_id} with role {user_role.value}"
        )
        logger.info(f"Update data: {update_data.model_dump()}")

        db = get_database()
        collection = db[self.collection_name]

        try:
            # First, get the current ticket with role-based access
            current_ticket = await self.get_ticket_by_id_with_role(
                ticket_id, user_id, user_role
            )

            if not current_ticket:
                logger.warning(
                    f"Ticket {ticket_id} not found or not accessible by user {user_id} with role {user_role.value}"
                )
                return None

            # Build update document based on user role and current ticket status
            update_doc = {"updated_at": datetime.now(timezone.utc)}

            # Role-based update permissions
            if user_role == UserRole.USER:
                # Users can only edit title, description, urgency if status is "open" and they own the ticket
                if current_ticket.status != TicketStatus.OPEN:
                    logger.warning(
                        f"User {user_id} cannot edit ticket {ticket_id}: status is {current_ticket.status}, must be 'open'"
                    )
                    raise ValueError("Can only edit tickets with status 'open'")

                # Only allow updating title, description, and urgency for users
                if update_data.title is not None:
                    update_doc["title"] = update_data.title
                if update_data.description is not None:
                    update_doc["description"] = update_data.description
                if update_data.urgency is not None:
                    update_doc["urgency"] = update_data.urgency.value

            elif user_role in [UserRole.IT_AGENT, UserRole.HR_AGENT]:
                # Agents can update status, department, feedback, title, and description
                if update_data.status is not None:
                    # Validate status transitions
                    if not self._is_valid_status_transition(
                        current_ticket.status, update_data.status
                    ):
                        raise ValueError(
                            f"Invalid status transition from {current_ticket.status.value} to {update_data.status.value}"
                        )
                    update_doc["status"] = update_data.status.value

                    # Set closed_at when status changes to closed
                    if update_data.status == TicketStatus.CLOSED:
                        update_doc["closed_at"] = datetime.now(timezone.utc)

                # Allow agents to update title and description
                if update_data.title is not None:
                    update_doc["title"] = update_data.title
                if update_data.description is not None:
                    update_doc["description"] = update_data.description
                if update_data.urgency is not None:
                    update_doc["urgency"] = update_data.urgency.value

                # Agents can change department regardless of ticket status
                # This allows for correcting department assignments even after resolution
                if update_data.department is not None:
                    logger.info(f"Agent {user_id} updating department from '{current_ticket.department}' to '{update_data.department.value}' for ticket {ticket_id}")
                    update_doc["department"] = update_data.department.value

                if update_data.feedback is not None:
                    update_doc["feedback"] = update_data.feedback

            elif user_role == UserRole.ADMIN:
                # Admins can update any field
                if update_data.title is not None:
                    update_doc["title"] = update_data.title
                if update_data.description is not None:
                    update_doc["description"] = update_data.description
                if update_data.urgency is not None:
                    update_doc["urgency"] = update_data.urgency.value
                if update_data.status is not None:
                    if not self._is_valid_status_transition(
                        current_ticket.status, update_data.status
                    ):
                        raise ValueError(
                            f"Invalid status transition from {current_ticket.status.value} to {update_data.status.value}"
                        )
                    update_doc["status"] = update_data.status.value
                    if update_data.status == TicketStatus.CLOSED:
                        update_doc["closed_at"] = datetime.now(timezone.utc)
                if update_data.department is not None:
                    update_doc["department"] = update_data.department.value
                if update_data.assignee_id is not None:
                    update_doc["assignee_id"] = ObjectId(update_data.assignee_id)
                if update_data.feedback is not None:
                    update_doc["feedback"] = update_data.feedback

            # If no fields to update, return current ticket
            if len(update_doc) == 1:  # Only updated_at
                logger.info(f"No changes to apply to ticket {ticket_id}")
                return current_ticket

            logger.info(f"Applying updates to ticket {ticket_id}: {update_doc}")

            # Perform update using both ticket_id and _id for flexibility
            query = {"$or": [{"ticket_id": ticket_id}]}
            if ObjectId.is_valid(ticket_id):
                query["$or"].append({"_id": ObjectId(ticket_id)})

            result = await collection.update_one(query, {"$set": update_doc})

            if result.modified_count == 0:
                logger.warning(f"No changes made to ticket {ticket_id}")
                return current_ticket

            # Get updated ticket
            updated_ticket = await self.get_ticket_by_id_with_role(
                ticket_id, user_id, user_role
            )

            # Check if ticket was closed and trigger summarization
            if (update_data.status == TicketStatus.CLOSED and
                current_ticket.status != TicketStatus.CLOSED):
                logger.info(f"Ticket {ticket_id} was closed, triggering FAQ summarization")
                await self._trigger_ticket_summarization(updated_ticket)

            logger.info(
                f"Successfully updated ticket {ticket_id} for user {user_id} with role {user_role.value}"
            )
            return updated_ticket

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(
                f"Failed to update ticket {ticket_id} for user {user_id} with role {user_role.value}: {str(e)}"
            )
            raise ValueError(f"Failed to update ticket: {str(e)}")

    async def delete_ticket(self, ticket_id: str) -> bool:
        """
        Delete a ticket by ticket_id (Admin only operation)

        Args:
            ticket_id: The ticket ID to delete

        Returns:
            bool: True if ticket was deleted successfully, False if ticket not found

        Raises:
            Exception: If database operation fails
        """
        logger.info(f"Attempting to delete ticket {ticket_id}")

        try:
            db = get_database()
            tickets_collection = db[self.collection_name]
            messages_collection = db["messages"]

            # First check if ticket exists
            existing_ticket = await tickets_collection.find_one({"ticket_id": ticket_id})

            if not existing_ticket:
                logger.warning(f"Ticket {ticket_id} not found for deletion")
                return False

            # Delete the ticket
            delete_result = await tickets_collection.delete_one({"ticket_id": ticket_id})

            if delete_result.deleted_count == 1:
                logger.info(f"Successfully deleted ticket {ticket_id}")

                # Also delete associated messages if any
                try:
                    message_delete_result = await messages_collection.delete_many(
                        {"ticket_id": existing_ticket["_id"]}
                    )
                    logger.info(f"Deleted {message_delete_result.deleted_count} messages for ticket {ticket_id}")
                except Exception as msg_error:
                    logger.warning(f"Failed to delete messages for ticket {ticket_id}: {msg_error}")
                    # Don't fail the ticket deletion if message deletion fails

                return True
            else:
                logger.warning(f"Failed to delete ticket {ticket_id} - no documents deleted")
                return False

        except Exception as e:
            logger.error(f"Error deleting ticket {ticket_id}: {str(e)}")
            raise

    def _is_valid_status_transition(
        self, current_status: TicketStatus, new_status: TicketStatus
    ) -> bool:
        """
        Validate if a status transition is allowed

        Valid transitions: open -> assigned -> resolved -> closed
        """
        valid_transitions = {
            TicketStatus.OPEN: [TicketStatus.ASSIGNED, TicketStatus.RESOLVED],
            TicketStatus.ASSIGNED: [TicketStatus.RESOLVED, TicketStatus.OPEN],
            TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.ASSIGNED],
            TicketStatus.CLOSED: [],  # No transitions from closed
        }

        return new_status in valid_transitions.get(current_status, [])

    async def _trigger_ticket_summarization(self, ticket: TicketModel) -> None:
        """
        Trigger automatic summarization and FAQ storage for a closed ticket.

        Args:
            ticket: The closed ticket to summarize
        """
        try:
            logger.info(f"Starting automatic summarization for closed ticket {ticket.ticket_id}")

            # Import here to avoid circular imports
            from app.services.ai.ticket_summarizer import summarize_closed_ticket
            from app.services.faq_service import store_ticket_as_faq
            from app.services.message_service import message_service
            from app.schemas.message import MessageSchema

            # Get all conversation messages for the ticket
            message_models = await message_service.get_all_ticket_messages(str(ticket._id))

            # Convert MessageModel to MessageSchema for the summarizer
            conversation_messages = []
            for msg_model in message_models:
                msg_schema = MessageSchema(
                    id=str(msg_model._id),
                    ticket_id=str(msg_model.ticket_id),
                    sender_id=str(msg_model.sender_id),
                    sender_role=msg_model.sender_role,
                    message_type=msg_model.message_type,
                    content=msg_model.content,
                    isAI=msg_model.isAI,
                    feedback=msg_model.feedback,
                    timestamp=msg_model.timestamp
                )
                conversation_messages.append(msg_schema)

            logger.info(f"Retrieved {len(conversation_messages)} messages for ticket {ticket.ticket_id}")

            # Generate AI summary
            summary = await summarize_closed_ticket(ticket, conversation_messages)

            if summary:
                logger.info(f"Successfully generated summary for ticket {ticket.ticket_id}")

                # Store as FAQ in vector database
                success = await store_ticket_as_faq(ticket, summary)

                if success:
                    logger.info(f"Successfully stored FAQ for ticket {ticket.ticket_id}")
                else:
                    logger.error(f"Failed to store FAQ for ticket {ticket.ticket_id}")
            else:
                logger.warning(f"No summary generated for ticket {ticket.ticket_id}")

        except Exception as e:
            # Don't fail the ticket update if summarization fails
            logger.error(f"Error in automatic ticket summarization for {ticket.ticket_id}: {str(e)}")
            # Continue without raising the exception to avoid breaking the ticket update


# Global service instance
ticket_service = TicketService()
