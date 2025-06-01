"""
Ticket Summarization Service

This service provides AI-powered summarization of closed tickets for FAQ generation.
Analyzes ticket content and conversation history to create structured summaries
that can be stored in the RAG knowledge base.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from app.core.ai_config import ai_config
from app.models.ticket import TicketModel
from app.schemas.message import MessageSchema

logger = logging.getLogger(__name__)


class TicketSummary(BaseModel):
    """Structured ticket summary for FAQ storage"""

    issue_summary: str = Field(..., min_length=1, description="Summary of the reported issue")
    resolution_summary: str = Field(..., min_length=1, description="Summary of how the issue was resolved")
    department: str = Field(..., description="Department that handled the ticket")
    category: str = Field(default="FAQ", description="Category for knowledge base storage")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence in the summary quality")


async def summarize_closed_ticket(
    ticket: TicketModel,
    conversation_messages: List[MessageSchema]
) -> Optional[TicketSummary]:
    """
    Summarize a closed ticket and its conversation history for FAQ storage.
    
    Args:
        ticket: The closed ticket to summarize
        conversation_messages: List of all messages in the ticket conversation
        
    Returns:
        TicketSummary object or None if summarization fails
        
    Raises:
        ValueError: If ticket is not closed or required data is missing
        Exception: If AI analysis fails
    """
    # Validate inputs
    if not ticket:
        raise ValueError("Ticket is required for summarization")
    
    if ticket.status.value != "closed":
        raise ValueError(f"Can only summarize closed tickets, got status: {ticket.status.value}")
    
    logger.info(f"Starting summarization for closed ticket {ticket.ticket_id}")
    
    try:
        # Check if AI is enabled and configured
        if not ai_config.GOOGLE_API_KEY:
            logger.warning("Google API key not configured, cannot perform AI summarization")
            return None
        
        # Use AI to generate summary
        if ai_config.GOOGLE_API_KEY:
            logger.info("Using Gemini LLM for ticket summarization")
            summary = await _summarize_with_gemini_llm(ticket, conversation_messages)
        else:
            logger.warning("AI not available, using fallback summarization")
            summary = _create_fallback_summary(ticket, conversation_messages)
        
        logger.info(f"Successfully summarized ticket {ticket.ticket_id}")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to summarize ticket {ticket.ticket_id}: {str(e)}")
        raise Exception(f"Ticket summarization failed: {str(e)}")


async def _summarize_with_gemini_llm(
    ticket: TicketModel,
    conversation_messages: List[MessageSchema]
) -> TicketSummary:
    """
    Use Google Gemini LLM to generate ticket summary.
    
    Args:
        ticket: The ticket to summarize
        conversation_messages: Conversation history
        
    Returns:
        TicketSummary with AI-generated content
    """
    logger.debug("Initializing Gemini LLM for ticket summarization")
    
    # Initialize ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=ai_config.GEMINI_MODEL,
        temperature=0.3,  # Lower temperature for more consistent summaries
        max_tokens=ai_config.GEMINI_MAX_TOKENS,
        google_api_key=ai_config.GOOGLE_API_KEY,
        max_retries=2,
        timeout=30
    )
    
    # Prepare conversation context
    conversation_text = _format_conversation_for_analysis(conversation_messages)
    
    # Create system message for summarization
    system_message = SystemMessage(content="""You are an expert at analyzing helpdesk tickets and creating concise, useful FAQ summaries.

Your task is to analyze a closed helpdesk ticket and create a structured summary that will be useful for future reference.

Focus on:
1. ISSUE SUMMARY: What was the core problem or request? (2-3 sentences max)
2. RESOLUTION SUMMARY: How was the issue resolved? What steps were taken? (3-4 sentences max)

Guidelines:
- Be concise but comprehensive
- Focus on actionable information
- Use clear, professional language
- Avoid personal details or names
- Include technical details that might help with similar issues
- Make it useful for both users and agents

Respond with a JSON object containing:
{
  "issue_summary": "Brief description of the problem",
  "resolution_summary": "Clear explanation of how it was resolved",
  "confidence_score": 0.85
}""")
    
    # Create user message with ticket data
    user_message = HumanMessage(content=f"""Please analyze this closed helpdesk ticket and create a FAQ summary:

TICKET DETAILS:
- Ticket ID: {ticket.ticket_id}
- Title: {ticket.title}
- Description: {ticket.description}
- Department: {ticket.department.value if ticket.department else 'Unknown'}
- Urgency: {ticket.urgency.value}

