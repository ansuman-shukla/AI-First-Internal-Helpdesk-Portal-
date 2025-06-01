"""
AI Routing Module

This module provides functionality to automatically route tickets to appropriate departments.
Uses Google Gemini LLM for intelligent department routing between IT and HR.
"""

import logging
from typing import Literal, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from app.core.ai_config import ai_config

logger = logging.getLogger(__name__)

# Department type definition
Department = Literal["IT", "HR"]


class DepartmentClassification(BaseModel):
    """Pydantic model for structured LLM response"""
    department: Department = Field(description="The department that should handle this ticket: IT or HR")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Brief explanation for the classification decision")


def assign_department(title: str, description: str) -> Department:
    """
    Assign a department (IT or HR) based on ticket title and description using Google Gemini LLM.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        Department: Either "IT" or "HR"

    Raises:
        TypeError: If title or description are not strings
    """
    # Type validation
    if not isinstance(title, str):
        raise TypeError(f"title must be a string, got {type(title).__name__}")
    if not isinstance(description, str):
        raise TypeError(f"description must be a string, got {type(description).__name__}")

    logger.info(f"Department routing requested for title: '{title[:50]}...' and description length: {len(description)}")

    # Check if LLM routing is enabled and API key is configured
    if not ai_config.GOOGLE_API_KEY:
        logger.warning("Google API key not configured, falling back to keyword-based routing")
        return _fallback_keyword_routing(title, description)

    try:
        # Use real LLM analysis
        result = _analyze_with_llm(title, description)
        logger.info(f"LLM routing complete - Title: '{title[:50]}...', Department: {result}")
        return result

    except Exception as e:
        logger.error(f"LLM routing failed: {str(e)}, falling back to keyword-based routing")
        # Fallback to keyword-based routing
        return _fallback_keyword_routing(title, description)


def _analyze_with_llm(title: str, description: str) -> Department:
    """
    Analyze ticket content using Google Gemini LLM for department routing.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        Department: Either "IT" or "HR"
    """
    logger.debug("Initializing Gemini LLM for department routing")

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
    structured_llm = llm.with_structured_output(DepartmentClassification)

    # Create system message with routing instructions
    system_message = SystemMessage(content="""You are an expert helpdesk ticket routing system. Your job is to classify tickets into either IT or HR departments based on their content.

IT Department handles:
- Computer hardware and software issues
- Network and internet connectivity problems
- Email and login issues
- System errors and technical bugs
- Software installation and updates
- Security and virus concerns
- Printer and peripheral device issues
- Database and server problems
- Website and application issues

HR Department handles:
- Payroll and salary questions
- Benefits and insurance inquiries
- Vacation and leave requests
- Employee policies and procedures
- Workplace harassment or discrimination
- Training and onboarding
- Performance reviews and evaluations
- Termination and resignation processes
- Employee complaints and grievances
- Workplace conduct issues

Analyze the ticket content and classify it with high confidence. If the content could apply to both departments, choose the most likely primary department based on the specific issue described.""")

    # Create user message with the ticket content
    user_message = HumanMessage(content=f"""Please classify this helpdesk ticket:

Title: {title}

Description: {description}

Which department (IT or HR) should handle this ticket?""")

    # Get structured response from LLM
    logger.debug("Sending routing request to Gemini LLM")

    try:
        response = structured_llm.invoke([system_message, user_message])
        logger.debug(f"Raw LLM response: {response}")

        # Extract department from structured response
        if hasattr(response, 'department'):
            department = response.department
            confidence = getattr(response, 'confidence', 0.8)
            reasoning = getattr(response, 'reasoning', 'LLM classification')

            logger.info(f"LLM routing result - Department: {department}, Confidence: {confidence}, Reasoning: {reasoning}")
            return department
        else:
            logger.error(f"Unexpected LLM response format: {response}")
            raise ValueError("Invalid LLM response format")

    except Exception as e:
        logger.error(f"Error processing LLM routing response: {str(e)}")
        raise


def _fallback_keyword_routing(title: str, description: str) -> Department:
    """
    Fallback keyword-based routing when LLM is unavailable.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        Department: Either "IT" or "HR"
    """
    logger.debug("Using fallback keyword-based routing")

    # Combine title and description for analysis
    content = f"{title} {description}".lower()

    # IT keywords
    it_keywords = [
        "computer", "laptop", "software", "hardware", "network", "internet",
        "email", "password", "login", "system", "server", "database",
        "application", "app", "website", "wifi", "printer", "monitor",
        "keyboard", "mouse", "technical", "bug", "error", "crash",
        "install", "update", "backup", "security", "virus", "malware"
    ]

    # HR keywords
    hr_keywords = [
        "payroll", "salary", "benefits", "vacation", "leave", "holiday",
        "policy", "harassment", "discrimination", "training", "onboarding",
        "performance", "review", "promotion", "termination", "resignation",
        "employee", "manager", "supervisor", "team", "department",
        "workplace", "conduct", "complaint", "grievance", "disciplinary"
    ]

    # Count keyword matches
    it_score = sum(1 for keyword in it_keywords if keyword in content)
    hr_score = sum(1 for keyword in hr_keywords if keyword in content)

    # Determine department based on keyword scores
    if it_score > hr_score:
        department = "IT"
    elif hr_score > it_score:
        department = "HR"
    else:
        # Default to IT if no clear match or tie
        department = "IT"

    logger.debug(f"Keyword routing analysis - IT score: {it_score}, HR score: {hr_score}, Assigned: {department}")
    logger.info(f"Fallback routing result: {department}")

    return department
