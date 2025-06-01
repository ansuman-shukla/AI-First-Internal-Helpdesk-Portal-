"""
Integration tests for AI-powered ticket creation

Tests the integration of HSA filtering and department routing in ticket creation process.
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.services.ticket_service import TicketService
from app.schemas.ticket import TicketCreateSchema, TicketUrgency, TicketStatus, TicketDepartment
from app.models.ticket import TicketModel
from bson import ObjectId


class TestTicketCreationAIIntegration:
    """Test AI integration in ticket creation process"""

    @pytest.fixture
    def ticket_service(self):
        """Create ticket service instance"""
        return TicketService()

    @pytest.fixture
    def sample_ticket_data(self):
        """Sample ticket creation data"""
        return TicketCreateSchema(
            title="Computer won't start",
            description="My laptop is not booting up and shows a blue screen error",
            urgency=TicketUrgency.MEDIUM
        )

    @pytest.fixture
    def harmful_ticket_data(self):
        """Sample harmful ticket data for testing"""
        return TicketCreateSchema(
            title="Test harmful content",
            description="This is test content that would be flagged as harmful",
            urgency=TicketUrgency.LOW
        )

    @pytest.fixture
    def hr_ticket_data(self):
        """Sample HR-related ticket data"""
        return TicketCreateSchema(
            title="Payroll issue",
            description="I have a problem with my salary calculation this month",
            urgency=TicketUrgency.HIGH
        )

    @pytest.mark.asyncio
    async def test_safe_ticket_creation_it_routing(self, ticket_service, sample_ticket_data):
        """Test that safe IT-related tickets are properly routed"""
        user_id = str(ObjectId())
        
        with patch.object(ticket_service, '_check_rate_limit', new_callable=AsyncMock) as mock_rate_limit, \
             patch('app.services.ticket_service.check_harmful', return_value=False) as mock_hsa, \
             patch('app.services.ticket_service.assign_department', return_value="IT") as mock_routing, \
             patch('app.services.ticket_service.get_database') as mock_db:

            # Mock database operations
            mock_collection = AsyncMock()
            mock_db.return_value = {ticket_service.collection_name: mock_collection}
            mock_collection.insert_one.return_value = AsyncMock(inserted_id=ObjectId())
            
            # Create ticket
            result = await ticket_service.create_ticket(sample_ticket_data, user_id)
            
            # Verify AI modules were called
            mock_hsa.assert_called_once_with(sample_ticket_data.title, sample_ticket_data.description)
            mock_routing.assert_called_once_with(sample_ticket_data.title, sample_ticket_data.description)
            
            # Verify ticket properties
            assert result.status == TicketStatus.ASSIGNED
            assert result.department == TicketDepartment.IT
            assert result.misuse_flag is False
            assert result.title == sample_ticket_data.title
            assert result.description == sample_ticket_data.description

    @pytest.mark.asyncio
    async def test_safe_ticket_creation_hr_routing(self, ticket_service, hr_ticket_data):
        """Test that safe HR-related tickets are properly routed"""
        user_id = str(ObjectId())
        
        with patch.object(ticket_service, '_check_rate_limit', new_callable=AsyncMock) as mock_rate_limit, \
             patch('app.services.ticket_service.check_harmful', return_value=False) as mock_hsa, \
             patch('app.services.ticket_service.assign_department', return_value="HR") as mock_routing, \
             patch('app.services.ticket_service.get_database') as mock_db:
            
            # Mock database operations
            mock_collection = AsyncMock()
            mock_db.return_value = {ticket_service.collection_name: mock_collection}
            mock_collection.insert_one.return_value = AsyncMock(inserted_id=ObjectId())
            
            # Create ticket
            result = await ticket_service.create_ticket(hr_ticket_data, user_id)
            
            # Verify AI modules were called
            mock_hsa.assert_called_once_with(hr_ticket_data.title, hr_ticket_data.description)
            mock_routing.assert_called_once_with(hr_ticket_data.title, hr_ticket_data.description)
            
            # Verify ticket properties
            assert result.status == TicketStatus.ASSIGNED
            assert result.department == TicketDepartment.HR
            assert result.misuse_flag is False

    @pytest.mark.asyncio
    async def test_harmful_ticket_creation_flagged(self, ticket_service, harmful_ticket_data):
        """Test that harmful tickets are flagged and not routed"""
        user_id = str(ObjectId())
        
        with patch.object(ticket_service, '_check_rate_limit', new_callable=AsyncMock) as mock_rate_limit, \
             patch('app.services.ticket_service.check_harmful', return_value=True) as mock_hsa, \
             patch('app.services.ticket_service.assign_department') as mock_routing, \
             patch('app.services.ticket_service.get_database') as mock_db:
            
            # Mock database operations
            mock_collection = AsyncMock()
            mock_db.return_value = {ticket_service.collection_name: mock_collection}
            mock_collection.insert_one.return_value = AsyncMock(inserted_id=ObjectId())
            
            # Create ticket
            result = await ticket_service.create_ticket(harmful_ticket_data, user_id)
            
            # Verify HSA was called but routing was not
            mock_hsa.assert_called_once_with(harmful_ticket_data.title, harmful_ticket_data.description)
            mock_routing.assert_not_called()
            
            # Verify ticket properties for harmful content
            assert result.status == TicketStatus.OPEN  # Stays open for admin review
            assert result.department is None  # No department assigned
            assert result.misuse_flag is True  # Flagged as harmful
            assert result.title == harmful_ticket_data.title
            assert result.description == harmful_ticket_data.description

    @pytest.mark.asyncio
    async def test_ai_integration_with_rate_limiting(self, ticket_service, sample_ticket_data):
        """Test that AI integration works with rate limiting"""
        user_id = str(ObjectId())
        
        with patch.object(ticket_service, '_check_rate_limit', new_callable=AsyncMock) as mock_rate_limit, \
             patch('app.services.ai.hsa.check_harmful', return_value=False) as mock_hsa, \
             patch('app.services.ai.routing.assign_department', return_value="IT") as mock_routing, \
             patch('app.core.database.get_database') as mock_db:
            
            # Mock rate limit to raise exception
            mock_rate_limit.side_effect = ValueError("Rate limit exceeded: Maximum 5 tickets per 24 hours")
            
            # Attempt to create ticket
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await ticket_service.create_ticket(sample_ticket_data, user_id)
            
            # Verify rate limit was checked first
            mock_rate_limit.assert_called_once_with(user_id)
            
            # Verify AI modules were not called due to rate limit
            mock_hsa.assert_not_called()
            mock_routing.assert_not_called()

    @pytest.mark.asyncio
    async def test_ai_integration_error_handling(self, ticket_service, sample_ticket_data):
        """Test error handling in AI integration"""
        user_id = str(ObjectId())

        with patch.object(ticket_service, '_check_rate_limit', new_callable=AsyncMock) as mock_rate_limit, \
             patch('app.services.ticket_service.check_harmful', side_effect=Exception("HSA service error")) as mock_hsa:

            # Attempt to create ticket with HSA error
            with pytest.raises(Exception, match="HSA service error"):
                await ticket_service.create_ticket(sample_ticket_data, user_id)

            # Verify rate limit was checked
            mock_rate_limit.assert_called_once_with(user_id)

            # Verify HSA was called and failed
            mock_hsa.assert_called_once_with(sample_ticket_data.title, sample_ticket_data.description)

    @pytest.mark.asyncio
    async def test_logging_for_ai_integration(self, ticket_service, sample_ticket_data, caplog):
        """Test that proper logging occurs during AI integration"""
        import logging
        caplog.set_level(logging.INFO)

        user_id = str(ObjectId())

        with patch.object(ticket_service, '_check_rate_limit', new_callable=AsyncMock) as mock_rate_limit, \
             patch('app.services.ticket_service.check_harmful', return_value=False) as mock_hsa, \
             patch('app.services.ticket_service.assign_department', return_value="IT") as mock_routing, \
             patch('app.services.ticket_service.get_database') as mock_db:

            # Mock database operations
            mock_collection = AsyncMock()
            mock_db.return_value = {ticket_service.collection_name: mock_collection}
            mock_collection.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

            # Create ticket
            await ticket_service.create_ticket(sample_ticket_data, user_id)

            # Check that appropriate log messages were generated
            assert "Running HSA check for ticket" in caplog.text
            assert "Running department routing for ticket" in caplog.text
            assert "Ticket routed to IT department" in caplog.text
