"""
Harmful/Spam Analysis (HSA) Module

This module provides functionality to analyze ticket content for harmful or spam content.
Uses Google Gemini LLM for real-time harmful content detection.
"""

import logging
from typing import Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory, HarmCategory
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from app.core.ai_config import ai_config

logger = logging.getLogger(__name__)


class HSAAnalysisResult(BaseModel):
    """Structured output for HSA analysis"""
    is_harmful: bool = Field(..., description="True if content is harmful/spam, False otherwise")
    confidence: float = Field(..., description="Confidence score between 0 and 1")
    reason: str = Field(..., description="Brief explanation of the decision")


def check_harmful(title: str, description: str) -> bool:
    """
    Check if the given title and description contain harmful or spam content using Google Gemini LLM.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        bool: True if content is harmful/spam, False otherwise

    Raises:
        TypeError: If title or description are not strings
    """
    # Type validation
    if not isinstance(title, str):
        raise TypeError(f"title must be a string, got {type(title).__name__}")
    if not isinstance(description, str):
        raise TypeError(f"description must be a string, got {type(description).__name__}")

    logger.info(f"HSA check requested for title: '{title[:50]}...' and description length: {len(description)}")

    # Check if HSA is enabled and API key is configured
    if not ai_config.HSA_ENABLED:
        logger.info("HSA is disabled, returning False (safe)")
        return False

    if not ai_config.GOOGLE_API_KEY:
        logger.warning("Google API key not configured, falling back to safe default")
        return False

    try:
        # Use real LLM analysis
        result = _analyze_with_llm(title, description)
        logger.info(f"HSA analysis complete - Title: '{title[:50]}...', Result: {result}")
        return result

    except Exception as e:
        logger.error(f"HSA LLM analysis failed: {str(e)}, falling back to safe default")
        # Fallback to safe default (False = not harmful)
        return False


def _analyze_with_llm(title: str, description: str) -> bool:
    """
    Analyze content using Google Gemini LLM for harmful/spam detection.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        bool: True if content is harmful/spam, False otherwise

    Raises:
        Exception: If LLM analysis fails
    """
    logger.debug(f"Starting LLM analysis for title: '{title[:50]}...'")

    # Initialize ChatGoogleGenerativeAI with safety settings
    llm = ChatGoogleGenerativeAI(
        model=ai_config.GEMINI_MODEL,
        temperature=ai_config.GEMINI_TEMPERATURE,
        max_tokens=ai_config.GEMINI_MAX_TOKENS,
        google_api_key=ai_config.GOOGLE_API_KEY,
        max_retries=2,
        timeout=30,
        # Configure safety settings to allow analysis of potentially harmful content
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    )

    # Create structured LLM for consistent output
    structured_llm = llm.with_structured_output(HSAAnalysisResult)

    # Create system prompt for harmful content detection
    system_message = SystemMessage(content="""You are a content moderation AI for an internal helpdesk system.

Your task is to analyze ticket content and determine if it contains:
1. SPAM CONTENT: promotional language, sales pitches, irrelevant marketing, "buy now", "click here", "free money", etc.
2. HARMFUL CONTENT: harassment, threats, profanity, inappropriate language, hate speech
3. SYSTEM MISUSE: personal requests, non-work related content, dating, social media, entertainment

IMPORTANT: You must respond with a JSON object containing exactly these fields:
{
  "is_harmful": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}

Examples of HARMFUL content to flag:
- "Buy now! Limited time offer!"
- "Click here for free money!"
- "F*** you, this is stupid"
- "Can you help me with my dating profile?"
- "Where can I download movies?"

Examples of SAFE content:
- "My printer is not working"
- "I forgot my password"
- "Need help with software installation"

Be strict - flag anything that looks like spam, contains profanity, or is clearly not work-related.""")

    # Create user message with the content to analyze
    user_message = HumanMessage(content=f"""Please analyze this helpdesk ticket:

    Title: {title}

    Description: {description}

    Is this content harmful, spam, or inappropriate for an internal helpdesk system?""")

    # Get structured response from LLM
    logger.debug("Sending request to Gemini LLM")

    try:
        response = structured_llm.invoke([system_message, user_message])
        logger.debug(f"Raw LLM response type: {type(response)}")
        logger.debug(f"Raw LLM response: {response}")

        # Handle different response types
        if hasattr(response, 'is_harmful'):
            # Structured response worked
            is_harmful = response.is_harmful
            confidence = getattr(response, 'confidence', 0.5)
            reason = getattr(response, 'reason', 'No reason provided')
            logger.debug(f"Structured response: is_harmful={is_harmful}, confidence={confidence}, reason='{reason}'")
        else:
            # Fallback: try to parse text response
            logger.warning("Structured response failed, attempting to parse text response")
            response_text = str(response)
            if hasattr(response, 'content'):
                response_text = response.content
            elif hasattr(response, 'text'):
                response_text = response.text

            logger.debug(f"Response text: {response_text}")

            # Simple text parsing for harmful content detection
            response_lower = response_text.lower()
            is_harmful = any(keyword in response_lower for keyword in [
                'harmful', 'spam', 'inappropriate', 'flagged', 'violation', 'true'
            ]) and not any(keyword in response_lower for keyword in [
                'not harmful', 'not spam', 'not inappropriate', 'legitimate', 'false'
            ])

            confidence = 0.8 if is_harmful else 0.9  # Default confidence
            reason = f"Parsed from text response: {response_text[:100]}..."

            logger.info(f"Text parsing result: is_harmful={is_harmful}, confidence={confidence}")

        # Apply confidence threshold
        if confidence < ai_config.HSA_CONFIDENCE_THRESHOLD:
            logger.info(f"LLM confidence {confidence} below threshold {ai_config.HSA_CONFIDENCE_THRESHOLD}, defaulting to safe")
            return False

        if is_harmful:
            logger.warning(f"LLM detected harmful content with confidence {confidence}: {reason}")
        else:
            logger.info(f"LLM determined content is safe with confidence {confidence}: {reason}")

        return is_harmful

    except Exception as e:
        logger.error(f"Error processing LLM response: {str(e)}")
        # Fallback to simple text analysis
        return _fallback_text_analysis(title, description)


