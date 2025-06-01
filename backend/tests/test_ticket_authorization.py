"""
Tests for role-based ticket authorization
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from bson import ObjectId
from datetime import datetime, timezone

from main import app
from app.models.ticket import TicketModel
from app.schemas.ticket import TicketStatus, TicketDepartment, TicketUrgency
from app.schemas.user import UserRole

client = TestClient(app)

# Mock data
MOCK_TOKEN = "mock_jwt_token"

# Mock users with different roles
MOCK_USER = {
    "user_id": "507f1f77bcf86cd799439011",
    "username": "testuser",
    "role": "user"
}

MOCK_IT_AGENT = {
    "user_id": "507f1f77bcf86cd799439012",
    "username": "itagent",
    "role": "it_agent"
}

MOCK_HR_AGENT = {
    "user_id": "507f1f77bcf86cd799439013",
    "username": "hragent",
    "role": "hr_agent"
}

MOCK_ADMIN = {
    "user_id": "507f1f77bcf86cd799439014",
    "username": "admin",
    "role": "admin"
}

# Mock ticket data
MOCK_USER_TICKET = {
    "_id": ObjectId("507f1f77bcf86cd799439020"),
    "ticket_id": "TKT-20240101-001",
    "title": "User's IT Issue",
    "description": "My computer won't start",
    "urgency": TicketUrgency.MEDIUM,
    "status": TicketStatus.OPEN,
    "department": TicketDepartment.IT,
    "assignee_id": ObjectId("507f1f77bcf86cd799439012"),  # IT agent
    "user_id": ObjectId("507f1f77bcf86cd799439011"),  # User
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "closed_at": None,
    "misuse_flag": False,
    "feedback": None
}

MOCK_IT_TICKET = {
    "_id": ObjectId("507f1f77bcf86cd799439021"),
    "ticket_id": "TKT-20240101-002",
    "title": "IT Department Ticket",
    "description": "Server maintenance required",
    "urgency": TicketUrgency.HIGH,
    "status": TicketStatus.ASSIGNED,
    "department": TicketDepartment.IT,
    "assignee_id": ObjectId("507f1f77bcf86cd799439012"),  # IT agent
    "user_id": ObjectId("507f1f77bcf86cd799439015"),  # Different user
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "closed_at": None,
    "misuse_flag": False,
    "feedback": None
}

MOCK_HR_TICKET = {
    "_id": ObjectId("507f1f77bcf86cd799439022"),
    "ticket_id": "TKT-20240101-003",
    "title": "HR Department Ticket",
    "description": "Payroll inquiry",
    "urgency": TicketUrgency.LOW,
    "status": TicketStatus.ASSIGNED,
    "department": TicketDepartment.HR,
    "assignee_id": ObjectId("507f1f77bcf86cd799439013"),  # HR agent
    "user_id": ObjectId("507f1f77bcf86cd799439016"),  # Different user
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "closed_at": None,
    "misuse_flag": False,
    "feedback": None
}


@pytest.fixture
def mock_dependencies():
    """Mock both authentication and ticket service dependencies"""
    with patch("app.routers.tickets.get_current_user") as mock_get_user, \
         patch("app.routers.tickets.ticket_service") as mock_service:
        yield mock_get_user, mock_service


class TestGetTicketsAuthorization:
    """Test GET /tickets endpoint with role-based authorization"""

    def test_user_can_only_see_own_tickets(self, mock_dependencies):
        """Test that users can only see their own tickets"""
        mock_get_user, mock_ticket_service = mock_dependencies
        mock_get_user.return_value = MOCK_USER

        # Setup mock
        user_ticket = TicketModel.from_dict(MOCK_USER_TICKET)
        mock_result = {
            "tickets": [user_ticket],
            "total_count": 1,
            "page": 1,
            "limit": 10,
            "total_pages": 1
        }
        mock_ticket_service.get_tickets = AsyncMock(return_value=mock_result)

        # Make request
        response = client.get(
            "/tickets/",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 1
        assert data["tickets"][0]["user_id"] == MOCK_USER["user_id"]

        # Verify service was called with USER role
        mock_ticket_service.get_tickets.assert_called_once_with(
            user_id=MOCK_USER["user_id"],
            user_role=UserRole.USER,
            status=None,
            department=None,
            page=1,
            limit=10
        )
    
    def test_it_agent_can_see_it_tickets(self, mock_dependencies):
        """Test that IT agents can see IT department tickets"""
        mock_get_user, mock_ticket_service = mock_dependencies
        mock_get_user.return_value = MOCK_IT_AGENT

        # Setup mock
        it_ticket = TicketModel.from_dict(MOCK_IT_TICKET)
        mock_result = {
            "tickets": [it_ticket],
            "total_count": 1,
            "page": 1,
            "limit": 10,
            "total_pages": 1
        }
        mock_ticket_service.get_tickets = AsyncMock(return_value=mock_result)

        # Make request
        response = client.get(
            "/tickets/",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 1
        assert data["tickets"][0]["department"] == "IT"

        # Verify service was called with IT_AGENT role
        mock_ticket_service.get_tickets.assert_called_once_with(
            user_id=MOCK_IT_AGENT["user_id"],
            user_role=UserRole.IT_AGENT,
            status=None,
            department=None,
            page=1,
            limit=10
        )
    
    def test_admin_can_see_all_tickets(self, mock_dependencies):
        """Test that admins can see all tickets"""
        mock_get_user, mock_ticket_service = mock_dependencies
        mock_get_user.return_value = MOCK_ADMIN

        # Setup mock
        all_tickets = [
            TicketModel.from_dict(MOCK_USER_TICKET),
            TicketModel.from_dict(MOCK_IT_TICKET),
            TicketModel.from_dict(MOCK_HR_TICKET)
        ]
        mock_result = {
            "tickets": all_tickets,
            "total_count": 3,
            "page": 1,
            "limit": 10,
            "total_pages": 1
        }
        mock_ticket_service.get_tickets = AsyncMock(return_value=mock_result)

        # Make request
        response = client.get(
            "/tickets/",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 3

        # Verify service was called with ADMIN role
        mock_ticket_service.get_tickets.assert_called_once_with(
            user_id=MOCK_ADMIN["user_id"],
            user_role=UserRole.ADMIN,
            status=None,
            department=None,
            page=1,
            limit=10
        )


class TestGetTicketByIdAuthorization:
    """Test GET /tickets/{ticket_id} endpoint with role-based authorization"""

    def test_user_can_access_own_ticket(self, mock_dependencies):
        """Test that users can access their own tickets"""
        mock_get_user, mock_ticket_service = mock_dependencies
        mock_get_user.return_value = MOCK_USER

        # Setup mock
        user_ticket = TicketModel.from_dict(MOCK_USER_TICKET)
        mock_ticket_service.get_ticket_by_id_with_role = AsyncMock(return_value=user_ticket)

        # Make request
        response = client.get(
            f"/tickets/{MOCK_USER_TICKET['ticket_id']}",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ticket_id"] == MOCK_USER_TICKET["ticket_id"]
        assert data["user_id"] == MOCK_USER["user_id"]

        # Verify service was called with correct parameters
        mock_ticket_service.get_ticket_by_id_with_role.assert_called_once_with(
            ticket_id=MOCK_USER_TICKET["ticket_id"],
            user_id=MOCK_USER["user_id"],
            user_role=UserRole.USER
        )

    def test_admin_can_access_any_ticket(self, mock_dependencies):
        """Test that admins can access any ticket"""
        mock_get_user, mock_ticket_service = mock_dependencies
        mock_get_user.return_value = MOCK_ADMIN

        # Setup mock
        any_ticket = TicketModel.from_dict(MOCK_USER_TICKET)
        mock_ticket_service.get_ticket_by_id_with_role = AsyncMock(return_value=any_ticket)

        # Make request
        response = client.get(
            f"/tickets/{MOCK_USER_TICKET['ticket_id']}",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ticket_id"] == MOCK_USER_TICKET["ticket_id"]

        # Verify service was called with ADMIN role
        mock_ticket_service.get_ticket_by_id_with_role.assert_called_once_with(
            ticket_id=MOCK_USER_TICKET["ticket_id"],
            user_id=MOCK_ADMIN["user_id"],
            user_role=UserRole.ADMIN
        )
