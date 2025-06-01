"""
Response Suggestion RAG Module

This module provides functionality to generate AI-powered response suggestions
for agents based on conversation context and ticket information.
Uses Google Gemini LLM for intelligent response generation with fallback to context analysis.
"""

import logging
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from app.schemas.message import MessageSchema, MessageRole, MessageType
from app.core.ai_config import ai_config

logger = logging.getLogger(__name__)


class ResponseSuggestion(BaseModel):
    """Pydantic model for structured LLM response suggestion"""
    response: str = Field(description="The suggested response text for the agent")
    tone: str = Field(description="The tone of the response (professional, empathetic, technical, etc.)")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Brief explanation for the response suggestion")


def response_suggestion_rag(ticket_id: str, conversation_context: List[MessageSchema]) -> str:
    """
    Generate AI-powered response suggestions for agents using RAG approach.
    
    This function analyzes the conversation context and generates appropriate
    response suggestions that agents can use to help users more effectively.
    
    Args:
        ticket_id (str): ID of the ticket for context
        conversation_context (List[MessageSchema]): List of messages providing conversation history
        
    Returns:
        str: AI-generated response suggestion
        
    Raises:
        TypeError: If parameters are not of expected types
        ValueError: If ticket_id is empty or conversation_context is invalid
        
    Note:
        This is a V1 intelligent stub implementation with context analysis.
        In future versions, this will integrate with LLM for actual RAG-based suggestions.
    """
    # Type validation
    if not isinstance(ticket_id, str):
        raise TypeError(f"ticket_id must be a string, got {type(ticket_id).__name__}")
    if not isinstance(conversation_context, list):
        raise TypeError(f"conversation_context must be a list, got {type(conversation_context).__name__}")
    
    # Value validation
    if not ticket_id.strip():
        raise ValueError("ticket_id cannot be empty")
    
    # Validate conversation context items
    for i, message in enumerate(conversation_context):
        if not isinstance(message, MessageSchema):
            raise ValueError(f"conversation_context[{i}] must be a MessageSchema instance")
    
    logger.info(
        f"Response suggestion requested for ticket {ticket_id} "
        f"with {len(conversation_context)} context messages"
    )

    # Check if LLM is available and configured
    if ai_config.GOOGLE_API_KEY:
        try:
            # Use LLM for intelligent response generation
            suggestion = _analyze_with_llm(ticket_id, conversation_context)
            logger.info(
                f"LLM response suggestion generated for ticket {ticket_id} "
                f"- Suggestion length: {len(suggestion)}"
            )
            return suggestion
        except Exception as e:
            logger.error(f"LLM response suggestion failed: {str(e)}, falling back to context analysis")
            # Fall through to context analysis fallback
    else:
        logger.warning("Google API key not configured, using context analysis fallback")

    # Fallback: Analyze conversation context and generate response
    context_analysis = _analyze_conversation_context(conversation_context)
    suggestion = _generate_response_suggestion(ticket_id, context_analysis)

    logger.info(
        f"Fallback response suggestion generated for ticket {ticket_id} "
        f"- Suggestion length: {len(suggestion)}, Context: {context_analysis['summary']}"
    )

    return suggestion


def _analyze_conversation_context(conversation_context: List[MessageSchema]) -> dict:
    """
    Analyze conversation context to understand the situation and user needs.
    
    Args:
        conversation_context: List of messages to analyze
        
    Returns:
        dict: Analysis results including patterns, sentiment, and recommendations
    """
    if not conversation_context:
        return {
            "message_count": 0,
            "user_messages": 0,
            "agent_messages": 0,
            "ai_messages": 0,
            "last_sender": None,
            "department_hints": [],
            "query_type": "general",
            "urgency_level": "medium",
            "summary": "No conversation context available"
        }
    
    # Count message types and analyze patterns
    user_messages = 0
    agent_messages = 0
    ai_messages = 0
    last_sender = None
    content_keywords = []
    
    for message in conversation_context:
        # Count by sender role
        if message.sender_role in [MessageRole.USER]:
            user_messages += 1
        elif message.sender_role in [MessageRole.IT_AGENT, MessageRole.HR_AGENT]:
            agent_messages += 1
        
        # Count AI messages
        if message.isAI:
            ai_messages += 1
            
        # Track last sender
        last_sender = message.sender_role.value
        
        # Extract keywords from content
        content_keywords.extend(message.content.lower().split())
    
    # Determine department hints based on content
    department_hints = _extract_department_hints(content_keywords)
    
    # Determine query type
    query_type = _determine_query_type(content_keywords)
    
    # Assess urgency level
    urgency_level = _assess_urgency_level(content_keywords)
    
    return {
        "message_count": len(conversation_context),
        "user_messages": user_messages,
        "agent_messages": agent_messages,
        "ai_messages": ai_messages,
        "last_sender": last_sender,
        "department_hints": department_hints,
        "query_type": query_type,
        "urgency_level": urgency_level,
        "summary": f"{query_type} query with {urgency_level} urgency"
    }


