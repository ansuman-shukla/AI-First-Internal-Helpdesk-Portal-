"""
FAQ Service

This service handles storing ticket summaries as FAQ documents in the vector database.
Provides functionality to add, retrieve, and manage FAQ entries from closed tickets.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from langchain_core.documents import Document
from app.services.ai.vector_store import get_vector_store_manager
from app.services.ai.ticket_summarizer import TicketSummary
from app.models.ticket import TicketModel

logger = logging.getLogger(__name__)


class FAQService:
    """Service for managing FAQ documents in the vector database"""
    
    def __init__(self):
        self.vector_store_manager = get_vector_store_manager()
    
    async def store_ticket_summary_as_faq(
        self,
        ticket: TicketModel,
        summary: TicketSummary
    ) -> bool:
        """
        Store a ticket summary as an FAQ document in the vector database.

        Args:
            ticket: The original ticket
            summary: The AI-generated summary

        Returns:
            bool: True if successfully stored, False otherwise
        """
        try:
            logger.info(f"Storing FAQ for ticket {ticket.ticket_id}")

            # Ensure vector store is initialized
            if not self.vector_store_manager._initialized:
                logger.info("Vector store not initialized, attempting to initialize")
                if not self.vector_store_manager.initialize():
                    logger.error("Failed to initialize vector store")
                    return False

            # Create FAQ document content
            faq_content = self._create_faq_content(ticket, summary)

            # Create metadata for the document
            metadata = self._create_faq_metadata(ticket, summary)

            # Create LangChain Document
            faq_document = Document(
                page_content=faq_content,
                metadata=metadata
            )

            # Store in vector database
            success = self.vector_store_manager.add_documents([faq_document])

            if success:
                logger.info(f"Successfully stored FAQ for ticket {ticket.ticket_id}")
                return True
            else:
                logger.error(f"Failed to store FAQ for ticket {ticket.ticket_id}")
                return False

        except Exception as e:
            logger.error(f"Error storing FAQ for ticket {ticket.ticket_id}: {str(e)}")
            return False
    
    def _create_faq_content(self, ticket: TicketModel, summary: TicketSummary) -> str:
        """
        Create the FAQ content text for vector storage.
        
        Args:
            ticket: The original ticket
            summary: The AI-generated summary
            
        Returns:
            Formatted FAQ content string
        """
        # Create a comprehensive FAQ entry
        faq_content = f"""FAQ: {ticket.title}

ISSUE:
{summary.issue_summary}

RESOLUTION:
{summary.resolution_summary}

DEPARTMENT: {summary.department}
URGENCY: {ticket.urgency.value}
CATEGORY: {summary.category}

This FAQ was generated from ticket {ticket.ticket_id} which was successfully resolved.
"""
        
        return faq_content
    
    def _create_faq_metadata(self, ticket: TicketModel, summary: TicketSummary) -> Dict[str, Any]:
        """
        Create metadata for the FAQ document.
        
        Args:
            ticket: The original ticket
            summary: The AI-generated summary
            
        Returns:
            Dictionary containing document metadata
        """
        return {
            "document_id": f"faq_{ticket.ticket_id}_{uuid.uuid4().hex[:8]}",
            "source_type": "ticket_summary",
            "source_ticket_id": ticket.ticket_id,
            "source_ticket_object_id": str(ticket._id) if ticket._id else None,
            "category": summary.category,
            "department": summary.department,
            "urgency": ticket.urgency.value,
            "confidence_score": summary.confidence_score,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ticket_created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "ticket_closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
            "title": ticket.title,
            "original_description": ticket.description[:200] + "..." if len(ticket.description) > 200 else ticket.description
        }
    
    async def get_faq_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored FAQ documents.
        
        Returns:
            Dictionary with FAQ statistics
        """
        try:
            # This would require implementing a stats method in vector store
            # For now, return basic info
            logger.info("Getting FAQ statistics")
            
            return {
                "total_faqs": "Not implemented yet",
                "by_department": "Not implemented yet",
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting FAQ stats: {str(e)}")
            return {
                "error": str(e),
                "total_faqs": 0
            }


# Global FAQ service instance
faq_service = FAQService()


async def store_ticket_as_faq(ticket: TicketModel, summary: TicketSummary) -> bool:
    """
    Convenience function to store a ticket summary as FAQ.
    
    Args:
        ticket: The closed ticket
        summary: The AI-generated summary
        
    Returns:
        bool: True if successfully stored
    """
    return await faq_service.store_ticket_summary_as_faq(ticket, summary)


async def get_faq_statistics() -> Dict[str, Any]:
    """
    Convenience function to get FAQ statistics.
    
    Returns:
        Dictionary with FAQ statistics
    """
    return await faq_service.get_faq_stats()