def _fallback_text_analysis(title: str, description: str) -> bool:
    """
    Fallback text analysis when LLM fails.

    Uses simple keyword-based detection for obvious spam/harmful content.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        bool: True if content appears harmful/spam, False otherwise
    """
    logger.info("Using fallback text analysis for HSA")

    # Combine title and description for analysis
    content = f"{title} {description}".lower()

    # Obvious spam/harmful keywords
    harmful_keywords = [
        'buy now', 'click here', 'free money', 'urgent action required',
        'limited time offer', 'act now', 'guaranteed', 'make money fast',
        'work from home', 'no experience needed', 'earn $', 'get rich',
        'viagra', 'casino', 'lottery', 'winner', 'congratulations you won',
        'nigerian prince', 'inheritance', 'transfer money', 'bank account',
        'fuck', 'shit', 'damn you', 'go to hell', 'kill yourself',
        'hate you', 'stupid idiot', 'moron', 'retard', 'loser'
    ]

    # Check for harmful keywords
    harmful_count = sum(1 for keyword in harmful_keywords if keyword in content)

    # If multiple harmful keywords found, likely spam/harmful
    if harmful_count >= 2:
        logger.warning(f"Fallback analysis detected {harmful_count} harmful keywords in content")
        return True

    # Check for excessive promotional language patterns
    promotional_patterns = ['!', '$', 'free', 'now', 'urgent', 'limited']
    promotional_count = sum(content.count(pattern) for pattern in promotional_patterns)

    if promotional_count >= 5:
        logger.warning(f"Fallback analysis detected excessive promotional language (score: {promotional_count})")
        return True

    logger.info("Fallback analysis determined content is safe")
    return False


def check_harmful_detailed(title: str, description: str) -> dict:
    """
    Check if the given title and description contain harmful or spam content with detailed results.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        dict: Dictionary with keys:
            - is_harmful (bool): True if content is harmful/spam, False otherwise
            - confidence (float): Confidence score between 0 and 1
            - reason (str): Explanation of the decision
            - content_type (str): Type of harmful content (profanity, spam, inappropriate)

    Raises:
        TypeError: If title or description are not strings
    """
    # Type validation
    if not isinstance(title, str):
        raise TypeError(f"title must be a string, got {type(title).__name__}")
    if not isinstance(description, str):
        raise TypeError(f"description must be a string, got {type(description).__name__}")

    logger.info(f"HSA detailed check requested for title: '{title[:50]}...' and description length: {len(description)}")

    # Check if HSA is enabled and API key is configured
    if not ai_config.HSA_ENABLED:
        logger.info("HSA is disabled, returning safe result")
        return {
            "is_harmful": False,
            "confidence": 1.0,
            "reason": "HSA is disabled",
            "content_type": "none"
        }

    if not ai_config.GOOGLE_API_KEY:
        logger.warning("Google API key not configured, falling back to safe default")
        return {
            "is_harmful": False,
            "confidence": 0.5,
            "reason": "API key not configured, using safe default",
            "content_type": "none"
        }

    try:
        # Use real LLM analysis
        result = _analyze_with_llm_detailed(title, description)
        logger.info(f"HSA detailed analysis complete - Title: '{title[:50]}...', Result: {result}")
        return result

    except Exception as e:
        logger.error(f"HSA LLM detailed analysis failed: {str(e)}, falling back to safe default")
        # Fallback to safe default
        return {
            "is_harmful": False,
            "confidence": 0.5,
            "reason": f"LLM analysis failed: {str(e)}",
            "content_type": "error"
        }


