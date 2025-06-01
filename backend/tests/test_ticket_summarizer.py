"""
Tests for Ticket Summarization Service

This module tests the AI-powered ticket summarization functionality
for FAQ generation from closed tickets.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from bson import ObjectId

from app.services.ai.ticket_summarizer import (
    summarize_closed_ticket,
    TicketSummary,
    _format_conversation_for_analysis,
    _parse_llm_summary_response,
    _create_fallback_summary
)
from app.models.ticket import TicketModel
from app.schemas.ticket import TicketStatus, TicketUrgency, TicketDepartment
from app.schemas.message import MessageSchema, MessageRole, MessageType, MessageFeedback


@pytest.fixture
def sample_closed_ticket():
    """Create a sample closed ticket for testing"""
    return TicketModel(
        _id=ObjectId("507f1f77bcf86cd799439011"),
        ticket_id="TKT-20240101-ABC123",
        title="Cannot access email",
        description="User unable to access their email account since this morning",
        urgency=TicketUrgency.HIGH,
        status=TicketStatus.CLOSED,
        department=TicketDepartment.IT,
        user_id=ObjectId("507f1f77bcf86cd799439012"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        closed_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_conversation_messages():
    """Create sample conversation messages for testing"""
    base_time = datetime.now(timezone.utc)
    
    return [
        MessageSchema(
            id="msg1",
            ticket_id="TKT-20240101-ABC123",
            sender_id="user123",
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
            sender_id="agent456",
            sender_role=MessageRole.IT_AGENT,
            message_type=MessageType.AGENT_MESSAGE,
            content="Let me help you with that. Can you try resetting your password?",
            isAI=False,
            feedback=MessageFeedback.NONE,
            timestamp=base_time
        ),
        MessageSchema(
            id="msg3",
            ticket_id="TKT-20240101-ABC123",
            sender_id="user123",
            sender_role=MessageRole.USER,
            message_type=MessageType.USER_MESSAGE,
            content="I tried that but it's still not working.",
            isAI=False,
            feedback=MessageFeedback.NONE,
            timestamp=base_time
        ),
        MessageSchema(
            id="msg4",
            ticket_id="TKT-20240101-ABC123",
            sender_id="agent456",
            sender_role=MessageRole.IT_AGENT,
            message_type=MessageType.AGENT_MESSAGE,
            content="I've reset your account on the server side. Please try logging in now.",
            isAI=False,
            feedback=MessageFeedback.UP,
            timestamp=base_time
        )
    ]


class TestTicketSummarizer:
    """Test cases for ticket summarization functionality"""

    @pytest.mark.asyncio
    async def test_summarize_closed_ticket_validation_errors(self, sample_conversation_messages):
        """Test validation errors in summarize_closed_ticket"""

        # Test with None ticket
        with pytest.raises(ValueError, match="Ticket is required for summarization"):
            await summarize_closed_ticket(None, sample_conversation_messages)

        # Test with non-closed ticket
        open_ticket = TicketModel(
            title="Test",
            description="Test",
            user_id=ObjectId(),
            status=TicketStatus.OPEN
        )

        with pytest.raises(ValueError, match="Can only summarize closed tickets"):
            await summarize_closed_ticket(open_ticket, sample_conversation_messages)

    @pytest.mark.asyncio
    @patch('app.services.ai.ticket_summarizer.ai_config')
    async def test_summarize_closed_ticket_no_api_key(self, mock_config, sample_closed_ticket, sample_conversation_messages):
        """Test summarization when no API key is configured"""
        mock_config.GOOGLE_API_KEY = None

        result = await summarize_closed_ticket(sample_closed_ticket, sample_conversation_messages)

        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.ai.ticket_summarizer.ai_config')
    @patch('app.services.ai.ticket_summarizer._summarize_with_gemini_llm')
    async def test_summarize_closed_ticket_with_ai(self, mock_llm, mock_config, sample_closed_ticket, sample_conversation_messages):
        """Test successful AI summarization"""
        mock_config.GOOGLE_API_KEY = "test-key"

        expected_summary = TicketSummary(
            issue_summary="User unable to access email due to password issues",
            resolution_summary="Agent reset the account on server side, resolving the access issue",
            department="IT",
            category="FAQ",
            confidence_score=0.9
        )

        mock_llm.return_value = expected_summary

        result = await summarize_closed_ticket(sample_closed_ticket, sample_conversation_messages)

        assert result == expected_summary
        mock_llm.assert_called_once_with(sample_closed_ticket, sample_conversation_messages)

    @pytest.mark.asyncio
    @patch('app.services.ai.ticket_summarizer.ai_config')
    @patch('app.services.ai.ticket_summarizer._summarize_with_gemini_llm')
    @patch('app.services.ai.ticket_summarizer._create_fallback_summary')
    async def test_summarize_closed_ticket_fallback_on_error(self, mock_fallback, mock_llm, mock_config, sample_closed_ticket, sample_conversation_messages):
        """Test fallback when AI summarization fails"""
        mock_config.GOOGLE_API_KEY = "test-key"
        mock_llm.side_effect = Exception("AI service error")

        fallback_summary = TicketSummary(
            issue_summary="Fallback issue summary",
            resolution_summary="Fallback resolution summary",
            department="IT",
            category="FAQ",
            confidence_score=0.5
        )
        mock_fallback.return_value = fallback_summary

        with pytest.raises(Exception, match="Ticket summarization failed"):
            await summarize_closed_ticket(sample_closed_ticket, sample_conversation_messages)

    def test_format_conversation_for_analysis_empty(self):
        """Test formatting empty conversation"""
        result = _format_conversation_for_analysis([])
        assert result == "No conversation history available."

    def test_format_conversation_for_analysis_with_messages(self, sample_conversation_messages):
        """Test formatting conversation with messages"""
        result = _format_conversation_for_analysis(sample_conversation_messages)
        
        assert "User: I can't access my email" in result
        assert "Agent: Let me help you with that" in result
        assert "Agent: I've reset your account" in result
        assert len(result.split('\n')) == 4  # Four messages

    def test_parse_llm_summary_response_valid_json(self, sample_closed_ticket):
        """Test parsing valid JSON response"""
        json_response = '''
        {
            "issue_summary": "Email access problem",
            "resolution_summary": "Password reset resolved the issue",
            "confidence_score": 0.85
        }
        '''
        
        result = _parse_llm_summary_response(json_response, sample_closed_ticket)
        
        assert result["issue_summary"] == "Email access problem"
        assert result["resolution_summary"] == "Password reset resolved the issue"
        assert result["confidence_score"] == 0.85

    def test_parse_llm_summary_response_with_markdown(self, sample_closed_ticket):
        """Test parsing JSON response wrapped in markdown"""
        markdown_response = '''```json
        {
            "issue_summary": "Email access problem",
            "resolution_summary": "Password reset resolved the issue",
            "confidence_score": 0.85
        }
        ```'''
        
        result = _parse_llm_summary_response(markdown_response, sample_closed_ticket)
        
        assert result["issue_summary"] == "Email access problem"
        assert result["resolution_summary"] == "Password reset resolved the issue"

    def test_parse_llm_summary_response_invalid_json(self, sample_closed_ticket):
        """Test parsing invalid JSON response falls back to text extraction"""
        invalid_response = "This is not JSON but mentions issue and resolution somewhere"
        
        result = _parse_llm_summary_response(invalid_response, sample_closed_ticket)
        
        assert "issue_summary" in result
        assert "resolution_summary" in result
        assert result["confidence_score"] == 0.6

    def test_create_fallback_summary_basic(self, sample_closed_ticket):
        """Test creating basic fallback summary"""
        result = _create_fallback_summary(sample_closed_ticket, [])
        
        assert isinstance(result, TicketSummary)
        assert "Cannot access email" in result.issue_summary
        assert result.department == "IT"
        assert result.category == "FAQ"
        assert result.confidence_score == 0.5

    def test_create_fallback_summary_with_agent_messages(self, sample_closed_ticket, sample_conversation_messages):
        """Test creating fallback summary with agent messages"""
        result = _create_fallback_summary(sample_closed_ticket, sample_conversation_messages)
        
        assert isinstance(result, TicketSummary)
        assert "I've reset your account" in result.resolution_summary
        assert result.department == "IT"


class TestTicketSummaryModel:
    """Test cases for TicketSummary Pydantic model"""

    def test_ticket_summary_creation(self):
        """Test creating a TicketSummary instance"""
        summary = TicketSummary(
            issue_summary="Test issue",
            resolution_summary="Test resolution",
            department="IT",
            confidence_score=0.8
        )
        
        assert summary.issue_summary == "Test issue"
        assert summary.resolution_summary == "Test resolution"
        assert summary.department == "IT"
        assert summary.category == "FAQ"  # Default value
        assert summary.confidence_score == 0.8

    def test_ticket_summary_validation(self):
        """Test TicketSummary validation"""
        # Test that we can create a valid summary
        summary = TicketSummary(
            issue_summary="Valid issue summary",
            resolution_summary="Valid resolution summary",
            department="IT",
            confidence_score=0.8
        )
        assert summary.issue_summary == "Valid issue summary"

        # Test invalid confidence score
        with pytest.raises(ValueError):
            TicketSummary(
                issue_summary="Valid issue",
                resolution_summary="Valid resolution",
                department="IT",
                confidence_score=1.5  # Invalid score > 1.0
            )
