import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from bson import ObjectId
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

client = TestClient(app)

# Mock user data
MOCK_USER = {
    "user_id": "507f1f77bcf86cd799439011",
    "username": "testuser",
    "role": "user"
}

def test_create_ticket_unauthorized():
    """Test that creating a ticket without auth returns 401"""
    response = client.post("/tickets/", json={"title": "Test", "description": "Test"})
    # Should be 401 or 403 (depending on FastAPI auth setup)
    assert response.status_code in [401, 403]

def test_create_ticket_with_dependency_override():
    """Test ticket creation using FastAPI dependency override"""
    from app.routers.auth import get_current_user
    from app.models.ticket import TicketModel
    from app.schemas.ticket import TicketStatus, TicketUrgency
    from datetime import datetime, timezone

    # Mock function to return our test user
    def mock_get_current_user():
        return MOCK_USER

    # Mock ticket service
    with patch("app.routers.tickets.ticket_service") as mock_service:
        mock_ticket = TicketModel(
            title="Test Ticket",
            description="Test Description",
            user_id=ObjectId(MOCK_USER["user_id"]),
            urgency=TicketUrgency.MEDIUM,
            status=TicketStatus.OPEN
        )
        mock_service.create_ticket = AsyncMock(return_value=mock_ticket)

        # Override the dependency
        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            # Test data
            ticket_data = {
                "title": "Test Ticket",
                "description": "Test Description",
                "urgency": "medium"
            }

            # Make request (no auth header needed with override)
            response = client.post("/tickets/", json=ticket_data)

            # Check response
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")

            # Should succeed with mocked auth
            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "Test Ticket"
            assert data["status"] == "open"

        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

if __name__ == "__main__":
    test_create_ticket_unauthorized()
    test_create_ticket_with_dependency_override()
    print("Basic tests passed!")