def _extract_department_hints(keywords: List[str]) -> List[str]:
    """Extract department-related hints from conversation keywords."""
    it_keywords = {
        "computer", "laptop", "software", "hardware", "network", "internet",
        "email", "password", "login", "system", "server", "database",
        "application", "app", "website", "wifi", "printer", "monitor",
        "technical", "bug", "error", "crash", "install", "update"
    }
    
    hr_keywords = {
        "payroll", "salary", "benefits", "vacation", "leave", "holiday",
        "policy", "harassment", "training", "onboarding", "performance",
        "review", "promotion", "employee", "manager", "workplace"
    }
    
    hints = []
    if any(keyword in it_keywords for keyword in keywords):
        hints.append("IT")
    if any(keyword in hr_keywords for keyword in keywords):
        hints.append("HR")
    
    return hints


def _determine_query_type(keywords: List[str]) -> str:
    """Determine the type of query based on keywords."""
    if any(word in keywords for word in ["help", "how", "can't", "unable", "problem", "issue"]):
        return "troubleshooting"
    elif any(word in keywords for word in ["policy", "procedure", "rule", "guideline"]):
        return "policy_inquiry"
    elif any(word in keywords for word in ["password", "reset", "login", "access"]):
        return "access_issue"
    elif any(word in keywords for word in ["install", "setup", "configure"]):
        return "setup_assistance"
    else:
        return "general_inquiry"


def _assess_urgency_level(keywords: List[str]) -> str:
    """Assess urgency level based on keywords."""
    urgent_keywords = {"urgent", "emergency", "critical", "asap", "immediately", "broken", "down"}
    high_keywords = {"important", "soon", "quickly", "priority", "needed"}
    
    if any(word in keywords for word in urgent_keywords):
        return "high"
    elif any(word in keywords for word in high_keywords):
        return "medium"
    else:
        return "low"


def _generate_response_suggestion(ticket_id: str, context_analysis: dict) -> str:
    """
    Generate response suggestion based on context analysis.
    
    Args:
        ticket_id: Ticket identifier
        context_analysis: Analysis results from conversation context
        
    Returns:
        str: Generated response suggestion
    """
    query_type = context_analysis["query_type"]
    urgency_level = context_analysis["urgency_level"]
    department_hints = context_analysis["department_hints"]
    last_sender = context_analysis["last_sender"]
    
    # Base greeting and acknowledgment
    if last_sender == "user":
        greeting = "Thank you for providing that information. "
    else:
        greeting = "I understand your concern. "
    
    # Generate response based on query type
    if query_type == "troubleshooting":
        suggestion = _generate_troubleshooting_response(department_hints, urgency_level)
    elif query_type == "policy_inquiry":
        suggestion = _generate_policy_response(department_hints)
    elif query_type == "access_issue":
        suggestion = _generate_access_response(department_hints)
    elif query_type == "setup_assistance":
        suggestion = _generate_setup_response(department_hints)
    else:
        suggestion = _generate_general_response(department_hints)
    
    # Add urgency-appropriate closing
    if urgency_level == "high":
        closing = " I'll prioritize this issue and work on resolving it as quickly as possible."
    elif urgency_level == "medium":
        closing = " I'll work on this and keep you updated on the progress."
    else:
        closing = " Please let me know if you need any clarification or have additional questions."
    
    return greeting + suggestion + closing


def _generate_troubleshooting_response(department_hints: List[str], urgency_level: str) -> str:
    """Generate troubleshooting-focused response."""
    if "IT" in department_hints:
        return ("Let me help you troubleshoot this technical issue. To better assist you, could you please "
                "provide more details about when this problem started and any error messages you're seeing?")
    elif "HR" in department_hints:
        return ("I'll help you resolve this HR-related issue. Let me review the relevant policies and "
                "procedures to provide you with the most accurate information.")
    else:
        return ("I'll help you troubleshoot this issue. Could you provide some additional details about "
                "the problem you're experiencing so I can offer the most appropriate solution?")


def _generate_policy_response(department_hints: List[str]) -> str:
    """Generate policy inquiry response."""
    if "HR" in department_hints:
        return ("I'll be happy to help clarify our HR policies for you. Let me review the current "
                "policy documentation to ensure I provide you with the most up-to-date information.")
    else:
        return ("I'll help you understand the relevant policies and procedures. Let me gather the "
                "appropriate documentation to give you a comprehensive answer.")


