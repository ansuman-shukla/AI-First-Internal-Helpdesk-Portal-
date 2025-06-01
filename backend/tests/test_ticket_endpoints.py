import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from bson import ObjectId
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
from app.models.ticket import TicketModel
from app.schemas.ticket import TicketStatus, TicketUrgency, TicketDepartment

client = TestClient(app)

# Mock user data
MOCK_USER = {
    "user_id": "507f1f77bcf86cd799439011",
    "username": "testuser",
    "role": "user"
}

# Mock JWT token
MOCK_TOKEN = "mock_jwt_token"

# Mock ticket data
MOCK_TICKET_DATA = {
    "_id": ObjectId("507f1f77bcf86cd799439012"),
    "ticket_id": "TKT-20240101-ABC123",
    "title": "Test Ticket",
    "description": "Test Description",
    "urgency": TicketUrgency.MEDIUM,
    "status": TicketStatus.OPEN,
    "department": None,
    "assignee_id": None,
    "user_id": ObjectId("507f1f77bcf86cd799439011"),
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

        mock_get_user.return_value = MOCK_USER
        yield mock_get_user, mock_service


class TestCreateTicket:
    """Test POST /tickets endpoint"""
    
    def test_create_ticket_success(self, mock_dependencies):
        """Test successful ticket creation"""
        mock_auth, mock_ticket_service = mock_dependencies

        # Setup mock
        mock_ticket = TicketModel.from_dict(MOCK_TICKET_DATA)
        mock_ticket_service.create_ticket = AsyncMock(return_value=mock_ticket)
        
        # Test data
        ticket_data = {
            "title": "Test Ticket",
            "description": "Test Description",
            "urgency": "medium"
        }
        
        # Make request
        response = client.post(
            "/tickets/",
            json=ticket_data,
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Ticket"
        assert data["description"] == "Test Description"
        assert data["urgency"] == "medium"
        assert data["status"] == "open"
        assert data["misuse_flag"] is False
        
        # Verify service was called correctly
        mock_ticket_service.create_ticket.assert_called_once()
    
    def test_create_ticket_rate_limit_exceeded(self, mock_dependencies):
        """Test ticket creation with rate limit exceeded"""
        mock_auth, mock_ticket_service = mock_dependencies

        # Setup mock to raise rate limit error
        mock_ticket_service.create_ticket = AsyncMock(
            side_effect=ValueError("Rate limit exceeded: Maximum 5 tickets per 24 hours")
        )
        
        ticket_data = {
            "title": "Test Ticket",
            "description": "Test Description"
        }
        
        response = client.post(
            "/tickets/",
            json=ticket_data,
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )
        
        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()
    
    def test_create_ticket_validation_error(self, mock_dependencies):
        """Test ticket creation with validation errors"""
        mock_auth, mock_ticket_service = mock_dependencies
        # Test missing title
        response = client.post(
            "/tickets/",
            json={"description": "Test Description"},
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )
        assert response.status_code == 422
        
        # Test empty title
        response = client.post(
            "/tickets/",
            json={"title": "", "description": "Test Description"},
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )
        assert response.status_code == 422
        
        # Test title too long
        response = client.post(
            "/tickets/",
            json={"title": "x" * 201, "description": "Test Description"},
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )
        assert response.status_code == 422


class TestGetTickets:
    """Test GET /tickets endpoint"""
    
    def test_get_tickets_success(self, mock_dependencies):
        """Test successful ticket retrieval"""
        mock_auth, mock_ticket_service = mock_dependencies

        # Setup mock
        mock_ticket = TicketModel.from_dict(MOCK_TICKET_DATA)
        mock_result = {
            "tickets": [mock_ticket],
            "total_count": 1,
            "page": 1,
            "limit": 10,
            "total_pages": 1
        }
        mock_ticket_service.get_tickets_by_user = AsyncMock(return_value=mock_result)
        
        # Make request
        response = client.get(
            "/tickets/",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 1
        assert data["total_count"] == 1
        assert data["page"] == 1
        assert data["limit"] == 10
        
        # Verify service was called correctly
        mock_ticket_service.get_tickets_by_user.assert_called_once_with(
            user_id=MOCK_USER["user_id"],
            status=None,
            department=None,
            page=1,
            limit=10
        )
    
    def test_get_tickets_with_filters(self, mock_auth, mock_ticket_service):
        """Test ticket retrieval with filters"""
        mock_ticket_service.get_tickets_by_user = AsyncMock(return_value={
            "tickets": [],
            "total_count": 0,
            "page": 1,
            "limit": 5,
            "total_pages": 0
        })
        
        response = client.get(
            "/tickets/?status=open&department=IT&page=1&limit=5",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )
        
        assert response.status_code == 200
        
        # Verify filters were passed correctly
        mock_ticket_service.get_tickets_by_user.assert_called_once_with(
            user_id=MOCK_USER["user_id"],
            status=TicketStatus.OPEN,
            department=TicketDepartment.IT,
            page=1,
            limit=5
        )


class TestGetTicketById:
    """Test GET /tickets/{ticket_id} endpoint"""

    def test_get_ticket_by_id_success(self, mock_auth, mock_ticket_service):
        """Test successful single ticket retrieval"""
        # Setup mock
        mock_ticket = TicketModel.from_dict(MOCK_TICKET_DATA)
        mock_ticket_service.get_ticket_by_id = AsyncMock(return_value=mock_ticket)

        # Make request
        response = client.get(
            f"/tickets/{MOCK_TICKET_DATA['ticket_id']}",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ticket_id"] == MOCK_TICKET_DATA["ticket_id"]
        assert data["title"] == MOCK_TICKET_DATA["title"]

        # Verify service was called correctly
        mock_ticket_service.get_ticket_by_id.assert_called_once_with(
            MOCK_TICKET_DATA["ticket_id"],
            MOCK_USER["user_id"]
        )

    def test_get_ticket_by_id_not_found(self, mock_auth, mock_ticket_service):
        """Test ticket retrieval when ticket not found"""
        # Setup mock to return None
        mock_ticket_service.get_ticket_by_id = AsyncMock(return_value=None)

        response = client.get(
            "/tickets/nonexistent-ticket",
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateTicket:
    """Test PUT /tickets/{ticket_id} endpoint"""

    def test_update_ticket_success(self, mock_auth, mock_ticket_service):
        """Test successful ticket update"""
        # Setup mock
        updated_data = MOCK_TICKET_DATA.copy()
        updated_data["title"] = "Updated Title"
        updated_data["description"] = "Updated Description"
        mock_updated_ticket = TicketModel.from_dict(updated_data)
        mock_ticket_service.update_ticket = AsyncMock(return_value=mock_updated_ticket)

        # Test data
        update_data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "urgency": "high"
        }

        # Make request
        response = client.put(
            f"/tickets/{MOCK_TICKET_DATA['ticket_id']}",
            json=update_data,
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated Description"

        # Verify service was called correctly
        mock_ticket_service.update_ticket.assert_called_once()

    def test_update_ticket_not_found(self, mock_auth, mock_ticket_service):
        """Test ticket update when ticket not found"""
        # Setup mock to return None
        mock_ticket_service.update_ticket = AsyncMock(return_value=None)

        update_data = {"title": "Updated Title"}

        response = client.put(
            "/tickets/nonexistent-ticket",
            json=update_data,
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_ticket_status_not_open(self, mock_auth, mock_ticket_service):
        """Test ticket update when status is not open"""
        # Setup mock to raise validation error
        mock_ticket_service.update_ticket = AsyncMock(
            side_effect=ValueError("Can only edit tickets with status 'open'")
        )

        update_data = {"title": "Updated Title"}

        response = client.put(
            f"/tickets/{MOCK_TICKET_DATA['ticket_id']}",
            json=update_data,
            headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        assert response.status_code == 400
        assert "open" in response.json()["detail"].lower()


class TestTicketEndpointsIntegration:
    """Integration tests for ticket endpoints"""

    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        # Test create ticket without auth
        response = client.post("/tickets/", json={"title": "Test", "description": "Test"})
        assert response.status_code == 401

        # Test get tickets without auth
        response = client.get("/tickets/")
        assert response.status_code == 401

        # Test get ticket by id without auth
        response = client.get("/tickets/test-ticket")
        assert response.status_code == 401

        # Test update ticket without auth
        response = client.put("/tickets/test-ticket", json={"title": "Updated"})
        assert response.status_code == 401