CONVERSATION HISTORY:
{conversation_text}

Please provide a structured summary suitable for FAQ storage.""")
    
    # Get response from LLM
    logger.debug("Sending summarization request to Gemini LLM")
    
    try:
        response = llm.invoke([system_message, user_message])
        logger.debug(f"Received LLM response for ticket {ticket.ticket_id}")
        
        # Parse the response (assuming it returns JSON-like content)
        summary_data = _parse_llm_summary_response(response.content, ticket)
        
        return TicketSummary(
            issue_summary=summary_data["issue_summary"],
            resolution_summary=summary_data["resolution_summary"],
            department=ticket.department.value if ticket.department else "General",
            category="FAQ",
            confidence_score=summary_data.get("confidence_score", 0.8)
        )
        
    except Exception as e:
        logger.error(f"Error in LLM summarization: {str(e)}")
        # Fall back to rule-based summary
        return _create_fallback_summary(ticket, conversation_messages)


def _format_conversation_for_analysis(messages: List[MessageSchema]) -> str:
    """
    Format conversation messages for LLM analysis.
    
    Args:
        messages: List of conversation messages
        
    Returns:
        Formatted conversation text
    """
    if not messages:
        return "No conversation history available."
    
    formatted_lines = []
    
    for msg in messages:
        # Format timestamp
        timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")
        
        # Determine sender type
        sender_type = "User" if msg.sender_role.value == "user" else "Agent"
        if msg.isAI:
            sender_type = "AI Agent"
        
        # Add message
        formatted_lines.append(f"[{timestamp}] {sender_type}: {msg.content}")
    
    return "\n".join(formatted_lines)


def _parse_llm_summary_response(response_content: str, ticket: TicketModel) -> Dict[str, Any]:
    """
    Parse LLM response content into structured summary data.
    
    Args:
        response_content: Raw LLM response
        ticket: Original ticket for fallback data
        
    Returns:
        Dictionary with summary components
    """
    try:
        # Try to parse as JSON first
        import json
        
        # Clean up the response (remove markdown formatting if present)
        cleaned_content = response_content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        cleaned_content = cleaned_content.strip()
        
        parsed_data = json.loads(cleaned_content)
        
        # Validate required fields
        if "issue_summary" not in parsed_data or "resolution_summary" not in parsed_data:
            raise ValueError("Missing required summary fields")
        
        return parsed_data
        
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as JSON: {str(e)}, using fallback parsing")
        
        # Fallback: extract key information from text
        lines = response_content.split('\n')
        issue_summary = f"Issue: {ticket.title}"
        resolution_summary = "Resolution details available in conversation history."
        
        # Try to extract better summaries from the text
        for line in lines:
            line = line.strip()
            if "issue" in line.lower() and len(line) > 20:
                issue_summary = line
            elif "resolution" in line.lower() and len(line) > 20:
                resolution_summary = line
        
        return {
            "issue_summary": issue_summary,
            "resolution_summary": resolution_summary,
            "confidence_score": 0.6  # Lower confidence for fallback parsing
        }


def _create_fallback_summary(
    ticket: TicketModel,
    conversation_messages: List[MessageSchema]
) -> TicketSummary:
    """
    Create a basic summary when AI is not available.
    
    Args:
        ticket: The ticket to summarize
        conversation_messages: Conversation history
        
    Returns:
        Basic TicketSummary
    """
    logger.info(f"Creating fallback summary for ticket {ticket.ticket_id}")
    
    # Basic issue summary from ticket data
    issue_summary = f"Issue: {ticket.title}. {ticket.description[:200]}..."
    
    # Try to extract resolution from agent messages
    resolution_summary = "Ticket was resolved through agent assistance."
    
    agent_messages = [msg for msg in conversation_messages 
                     if msg.sender_role.value in ["it_agent", "hr_agent", "admin"]]
    
    if agent_messages:
        # Use the last few agent messages as resolution context
        last_agent_msg = agent_messages[-1]
        resolution_summary = f"Resolution: {last_agent_msg.content[:200]}..."
    
    return TicketSummary(
        issue_summary=issue_summary,
        resolution_summary=resolution_summary,
        department=ticket.department.value if ticket.department else "General",
        category="FAQ",
        confidence_score=0.5  # Lower confidence for fallback
    )
