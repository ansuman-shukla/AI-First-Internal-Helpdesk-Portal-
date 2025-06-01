"""
Tests for FAQ Service

This module tests the FAQ storage functionality for ticket summaries
in the vector database.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from bson import ObjectId

from app.services.faq_service import (
    FAQService,
    store_ticket_as_faq,
    get_faq_statistics
)
from app.services.ai.ticket_summarizer import TicketSummary
from app.models.ticket import TicketModel
from app.schemas.ticket import TicketStatus, TicketUrgency, TicketDepartment


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
def sample_ticket_summary():
    """Create a sample ticket summary for testing"""
    return TicketSummary(
        issue_summary="User unable to access email due to password authentication failure",
        resolution_summary="IT agent reset the user account on the server side, allowing successful login",
        department="IT",
        category="FAQ",
        confidence_score=0.9
    )


class TestFAQService:
    """Test cases for FAQ service functionality"""

    def test_faq_service_initialization(self):
        """Test FAQ service initialization"""
        service = FAQService()
        assert service.vector_store_manager is not None

    @pytest.mark.asyncio
    @patch('app.services.faq_service.get_vector_store_manager')
    async def test_store_ticket_summary_as_faq_success(self, mock_vector_store, sample_closed_ticket, sample_ticket_summary):
        """Test successful FAQ storage"""
        # Mock vector store manager
        mock_manager = Mock()
        mock_manager.add_documents.return_value = True
        mock_vector_store.return_value = mock_manager
        
        service = FAQService()
        service.vector_store_manager = mock_manager
        
        result = await service.store_ticket_summary_as_faq(sample_closed_ticket, sample_ticket_summary)
        
        assert result is True
        mock_manager.add_documents.assert_called_once()
        
        # Verify the document was created correctly
        call_args = mock_manager.add_documents.call_args[0][0]
        document = call_args[0]
        
        assert "Cannot access email" in document.page_content
        assert "password authentication failure" in document.page_content
        assert "reset the user account" in document.page_content
        assert document.metadata["source_ticket_id"] == "TKT-20240101-ABC123"
        assert document.metadata["department"] == "IT"
        assert document.metadata["category"] == "FAQ"

    @pytest.mark.asyncio
    @patch('app.services.faq_service.get_vector_store_manager')
    async def test_store_ticket_summary_as_faq_failure(self, mock_vector_store, sample_closed_ticket, sample_ticket_summary):
        """Test FAQ storage failure"""
        # Mock vector store manager to return failure
        mock_manager = Mock()
        mock_manager.add_documents.return_value = False
        mock_vector_store.return_value = mock_manager
        
        service = FAQService()
        service.vector_store_manager = mock_manager
        
        result = await service.store_ticket_summary_as_faq(sample_closed_ticket, sample_ticket_summary)
        
        assert result is False

    @pytest.mark.asyncio
    @patch('app.services.faq_service.get_vector_store_manager')
    async def test_store_ticket_summary_as_faq_exception(self, mock_vector_store, sample_closed_ticket, sample_ticket_summary):
        """Test FAQ storage with exception"""
        # Mock vector store manager to raise exception
        mock_manager = Mock()
        mock_manager.add_documents.side_effect = Exception("Vector store error")
        mock_vector_store.return_value = mock_manager
        
        service = FAQService()
        service.vector_store_manager = mock_manager
        
        result = await service.store_ticket_summary_as_faq(sample_closed_ticket, sample_ticket_summary)
        
        assert result is False

    def test_create_faq_content(self, sample_closed_ticket, sample_ticket_summary):
        """Test FAQ content creation"""
        service = FAQService()
        content = service._create_faq_content(sample_closed_ticket, sample_ticket_summary)
        
        assert "FAQ: Cannot access email" in content
        assert "ISSUE:" in content
        assert "password authentication failure" in content
        assert "RESOLUTION:" in content
        assert "reset the user account" in content
        assert "DEPARTMENT: IT" in content
        assert "URGENCY: high" in content
        assert "TKT-20240101-ABC123" in content

    def test_create_faq_metadata(self, sample_closed_ticket, sample_ticket_summary):
        """Test FAQ metadata creation"""
        service = FAQService()
        metadata = service._create_faq_metadata(sample_closed_ticket, sample_ticket_summary)
        
        assert metadata["source_type"] == "ticket_summary"
        assert metadata["source_ticket_id"] == "TKT-20240101-ABC123"
        assert metadata["source_ticket_object_id"] == str(sample_closed_ticket._id)
        assert metadata["category"] == "FAQ"
        assert metadata["department"] == "IT"
        assert metadata["urgency"] == "high"
        assert metadata["confidence_score"] == 0.9
        assert metadata["title"] == "Cannot access email"
        assert "created_at" in metadata
        assert "ticket_created_at" in metadata
        assert "ticket_closed_at" in metadata

    def test_create_faq_metadata_long_description(self, sample_ticket_summary):
        """Test FAQ metadata creation with long description"""
        long_description = "A" * 300  # Description longer than 200 chars
        
        ticket = TicketModel(
            _id=ObjectId("507f1f77bcf86cd799439011"),
            ticket_id="TKT-20240101-ABC123",
            title="Test ticket",
            description=long_description,
            urgency=TicketUrgency.LOW,
            status=TicketStatus.CLOSED,
            department=TicketDepartment.HR,
            user_id=ObjectId("507f1f77bcf86cd799439012")
        )
        
        service = FAQService()
        metadata = service._create_faq_metadata(ticket, sample_ticket_summary)
        
        # Should truncate description to 200 chars + "..."
        assert len(metadata["original_description"]) == 203
        assert metadata["original_description"].endswith("...")

    @pytest.mark.asyncio
    async def test_get_faq_stats(self):
        """Test getting FAQ statistics"""
        service = FAQService()
        stats = await service.get_faq_stats()
        
        # Currently returns placeholder data
        assert "total_faqs" in stats
        assert "by_department" in stats
        assert "last_updated" in stats

    @pytest.mark.asyncio
    async def test_get_faq_stats_with_error(self):
        """Test getting FAQ statistics with error"""
        service = FAQService()

        # Mock the vector store to raise an exception
        with patch.object(service.vector_store_manager, 'get_stats', side_effect=Exception("Stats error")):
            stats = await service.get_faq_stats()

            # Should return placeholder data since stats method doesn't handle errors yet
            assert "total_faqs" in stats
            assert "by_department" in stats


class TestFAQServiceConvenienceFunctions:
    """Test cases for FAQ service convenience functions"""

    @pytest.mark.asyncio
    @patch('app.services.faq_service.faq_service')
    async def test_store_ticket_as_faq(self, mock_service, sample_closed_ticket, sample_ticket_summary):
        """Test convenience function for storing ticket as FAQ"""
        mock_service.store_ticket_summary_as_faq = AsyncMock(return_value=True)
        
        result = await store_ticket_as_faq(sample_closed_ticket, sample_ticket_summary)
        
        assert result is True
        mock_service.store_ticket_summary_as_faq.assert_called_once_with(
            sample_closed_ticket, sample_ticket_summary
        )

    @pytest.mark.asyncio
    @patch('app.services.faq_service.faq_service')
    async def test_get_faq_statistics(self, mock_service):
        """Test convenience function for getting FAQ statistics"""
        expected_stats = {"total_faqs": 10, "by_department": {"IT": 6, "HR": 4}}
        mock_service.get_faq_stats = AsyncMock(return_value=expected_stats)
        
        result = await get_faq_statistics()
        
        assert result == expected_stats
        mock_service.get_faq_stats.assert_called_once()


class TestFAQIntegration:
    """Integration tests for FAQ functionality"""

    @pytest.mark.asyncio
    @patch('app.services.faq_service.get_vector_store_manager')
    async def test_end_to_end_faq_storage(self, mock_vector_store, sample_closed_ticket, sample_ticket_summary):
        """Test end-to-end FAQ storage process"""
        # Mock successful vector store
        mock_manager = Mock()
        mock_manager.add_documents.return_value = True
        mock_manager._initialized = True  # Mock that vector store is initialized
        mock_vector_store.return_value = mock_manager

        # Test the convenience function
        result = await store_ticket_as_faq(sample_closed_ticket, sample_ticket_summary)

        assert result is True
        
        # Verify the document structure
        call_args = mock_manager.add_documents.call_args[0][0]
        document = call_args[0]
        
        # Check content structure
        content_lines = document.page_content.split('\n')
        assert any("FAQ:" in line for line in content_lines)
        assert any("ISSUE:" in line for line in content_lines)
        assert any("RESOLUTION:" in line for line in content_lines)
        assert any("DEPARTMENT:" in line for line in content_lines)
        
        # Check metadata completeness
        required_metadata_keys = [
            "document_id", "source_type", "source_ticket_id", "category",
            "department", "urgency", "confidence_score", "created_at", "title"
        ]
        for key in required_metadata_keys:
            assert key in document.metadata

    def test_faq_content_format_consistency(self, sample_closed_ticket, sample_ticket_summary):
        """Test that FAQ content format is consistent and searchable"""
        service = FAQService()
        content = service._create_faq_content(sample_closed_ticket, sample_ticket_summary)
        
        # Verify consistent format for RAG retrieval
        assert content.startswith("FAQ:")
        assert "\nISSUE:\n" in content
        assert "\nRESOLUTION:\n" in content
        assert "\nDEPARTMENT:" in content
        assert "\nURGENCY:" in content
        assert "\nCATEGORY:" in content
        
        # Verify it contains searchable keywords
        assert "email" in content.lower()
        assert "password" in content.lower()
        assert "reset" in content.lower()
