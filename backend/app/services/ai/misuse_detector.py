"""
Misuse Detection Module

This module provides functionality to detect misuse patterns in user ticket behavior.
Analyzes user tickets over a specified time window to identify potential spam, abuse, or system misuse.
Uses Google Gemini LLM for intelligent pattern detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bson import ObjectId
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from app.core.ai_config import ai_config
from app.core.database import get_database
from app.models.ticket import TicketModel

logger = logging.getLogger(__name__)


class MisuseAnalysisResult(BaseModel):
    """Pydantic model for misuse analysis results"""
    misuse_detected: bool = Field(..., description="Whether misuse was detected")
    patterns: List[str] = Field(default_factory=list, description="List of detected misuse patterns")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    reasoning: str = Field(default="", description="Explanation of the analysis")


async def detect_misuse_for_user(user_id: str, window_hours: int = 24) -> Dict[str, Any]:
    """
    Detect misuse patterns for a specific user by analyzing their recent tickets.
    
    Args:
        user_id (str): The user ID to analyze
        window_hours (int): Time window in hours to analyze (default: 24)
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - misuse_detected (bool): Whether misuse was detected
            - patterns (List[str]): List of detected misuse patterns
            - user_id (str): The analyzed user ID
            - analysis_date (datetime): When the analysis was performed
            - ticket_count (int): Number of tickets analyzed
            - confidence_score (float): Confidence score (0.0-1.0)
            - analysis_metadata (dict): Additional analysis metadata
            
    Raises:
        TypeError: If user_id is not a string or window_hours is not an integer
        ValueError: If user_id is empty or window_hours is not positive
    """
    # Type validation
    if not isinstance(user_id, str):
        raise TypeError(f"user_id must be a string, got {type(user_id).__name__}")
    if not isinstance(window_hours, int):
        raise TypeError(f"window_hours must be an integer, got {type(window_hours).__name__}")
    
    # Value validation
    if not user_id.strip():
        raise ValueError("user_id cannot be empty or only whitespace")
    if window_hours <= 0:
        raise ValueError("window_hours must be positive")
    
    logger.info(f"Misuse detection requested for user: {user_id}, window: {window_hours}h")
    
    try:
        # Collect user tickets from the specified time window
        tickets = await _collect_user_tickets(user_id, window_hours)
        ticket_count = len(tickets)
        
        logger.info(f"Collected {ticket_count} tickets for user {user_id} in last {window_hours}h")
        
        # Check if misuse detection is enabled and configured
        if not _is_misuse_detection_enabled():
            logger.info("Misuse detection is disabled, returning safe default")
            return _create_safe_default_result(user_id, ticket_count, "Misuse detection disabled", window_hours)

        if not ai_config.GOOGLE_API_KEY:
            logger.warning("Google API key not configured, falling back to safe default")
            return _create_safe_default_result(user_id, ticket_count, "API key not configured", window_hours)

        # Perform analysis
        if ticket_count == 0:
            logger.info(f"No tickets found for user {user_id} in last {window_hours}h")
            return _create_safe_default_result(user_id, ticket_count, "No tickets to analyze", window_hours)

        try:
            # Use real LLM analysis (V1: stub implementation)
            result = await _analyze_with_llm(user_id, tickets, window_hours)
            logger.info(f"Misuse analysis complete - User: {user_id}, Result: {result['misuse_detected']}")
            return result

        except Exception as e:
            logger.error(f"LLM misuse analysis failed: {str(e)}, falling back to safe default")
            return _create_safe_default_result(user_id, ticket_count, f"LLM analysis failed: {str(e)}", window_hours)
            
    except Exception as e:
        logger.error(f"Error in misuse detection for user {user_id}: {str(e)}")
        return _create_error_result(user_id, str(e))


async def _collect_user_tickets(user_id: str, window_hours: int) -> List[TicketModel]:
    """
    Collect tickets created by the user within the specified time window.
    
    Args:
        user_id: User ID to collect tickets for
        window_hours: Time window in hours
        
    Returns:
        List of TicketModel objects
    """
    try:
        # Calculate time window
        cutoff_time = datetime.utcnow() - timedelta(hours=window_hours)
        
        # Get database connection
        db = get_database()
        collection = db["tickets"]
        
        # Build query for user tickets within time window
        query = {
            "user_id": ObjectId(user_id),
            "created_at": {"$gte": cutoff_time}
        }
        
        logger.debug(f"Querying tickets for user {user_id} since {cutoff_time}")

        # Execute query
        cursor = collection.find(query).sort("created_at", -1)
        tickets_data = await cursor.to_list(length=None)  # Get all matching tickets
        
        # Convert to ticket models
        tickets = [TicketModel.from_dict(ticket_data) for ticket_data in tickets_data]
        
        logger.debug(f"Found {len(tickets)} tickets for user {user_id} in last {window_hours}h")
        return tickets
        
    except Exception as e:
        logger.error(f"Error collecting tickets for user {user_id}: {str(e)}")
        raise


def _is_misuse_detection_enabled() -> bool:
    """
    Check if misuse detection is enabled in configuration.
    
    Returns:
        bool: True if enabled, False otherwise
    """
    # For now, use HSA_ENABLED as a proxy for misuse detection
    # In the future, we can add a specific MISUSE_DETECTION_ENABLED config
    return ai_config.HSA_ENABLED


def _create_safe_default_result(user_id: str, ticket_count: int, reason: str, window_hours: int = 24) -> Dict[str, Any]:
    """
    Create a safe default result when analysis cannot be performed.

    Args:
        user_id: User ID being analyzed
        ticket_count: Number of tickets found
        reason: Reason for safe default
        window_hours: Time window analyzed

    Returns:
        Safe default analysis result
    """
    return {
        "misuse_detected": False,
        "patterns": [],
        "user_id": user_id,
        "analysis_date": datetime.utcnow(),
        "ticket_count": ticket_count,
        "confidence_score": 0.5,
        "analysis_metadata": {
            "detection_method": "safe_default",
            "tickets_analyzed": [],
            "reasoning": reason,
            "window_hours": window_hours
        }
    }


def _create_error_result(user_id: str, error_message: str) -> Dict[str, Any]:
    """
    Create an error result when analysis fails.
    
    Args:
        user_id: User ID being analyzed
        error_message: Error message
        
    Returns:
        Error analysis result
    """
    return {
        "misuse_detected": False,
        "patterns": [],
        "user_id": user_id,
        "analysis_date": datetime.utcnow(),
        "ticket_count": 0,
        "confidence_score": 0.0,
        "analysis_metadata": {
            "detection_method": "error",
            "tickets_analyzed": [],
            "reasoning": f"Analysis failed: {error_message}",
            "window_hours": 24
        }
    }


async def _analyze_with_llm(user_id: str, tickets: List[TicketModel], window_hours: int) -> Dict[str, Any]:
    """
    Analyze tickets using LLM for misuse detection.
    
    V1 Implementation: Stub that returns safe defaults with intelligent analysis
    Future: Will integrate with Google Gemini LLM for real pattern detection
    
    Args:
        user_id: User ID being analyzed
        tickets: List of tickets to analyze
        window_hours: Time window analyzed
        
    Returns:
        Analysis result dictionary
    """
    logger.debug(f"Performing LLM analysis for user {user_id} with {len(tickets)} tickets")
    
    # V1 Stub Implementation: Intelligent analysis based on ticket patterns
    ticket_count = len(tickets)
    ticket_ids = [str(ticket._id) if ticket._id else ticket.ticket_id for ticket in tickets]
    
    # Analyze patterns (V1: simple heuristics, future: LLM analysis)
    patterns_detected = []
    confidence_score = 0.8
    reasoning = "V1 stub analysis: "
    
    # Pattern 1: High volume (5+ tickets in 24h might indicate spam)
    if ticket_count >= 5:
        patterns_detected.append("high_volume")
        reasoning += f"High ticket volume ({ticket_count} tickets). "
    
    # Pattern 2: Duplicate titles (simple check)
    titles = [ticket.title.lower().strip() for ticket in tickets]
    if len(set(titles)) < len(titles):
        patterns_detected.append("duplicate_titles")
        reasoning += "Duplicate ticket titles detected. "
    
    # Pattern 3: Very short descriptions (potential spam)
    short_descriptions = [ticket for ticket in tickets if len(ticket.description.strip()) < 10]
    if len(short_descriptions) > ticket_count * 0.5:  # More than 50% are very short
        patterns_detected.append("short_descriptions")
        reasoning += "Many tickets with very short descriptions. "
    
    # Determine if misuse is detected (V1: conservative approach)
    misuse_detected = len(patterns_detected) >= 2  # Need at least 2 patterns for V1
    
    if not patterns_detected:
        reasoning += "No suspicious patterns detected."
        confidence_score = 0.9
    elif misuse_detected:
        reasoning += "Multiple suspicious patterns detected."
        confidence_score = 0.7
    else:
        reasoning += "Some patterns detected but below threshold."
        confidence_score = 0.6
    
    result = {
        "misuse_detected": misuse_detected,
        "patterns": patterns_detected,
        "user_id": user_id,
        "analysis_date": datetime.utcnow(),
        "ticket_count": ticket_count,
        "confidence_score": confidence_score,
        "analysis_metadata": {
            "detection_method": "llm_stub",
            "tickets_analyzed": ticket_ids,
            "reasoning": reasoning,
            "window_hours": window_hours
        }
    }
    
    if misuse_detected:
        logger.warning(f"Misuse detected for user {user_id}: {patterns_detected}")
    else:
        logger.info(f"No misuse detected for user {user_id}")
    
    return result
