from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
import time
import random
import string
import logging
from app.schemas.ticket import TicketUrgency, TicketStatus, TicketDepartment

logger = logging.getLogger(__name__)


class TicketModel:
    """Ticket model for MongoDB operations"""

    def __init__(
        self,
        title: str,
        description: str,
        user_id: ObjectId,
        urgency: TicketUrgency = TicketUrgency.MEDIUM,
        status: TicketStatus = TicketStatus.OPEN,
        department: Optional[TicketDepartment] = None,
        assignee_id: Optional[ObjectId] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        closed_at: Optional[datetime] = None,
        misuse_flag: bool = False,
        feedback: Optional[str] = None,
        ticket_id: Optional[str] = None,
        _id: Optional[ObjectId] = None,
        user_info: Optional[dict] = None,
    ):
        self._id = _id
        self.ticket_id = ticket_id or self._generate_ticket_id()
        self.title = title
        self.description = description
        self.urgency = urgency
        self.status = status
        self.department = department
        self.assignee_id = assignee_id
        self.user_id = user_id
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.closed_at = closed_at
        self.misuse_flag = misuse_flag
        self.feedback = feedback
        self.user_info = user_info  # For agents/admins to see user details

        logger.info(f"TicketModel initialized with ticket_id: {self.ticket_id}")

    @staticmethod
    def _generate_ticket_id() -> str:
        """Generate unique ticket ID in format TKT-<timestamp>-<random>"""
        timestamp = int(time.time())
        random_suffix = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )
        ticket_id = f"TKT-{timestamp}-{random_suffix}"
        logger.debug(f"Generated ticket_id: {ticket_id}")
        return ticket_id

    def to_dict(self) -> dict:
        """Convert model to dictionary for MongoDB"""
        data = {
            "ticket_id": self.ticket_id,
            "title": self.title,
            "description": self.description,
            "urgency": (
                self.urgency.value
                if isinstance(self.urgency, TicketUrgency)
                else self.urgency
            ),
            "status": (
                self.status.value
                if isinstance(self.status, TicketStatus)
                else self.status
            ),
            "department": (
                self.department.value
                if isinstance(self.department, TicketDepartment)
                else self.department
            ),
            "assignee_id": self.assignee_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
            "misuse_flag": self.misuse_flag,
            "feedback": self.feedback,
        }

        # Only include _id if it's not None (for updates)
        if self._id is not None:
            data["_id"] = self._id

        logger.debug(f"TicketModel.to_dict() for ticket_id: {self.ticket_id}")
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TicketModel":
        """Create model from MongoDB document"""
        logger.debug(
            f"Creating TicketModel from dict for ticket_id: {data.get('ticket_id', 'unknown')}"
        )

        return cls(
            _id=data.get("_id"),
            ticket_id=data.get("ticket_id"),
            title=data["title"],
            description=data["description"],
            urgency=(
                TicketUrgency(data["urgency"])
                if data.get("urgency")
                else TicketUrgency.MEDIUM
            ),
            status=(
                TicketStatus(data["status"])
                if data.get("status")
                else TicketStatus.OPEN
            ),
            department=(
                TicketDepartment(data["department"]) if data.get("department") else None
            ),
            assignee_id=data.get("assignee_id"),
            user_id=data["user_id"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            closed_at=data.get("closed_at"),
            misuse_flag=data.get("misuse_flag", False),
            feedback=data.get("feedback"),
        )

    def update_status(self, new_status: TicketStatus):
        """Update ticket status with logging and timestamp"""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

        # Set closed_at when status changes to closed
        if new_status == TicketStatus.CLOSED:
            self.closed_at = datetime.now(timezone.utc)
            logger.info(f"Ticket {self.ticket_id} closed at {self.closed_at}")

        logger.info(
            f"Ticket {self.ticket_id} status changed from {old_status.value} to {new_status.value}"
        )

    def update_department(self, new_department: TicketDepartment):
        """Update ticket department with logging"""
        old_department = self.department
        self.department = new_department
        self.updated_at = datetime.now(timezone.utc)
        logger.info(
            f"Ticket {self.ticket_id} department changed from {old_department} to {new_department.value}"
        )

    def assign_to_agent(self, agent_id: ObjectId):
        """Assign ticket to an agent"""
        self.assignee_id = agent_id
        self.status = TicketStatus.ASSIGNED
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Ticket {self.ticket_id} assigned to agent {agent_id}")

    def flag_misuse(self, flag: bool = True):
        """Flag or unflag ticket for misuse"""
        self.misuse_flag = flag
        self.updated_at = datetime.now(timezone.utc)
        logger.warning(f"Ticket {self.ticket_id} misuse flag set to {flag}")

    def add_feedback(self, feedback: str):
        """Add post-resolution feedback"""
        self.feedback = feedback
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Feedback added to ticket {self.ticket_id}")