def _generate_access_response(department_hints: List[str]) -> str:
    """Generate access issue response."""
    return ("I can help you with this access issue. For security purposes, I'll need to verify your "
            "identity and then guide you through the appropriate steps to restore your access.")


def _generate_setup_response(department_hints: List[str]) -> str:
    """Generate setup assistance response."""
    if "IT" in department_hints:
        return ("I'll guide you through the setup process step by step. Let me provide you with the "
                "detailed instructions and ensure everything is configured correctly.")
    else:
        return ("I'll help you with the setup process. Let me walk you through each step to ensure "
                "everything is configured properly for your needs.")


def _generate_general_response(department_hints: List[str]) -> str:
    """Generate general inquiry response."""
    return ("I'm here to help with your inquiry. Let me gather the relevant information and "
            "provide you with a comprehensive response that addresses your specific needs.")


def _analyze_with_llm(ticket_id: str, conversation_context: List[MessageSchema]) -> str:
    """
    Analyze conversation context using Google Gemini LLM to generate response suggestions.

    Args:
        ticket_id: ID of the ticket for context
        conversation_context: List of messages providing conversation history

    Returns:
        str: LLM-generated response suggestion
    """
    logger.debug("Initializing Gemini LLM for response suggestion")

    # Initialize ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=ai_config.GEMINI_MODEL,
        temperature=ai_config.GEMINI_TEMPERATURE,
        max_tokens=ai_config.GEMINI_MAX_TOKENS,
        google_api_key=ai_config.GOOGLE_API_KEY,
        max_retries=2,
        timeout=30
    )

    # Create structured LLM with response schema
    structured_llm = llm.with_structured_output(ResponseSuggestion)

    # Format conversation history for LLM
    conversation_history = _format_conversation_for_llm(conversation_context)

    # Create system message with response generation instructions
    system_message = SystemMessage(content="""You are an expert helpdesk agent assistant. Your job is to analyze conversation history and generate professional, helpful response suggestions for agents to send to users.

Your response suggestions should be:
- Professional and empathetic in tone
- Specific and actionable when possible
- Appropriate for the conversation context
- Helpful in moving the conversation toward resolution
- Clear and easy to understand

Consider the conversation history, identify the user's needs, and suggest a response that would be most helpful. The response should sound natural and professional, as if written by an experienced support agent.

For IT issues: Focus on troubleshooting steps, technical solutions, and clear instructions.
For HR issues: Focus on policy clarification, process guidance, and empathetic support.

Always maintain a helpful, professional tone and provide specific next steps when possible.""")

    # Create user message with conversation context
    user_message = HumanMessage(content=f"""Please analyze this helpdesk conversation and suggest an appropriate response for the agent to send:

Ticket ID: {ticket_id}

Conversation History:
{conversation_history}

Generate a professional response suggestion that would be most helpful for the agent to send to the user at this point in the conversation.""")

    # Get structured response from LLM
    logger.debug("Sending response suggestion request to Gemini LLM")

    try:
        response = structured_llm.invoke([system_message, user_message])
        logger.debug(f"Raw LLM response: {response}")

        # Extract response from structured output
        if hasattr(response, 'response'):
            suggested_response = response.response
            confidence = getattr(response, 'confidence', 0.8)
            tone = getattr(response, 'tone', 'professional')
            reasoning = getattr(response, 'reasoning', 'LLM-generated suggestion')

            logger.info(f"LLM response suggestion generated - Confidence: {confidence}, Tone: {tone}, Reasoning: {reasoning}")
            return suggested_response
        else:
            logger.error(f"Unexpected LLM response format: {response}")
            raise ValueError("Invalid LLM response format")

    except Exception as e:
        logger.error(f"Error processing LLM response suggestion: {str(e)}")
        raise


def _format_conversation_for_llm(conversation_context: List[MessageSchema]) -> str:
    """
    Format conversation context for LLM analysis.

    Args:
        conversation_context: List of messages to format

    Returns:
        str: Formatted conversation history
    """
    if not conversation_context:
        return "No conversation history available."

    formatted_messages = []
    for message in conversation_context:
        # Determine sender type
        if message.sender_role == MessageRole.USER:
            sender = "User"
        elif message.sender_role in [MessageRole.IT_AGENT, MessageRole.HR_AGENT]:
            sender = f"Agent ({message.sender_role.value})"
            if message.isAI:
                sender += " [AI-Generated]"
        else:
            sender = f"System ({message.sender_role.value})"

        # Format timestamp
        timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S") if message.timestamp else "Unknown time"

        # Format message
        formatted_messages.append(f"[{timestamp}] {sender}: {message.content}")

    return "\n".join(formatted_messages)