def _analyze_with_llm_detailed(title: str, description: str) -> dict:
    """
    Analyze content using Google Gemini LLM for harmful/spam detection with detailed results.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        dict: Dictionary with detailed analysis results

    Raises:
        Exception: If LLM analysis fails
    """
    logger.debug(f"Starting detailed LLM analysis for title: '{title[:50]}...'")

    # Initialize ChatGoogleGenerativeAI with safety settings
    llm = ChatGoogleGenerativeAI(
        model=ai_config.GEMINI_MODEL,
        temperature=ai_config.GEMINI_TEMPERATURE,
        max_tokens=ai_config.GEMINI_MAX_TOKENS,
        google_api_key=ai_config.GOOGLE_API_KEY,
        max_retries=2,
        timeout=30,
        # Configure safety settings to allow analysis of potentially harmful content
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    )

    # Create structured LLM for consistent output
    structured_llm = llm.with_structured_output(HSAAnalysisResult)

    # Create system prompt for harmful content detection
    system_message = SystemMessage(content="""You are a content moderation AI for an internal helpdesk system.

Your task is to analyze ticket content and determine if it contains:
1. SPAM CONTENT: promotional language, sales pitches, irrelevant marketing, "buy now", "click here", "free money", etc.
2. HARMFUL CONTENT: harassment, threats, profanity, inappropriate language, hate speech
3. SYSTEM MISUSE: personal requests, non-work related content, dating, social media, entertainment

IMPORTANT: You must respond with a JSON object containing exactly these fields:
{
  "is_harmful": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}

Examples of HARMFUL content to flag:
- "Buy now! Limited time offer!"
- "Click here for free money!"
- "F*** you, this is stupid"
- "Can you help me with my dating profile?"
- "Where can I download movies?"

Examples of SAFE content:
- "My printer is not working"
- "I forgot my password"
- "Need help with software installation"

Be strict - flag anything that looks like spam, contains profanity, or is clearly not work-related.""")

    # Create user message with the content to analyze
    user_message = HumanMessage(content=f"""Please analyze this helpdesk ticket:

Title: {title}

Description: {description}

Is this content harmful, spam, or inappropriate for an internal helpdesk system?""")

    # Get structured response from LLM
    logger.debug("Sending request to Gemini LLM for detailed analysis")

    try:
        response = structured_llm.invoke([system_message, user_message])
        logger.debug(f"Raw LLM response type: {type(response)}")
        logger.debug(f"Raw LLM response: {response}")

        # Handle different response types
        if hasattr(response, 'is_harmful'):
            # Structured response worked
            is_harmful = response.is_harmful
            confidence = getattr(response, 'confidence', 0.5)
            reason = getattr(response, 'reason', 'No reason provided')
            logger.debug(f"Structured response: is_harmful={is_harmful}, confidence={confidence}, reason='{reason}'")
        else:
            # Fallback: try to parse text response
            logger.warning("Structured response failed, attempting to parse text response")
            response_text = str(response)
            if hasattr(response, 'content'):
                response_text = response.content
            elif hasattr(response, 'text'):
                response_text = response.text

            logger.debug(f"Response text: {response_text}")

            # Simple text parsing for harmful content detection
            response_lower = response_text.lower()
            is_harmful = any(keyword in response_lower for keyword in [
                'harmful', 'spam', 'inappropriate', 'flagged', 'violation', 'true'
            ]) and not any(keyword in response_lower for keyword in [
                'not harmful', 'not spam', 'not inappropriate', 'legitimate', 'false'
            ])

            confidence = 0.8 if is_harmful else 0.9  # Default confidence
            reason = f"Parsed from text response: {response_text[:100]}..."

            logger.info(f"Text parsing result: is_harmful={is_harmful}, confidence={confidence}")

        # Apply confidence threshold
        if confidence < ai_config.HSA_CONFIDENCE_THRESHOLD:
            logger.info(f"LLM confidence {confidence} below threshold {ai_config.HSA_CONFIDENCE_THRESHOLD}, defaulting to safe")
            is_harmful = False
            reason = f"Low confidence ({confidence}), defaulting to safe"

        # Determine content type based on reason
        content_type = "none"
        if is_harmful:
            reason_lower = reason.lower()
            if any(word in reason_lower for word in ['profanity', 'inappropriate language', 'offensive', 'harassment', 'hate']):
                content_type = "profanity"
            elif any(word in reason_lower for word in ['spam', 'promotional', 'marketing', 'advertisement', 'sales']):
                content_type = "spam"
            else:
                content_type = "inappropriate"

        result = {
            "is_harmful": is_harmful,
            "confidence": confidence,
            "reason": reason,
            "content_type": content_type
        }

        if is_harmful:
            logger.warning(f"LLM detected harmful content: {result}")
        else:
            logger.info(f"LLM determined content is safe: {result}")

        return result

    except Exception as e:
        logger.error(f"Error processing detailed LLM response: {str(e)}")
        # Fallback to simple text analysis
        return _fallback_text_analysis_detailed(title, description)


