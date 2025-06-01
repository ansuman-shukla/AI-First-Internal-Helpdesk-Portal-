import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.services.ticket_service import TicketService

client = TestClient(app)


class TestTicketDelete:
    """Test cases for ticket deletion endpoint"""

    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user for testing"""
        return {
            "user_id": "admin123",
            "username": "admin",
            "email": "admin@test.com",
            "role": "admin"
        }

    @pytest.fixture
    def mock_regular_user(self):
        """Mock regular user for testing"""
        return {
            "user_id": "user123",
            "username": "testuser",
            "email": "user@test.com",
            "role": "user"
        }

    @pytest.fixture
    def mock_agent_user(self):
        """Mock agent user for testing"""
        return {
            "user_id": "agent123",
            "username": "agent",
            "email": "agent@test.com",
            "role": "it_agent"
        }

    @patch("app.routers.tickets.ticket_service.delete_ticket")
    @patch("app.routers.tickets.require_admin")
    def test_admin_can_delete_ticket_success(self, mock_require_admin, mock_delete_ticket, mock_admin_user):
        """Test that admin can successfully delete a ticket"""
        # Setup mocks
        mock_require_admin.return_value = mock_admin_user
        mock_delete_ticket.return_value = True
        
        # Make request
        response = client.delete("/tickets/TKT-123456-ABC123")
        
        # Assertions
        assert response.status_code == 204
        mock_delete_ticket.assert_called_once_with("TKT-123456-ABC123")

    @patch("app.routers.tickets.ticket_service.delete_ticket")
    @patch("app.routers.tickets.require_admin")
    def test_admin_delete_nonexistent_ticket(self, mock_require_admin, mock_delete_ticket, mock_admin_user):
        """Test that deleting a non-existent ticket returns 404"""
        # Setup mocks
        mock_require_admin.return_value = mock_admin_user
        mock_delete_ticket.return_value = False  # Ticket not found
        
        # Make request
        response = client.delete("/tickets/TKT-NONEXISTENT")
        
        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Ticket not found"
        mock_delete_ticket.assert_called_once_with("TKT-NONEXISTENT")

    @patch("app.routers.tickets.ticket_service.delete_ticket")
    @patch("app.routers.tickets.require_admin")
    def test_admin_delete_ticket_service_error(self, mock_require_admin, mock_delete_ticket, mock_admin_user):
        """Test that service errors are handled properly"""
        # Setup mocks
        mock_require_admin.return_value = mock_admin_user
        mock_delete_ticket.side_effect = Exception("Database error")
        
        # Make request
        response = client.delete("/tickets/TKT-123456-ABC123")
        
        # Assertions
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
        mock_delete_ticket.assert_called_once_with("TKT-123456-ABC123")

    @patch("app.routers.tickets.get_current_user")
    def test_non_admin_cannot_delete_ticket(self, mock_get_current_user, mock_regular_user):
        """Test that non-admin users cannot delete tickets"""
        # Setup mock - require_admin will check the role and raise 403
        mock_get_current_user.return_value = mock_regular_user
        
        # Make request
        response = client.delete("/tickets/TKT-123456-ABC123")
        
        # Assertions
        assert response.status_code == 403
        assert "Admin role required" in response.json()["detail"]

    @patch("app.routers.tickets.get_current_user")
    def test_agent_cannot_delete_ticket(self, mock_get_current_user, mock_agent_user):
        """Test that agent users cannot delete tickets"""
        # Setup mock - require_admin will check the role and raise 403
        mock_get_current_user.return_value = mock_agent_user
        
        # Make request
        response = client.delete("/tickets/TKT-123456-ABC123")
        
        # Assertions
        assert response.status_code == 403
        assert "Admin role required" in response.json()["detail"]

    def test_delete_ticket_without_auth(self):
        """Test that unauthenticated requests are rejected"""
        # Make request without authentication
        response = client.delete("/tickets/TKT-123456-ABC123")
        
        # Assertions
        assert response.status_code == 401


class TestTicketServiceDelete:
    """Test cases for ticket service delete method"""

    @pytest.fixture
    def ticket_service(self):
        """Create a ticket service instance for testing"""
        return TicketService()

    @pytest.mark.asyncio
    @patch("app.services.ticket_service.TicketService.db")
    async def test_delete_ticket_success(self, mock_db, ticket_service):
        """Test successful ticket deletion"""
        # Setup mocks
        mock_ticket = {
            "_id": "507f1f77bcf86cd799439011",
            "ticket_id": "TKT-123456-ABC123",
            "title": "Test ticket"
        }
        mock_db.tickets.find_one.return_value = mock_ticket
        mock_db.tickets.delete_one.return_value = AsyncMock(deleted_count=1)
        mock_db.messages.delete_many.return_value = AsyncMock(deleted_count=2)
        
        # Call method
        result = await ticket_service.delete_ticket("TKT-123456-ABC123")
        
        # Assertions
        assert result is True
        mock_db.tickets.find_one.assert_called_once_with({"ticket_id": "TKT-123456-ABC123"})
        mock_db.tickets.delete_one.assert_called_once_with({"ticket_id": "TKT-123456-ABC123"})
        mock_db.messages.delete_many.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.ticket_service.TicketService.db")
    async def test_delete_nonexistent_ticket(self, mock_db, ticket_service):
        """Test deleting a non-existent ticket"""
        # Setup mocks
        mock_db.tickets.find_one.return_value = None
        
        # Call method
        result = await ticket_service.delete_ticket("TKT-NONEXISTENT")
        
        # Assertions
        assert result is False
        mock_db.tickets.find_one.assert_called_once_with({"ticket_id": "TKT-NONEXISTENT"})
        mock_db.tickets.delete_one.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.ticket_service.TicketService.db")
    async def test_delete_ticket_database_error(self, mock_db, ticket_service):
        """Test handling of database errors during deletion"""
        # Setup mocks
        mock_db.tickets.find_one.side_effect = Exception("Database connection error")
        
        # Call method and expect exception
        with pytest.raises(Exception, match="Database connection error"):
            await ticket_service.delete_ticket("TKT-123456-ABC123")

    @pytest.mark.asyncio
    @patch("app.services.ticket_service.TicketService.db")
    async def test_delete_ticket_failed_deletion(self, mock_db, ticket_service):
        """Test when ticket exists but deletion fails"""
        # Setup mocks
        mock_ticket = {
            "_id": "507f1f77bcf86cd799439011",
            "ticket_id": "TKT-123456-ABC123",
            "title": "Test ticket"
        }
        mock_db.tickets.find_one.return_value = mock_ticket
        mock_db.tickets.delete_one.return_value = AsyncMock(deleted_count=0)  # Deletion failed
        
        # Call method
        result = await ticket_service.delete_ticket("TKT-123456-ABC123")
        
        # Assertions
        assert result is False
        mock_db.tickets.find_one.assert_called_once_with({"ticket_id": "TKT-123456-ABC123"})
        mock_db.tickets.delete_one.assert_called_once_with({"ticket_id": "TKT-123456-ABC123"})

    @pytest.mark.asyncio
    @patch("app.services.ticket_service.TicketService.db")
    async def test_delete_ticket_message_deletion_fails(self, mock_db, ticket_service):
        """Test that ticket deletion succeeds even if message deletion fails"""
        # Setup mocks
        mock_ticket = {
            "_id": "507f1f77bcf86cd799439011",
            "ticket_id": "TKT-123456-ABC123",
            "title": "Test ticket"
        }
        mock_db.tickets.find_one.return_value = mock_ticket
        mock_db.tickets.delete_one.return_value = AsyncMock(deleted_count=1)
        mock_db.messages.delete_many.side_effect = Exception("Message deletion failed")
        
        # Call method
        result = await ticket_service.delete_ticket("TKT-123456-ABC123")
        
        # Assertions - should still return True even if message deletion fails
        assert result is True
        mock_db.tickets.delete_one.assert_called_once_with({"ticket_id": "TKT-123456-ABC123"})
