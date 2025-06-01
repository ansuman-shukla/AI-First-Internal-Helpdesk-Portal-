"""
Integration Tests for Ticket FAQ Pipeline

This module tests the complete pipeline from ticket closure to FAQ storage,
including ticket summarization and vector database storage.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from bson import ObjectId

from app.services.ticket_service import TicketService
from app.models.ticket import TicketModel
from app.schemas.ticket import TicketStatus, TicketUrgency, TicketDepartment, TicketUpdateSchema
from app.schemas.user import UserRole
from app.schemas.message import MessageSchema, MessageRole, MessageType, MessageFeedback


@pytest.fixture
def sample_ticket_data():
    """Create sample ticket data for testing"""
    return {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "ticket_id": "TKT-20240101-ABC123",
        "title": "Cannot access email",
        "description": "User unable to access their email account since this morning",
        "urgency": TicketUrgency.HIGH.value,
        "status": TicketStatus.RESOLVED.value,  # Start as resolved, will be closed
        "department": TicketDepartment.IT.value,
        "user_id": ObjectId("507f1f77bcf86cd799439012"),
        "assignee_id": ObjectId("507f1f77bcf86cd799439013"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "closed_at": None,
        "misuse_flag": False,
        "feedback": None
    }


@pytest.fixture
def sample_messages():
    """Create sample conversation messages"""
    base_time = datetime.now(timezone.utc)
    
    return [
        MessageSchema(
            id="msg1",
            ticket_id="TKT-20240101-ABC123",
            sender_id="507f1f77bcf86cd799439012",
            sender_role=MessageRole.USER,
            message_type=MessageType.USER_MESSAGE,
            content="I can't access my email. It keeps saying password incorrect.",
            isAI=False,
            feedback=MessageFeedback.NONE,
            timestamp=base_time
        ),
        MessageSchema(
            id="msg2",
            ticket_id="TKT-20240101-ABC123",
            sender_id="507f1f77bcf86cd799439013",
            sender_role=MessageRole.IT_AGENT,
            message_type=MessageType.AGENT_MESSAGE,
            content="Let me help you with that. I'll reset your password.",
            isAI=False,
            feedback=MessageFeedback.NONE,
            timestamp=base_time
        ),
        MessageSchema(
            id="msg3",
            ticket_id="TKT-20240101-ABC123",
            sender_id="507f1f77bcf86cd799439013",
            sender_role=MessageRole.IT_AGENT,
            message_type=MessageType.AGENT_MESSAGE,
            content="I've reset your account on the server. Please try logging in now.",
            isAI=False,
            feedback=MessageFeedback.UP,
            timestamp=base_time
        ),
        MessageSchema(
            id="msg4",
            ticket_id="TKT-20240101-ABC123",
            sender_id="507f1f77bcf86cd799439012",
            sender_role=MessageRole.USER,
            message_type=MessageType.USER_MESSAGE,
            content="Thank you! It's working now.",
            isAI=False,
            feedback=MessageFeedback.NONE,
            timestamp=base_time
        )
    ]


class TestTicketFAQIntegration:
    """Integration tests for the complete ticket FAQ pipeline"""

    @pytest.mark.asyncio
    @patch('app.services.ticket_service.get_database')
    @patch('app.services.message_service.message_service')
    @patch('app.services.ai.ticket_summarizer.summarize_closed_ticket')
    @patch('app.services.faq_service.store_ticket_as_faq')
    async def test_complete_ticket_closure_to_faq_pipeline(
        self,
        mock_store_faq,
        mock_summarize,
        mock_message_service,
        mock_get_db,
        sample_ticket_data,
        sample_messages
    ):
        """Test the complete pipeline from ticket closure to FAQ storage"""
        
        # Setup mocks
        mock_collection = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        
        # Mock finding the ticket
        mock_collection.find_one.return_value = sample_ticket_data
        
        # Mock successful update
        mock_update_result = Mock()
        mock_update_result.modified_count = 1
        mock_collection.update_one.return_value = mock_update_result
        
        # Mock message service to return conversation (async function)
        mock_message_models = [
            Mock(
                _id=ObjectId(),
                ticket_id=ObjectId(sample_ticket_data["_id"]),
                sender_id=ObjectId(msg.sender_id),
                sender_role=msg.sender_role,
                message_type=msg.message_type,
                content=msg.content,
                isAI=msg.isAI,
                feedback=msg.feedback,
                timestamp=msg.timestamp
            ) for msg in sample_messages
        ]
        mock_message_service.get_all_ticket_messages = AsyncMock(return_value=mock_message_models)
        
        # Mock AI summarization
        from app.services.ai.ticket_summarizer import TicketSummary
        mock_summary = TicketSummary(
            issue_summary="User unable to access email due to password issues",
            resolution_summary="IT agent reset the account, resolving the access problem",
            department="IT",
            category="FAQ",
            confidence_score=0.9
        )
        mock_summarize.return_value = mock_summary
        
        # Mock FAQ storage
        mock_store_faq.return_value = True
        
        # Create service and test the update
        service = TicketService()
        
        # Create update data to close the ticket
        update_data = TicketUpdateSchema(status=TicketStatus.CLOSED)
        
        # Execute the update (this should trigger the FAQ pipeline)
        result = await service.update_ticket_with_role(
            ticket_id="TKT-20240101-ABC123",
            user_id="507f1f77bcf86cd799439013",  # Agent ID
            user_role=UserRole.IT_AGENT,
            update_data=update_data
        )
        
        # Verify the pipeline was executed
        assert result is not None
        
        # Verify message retrieval was called
        mock_message_service.get_all_ticket_messages.assert_called_once()
        
        # Verify summarization was called
        mock_summarize.assert_called_once()
        
        # Verify FAQ storage was called
        mock_store_faq.assert_called_once()
        
        # Verify the summary passed to FAQ storage
        call_args = mock_store_faq.call_args
        stored_summary = call_args[0][1]  # Second argument is the summary
        assert stored_summary.issue_summary == "User unable to access email due to password issues"
        assert stored_summary.department == "IT"

    @pytest.mark.asyncio
    @patch('app.services.ticket_service.get_database')
    @patch('app.services.message_service.message_service')
    @patch('app.services.ai.ticket_summarizer.summarize_closed_ticket')
    @patch('app.services.faq_service.store_ticket_as_faq')
    async def test_faq_pipeline_with_summarization_failure(
        self,
        mock_store_faq,
        mock_summarize,
        mock_message_service,
        mock_get_db,
        sample_ticket_data
    ):
        """Test that ticket update succeeds even if summarization fails"""
        
        # Setup mocks for successful ticket update
        mock_collection = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        
        mock_collection.find_one.return_value = sample_ticket_data
        
        mock_update_result = Mock()
        mock_update_result.modified_count = 1
        mock_collection.update_one.return_value = mock_update_result
        
        # Mock message service (async function)
        mock_message_service.get_all_ticket_messages = AsyncMock(return_value=[])
        
        # Mock summarization failure
        mock_summarize.side_effect = Exception("AI service unavailable")
        
        # Create service and test the update
        service = TicketService()
        update_data = TicketUpdateSchema(status=TicketStatus.CLOSED)
        
        # Execute the update - should not fail even if summarization fails
        result = await service.update_ticket_with_role(
            ticket_id="TKT-20240101-ABC123",
            user_id="507f1f77bcf86cd799439013",
            user_role=UserRole.IT_AGENT,
            update_data=update_data
        )
        
        # Ticket update should still succeed
        assert result is not None
        
        # Summarization was attempted but failed
        mock_summarize.assert_called_once()
        
        # FAQ storage should not be called due to summarization failure
        mock_store_faq.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.services.ticket_service.get_database')
    @patch('app.services.message_service.message_service')
    @patch('app.services.ai.ticket_summarizer.summarize_closed_ticket')
    @patch('app.services.faq_service.store_ticket_as_faq')
    async def test_faq_pipeline_with_storage_failure(
        self,
        mock_store_faq,
        mock_summarize,
        mock_message_service,
        mock_get_db,
        sample_ticket_data
    ):
        """Test that ticket update succeeds even if FAQ storage fails"""
        
        # Setup mocks for successful ticket update
        mock_collection = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        
        mock_collection.find_one.return_value = sample_ticket_data
        
        mock_update_result = Mock()
        mock_update_result.modified_count = 1
        mock_collection.update_one.return_value = mock_update_result
        
        # Mock message service (async function)
        mock_message_service.get_all_ticket_messages = AsyncMock(return_value=[])
        
        # Mock successful summarization
        from app.services.ai.ticket_summarizer import TicketSummary
        mock_summary = TicketSummary(
            issue_summary="Test issue",
            resolution_summary="Test resolution",
            department="IT",
            category="FAQ",
            confidence_score=0.8
        )
        mock_summarize.return_value = mock_summary
        
        # Mock FAQ storage failure
        mock_store_faq.return_value = False
        
        # Create service and test the update
        service = TicketService()
        update_data = TicketUpdateSchema(status=TicketStatus.CLOSED)
        
        # Execute the update - should not fail even if FAQ storage fails
        result = await service.update_ticket_with_role(
            ticket_id="TKT-20240101-ABC123",
            user_id="507f1f77bcf86cd799439013",
            user_role=UserRole.IT_AGENT,
            update_data=update_data
        )
        
        # Ticket update should still succeed
        assert result is not None
        
        # Both summarization and storage were attempted
        mock_summarize.assert_called_once()
        mock_store_faq.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.ticket_service.get_database')
    async def test_no_faq_pipeline_for_non_closure_updates(
        self,
        mock_get_db,
        sample_ticket_data
    ):
        """Test that FAQ pipeline is not triggered for non-closure updates"""
        
        # Setup mocks
        mock_collection = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        
        mock_collection.find_one.return_value = sample_ticket_data
        
        mock_update_result = Mock()
        mock_update_result.modified_count = 1
        mock_collection.update_one.return_value = mock_update_result
        
        # Create service and test a non-closure update
        service = TicketService()
        
        with patch.object(service, '_trigger_ticket_summarization') as mock_trigger:
            # Update title instead of status
            update_data = TicketUpdateSchema(title="Updated title")
            
            result = await service.update_ticket_with_role(
                ticket_id="TKT-20240101-ABC123",
                user_id="507f1f77bcf86cd799439013",
                user_role=UserRole.IT_AGENT,
                update_data=update_data
            )
            
            # Update should succeed
            assert result is not None
            
            # Summarization should not be triggered
            mock_trigger.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.services.ticket_service.get_database')
    async def test_no_faq_pipeline_for_already_closed_ticket(
        self,
        mock_get_db,
        sample_ticket_data
    ):
        """Test that FAQ pipeline is not triggered if ticket is already closed"""
        
        # Modify sample data to be already closed
        sample_ticket_data["status"] = TicketStatus.CLOSED.value
        sample_ticket_data["closed_at"] = datetime.now(timezone.utc)
        
        # Setup mocks
        mock_collection = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        
        mock_collection.find_one.return_value = sample_ticket_data
        
        mock_update_result = Mock()
        mock_update_result.modified_count = 1
        mock_collection.update_one.return_value = mock_update_result
        
        # Create service and test
        service = TicketService()
        
        with patch.object(service, '_trigger_ticket_summarization') as mock_trigger:
            # Try to update a closed ticket (should not trigger FAQ pipeline)
            update_data = TicketUpdateSchema(feedback="Great service!")
            
            result = await service.update_ticket_with_role(
                ticket_id="TKT-20240101-ABC123",
                user_id="507f1f77bcf86cd799439013",
                user_role=UserRole.IT_AGENT,
                update_data=update_data
            )
            
            # Update should succeed
            assert result is not None
            
            # Summarization should not be triggered (ticket was already closed)
            mock_trigger.assert_not_called()