def _fallback_text_analysis_detailed(title: str, description: str) -> dict:
    """
    Fallback text analysis when LLM fails, with detailed results.

    Uses simple keyword-based detection for obvious spam/harmful content.

    Args:
        title (str): The ticket title to analyze
        description (str): The ticket description to analyze

    Returns:
        dict: Dictionary with detailed analysis results
    """
    logger.info("Using fallback text analysis for detailed HSA")

    # Combine title and description for analysis
    content = f"{title} {description}".lower()

    # Obvious spam/harmful keywords
    harmful_keywords = [
        'buy now', 'click here', 'free money', 'urgent action required',
        'limited time offer', 'act now', 'guaranteed', 'make money fast',
        'work from home', 'no experience needed', 'earn $', 'get rich',
        'viagra', 'casino', 'lottery', 'winner', 'congratulations you won',
        'nigerian prince', 'inheritance', 'transfer money',
        'fuck', 'shit', 'damn you', 'go to hell', 'kill yourself',
        'hate you', 'stupid idiot', 'moron', 'retard', 'loser'
    ]

    # Check for harmful keywords
    harmful_count = sum(1 for keyword in harmful_keywords if keyword in content)
    found_keywords = [keyword for keyword in harmful_keywords if keyword in content]

    # Determine content type and harmfulness
    is_harmful = False
    content_type = "none"
    reason = "Content appears to be legitimate helpdesk request"
    confidence = 0.9

    if harmful_count >= 2:
        is_harmful = True
        confidence = 0.8

        # Determine type based on keywords found
        profanity_keywords = ['fuck', 'shit', 'damn you', 'go to hell', 'kill yourself', 'hate you', 'stupid idiot', 'moron', 'retard', 'loser']
        spam_keywords = ['buy now', 'click here', 'free money', 'urgent action required', 'limited time offer', 'act now', 'guaranteed', 'make money fast']

        if any(keyword in found_keywords for keyword in profanity_keywords):
            content_type = "profanity"
            reason = f"Contains inappropriate language: {', '.join([k for k in found_keywords if k in profanity_keywords])}"
        elif any(keyword in found_keywords for keyword in spam_keywords):
            content_type = "spam"
            reason = f"Contains promotional/spam language: {', '.join([k for k in found_keywords if k in spam_keywords])}"
        else:
            content_type = "inappropriate"
            reason = f"Contains inappropriate content: {', '.join(found_keywords[:3])}"

        logger.warning(f"Fallback analysis detected {harmful_count} harmful keywords: {found_keywords}")

    # Check for excessive promotional language patterns
    elif harmful_count == 0:
        promotional_patterns = ['!', '$', 'free', 'now', 'urgent', 'limited']
        promotional_count = sum(content.count(pattern) for pattern in promotional_patterns)

        if promotional_count >= 5:
            is_harmful = True
            content_type = "spam"
            confidence = 0.7
            reason = f"Excessive promotional language detected (score: {promotional_count})"
            logger.warning(f"Fallback analysis detected excessive promotional language (score: {promotional_count})")

    result = {
        "is_harmful": is_harmful,
        "confidence": confidence,
        "reason": reason,
        "content_type": content_type
    }

    logger.info(f"Fallback detailed analysis result: {result}")
    return result
