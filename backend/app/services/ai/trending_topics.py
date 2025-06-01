"""
Trending Topics AI Service

Analyzes ticket titles and descriptions to extract trending topics and themes
using LLM analysis. This service helps identify common issues and patterns
in user support requests.
"""

import logging
from typing import List, Dict, Any, Optional
import json
from collections import Counter
from datetime import datetime, timedelta
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from app.core.ai_config import ai_config

logger = logging.getLogger(__name__)


class TrendingTopicsResult(BaseModel):
    """Pydantic model for LLM trending topics analysis result"""
    topics: List[Dict[str, Any]] = Field(description="List of trending topics with metadata")

    class Config:
        extra = "allow"


async def extract_trending_topics(tickets: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Extract trending topics from ticket titles and descriptions using LLM analysis.
    
    Args:
        tickets: List of ticket documents with title and description
        limit: Maximum number of topics to return
        
    Returns:
        List of trending topics with counts and examples
    """
    try:
        logger.info(f"Analyzing {len(tickets)} tickets for trending topics")

        if not tickets:
            logger.warning("No tickets provided for trending topics analysis")
            return []

        # Log some sample ticket data for debugging
        logger.info(f"Sample ticket titles: {[t.get('title', 'No title')[:50] for t in tickets[:3]]}")

        # Use real Gemini LLM analysis
        if ai_config.GOOGLE_API_KEY:
            logger.info("Using Gemini LLM for trending topics analysis")
            topics = await _analyze_topics_with_gemini_llm(tickets, limit)
        else:
            logger.warning("Google API key not configured, falling back to pattern matching")
            topics = await _analyze_topics_with_llm_stub(tickets, limit)

        logger.info(f"Extracted {len(topics)} trending topics: {[t['topic'] for t in topics[:5]]}")
        return topics
        
    except Exception as e:
        logger.error(f"Error extracting trending topics: {str(e)}")
        # Return fallback simple analysis
        return await _fallback_keyword_analysis(tickets, limit)


async def _analyze_topics_with_gemini_llm(tickets: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """
    Analyze tickets using Google Gemini LLM to extract trending topics.

    Args:
        tickets: List of ticket documents
        limit: Maximum number of topics to return

    Returns:
        List of trending topics with metadata
    """
    try:
        logger.info(f"Analyzing {len(tickets)} tickets with Gemini LLM")

        # Prepare ticket data for LLM analysis
        ticket_summaries = []
        for i, ticket in enumerate(tickets[:50]):  # Limit to 50 tickets to avoid token limits
            title = ticket.get('title', 'No title')
            description = ticket.get('description', 'No description')
            department = ticket.get('department', 'Unknown')

            ticket_summaries.append({
                "id": i + 1,
                "title": title[:100],  # Truncate long titles
                "description": description[:200],  # Truncate long descriptions
                "department": department
            })

        # Initialize Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model=ai_config.GEMINI_MODEL,
            temperature=ai_config.GEMINI_TEMPERATURE,
            max_tokens=ai_config.GEMINI_MAX_TOKENS,
            google_api_key=ai_config.GOOGLE_API_KEY,
            max_retries=2,
            timeout=30
        )

        # Create system message for trending topics analysis
        system_message = SystemMessage(content=f"""You are an expert data analyst specializing in helpdesk ticket analysis. Your task is to analyze helpdesk tickets and identify the top {limit} trending topics/issues.

Analyze the provided tickets and identify common themes, patterns, and trending issues. Focus on:
1. Technical problems (software, hardware, network, etc.)
2. HR-related issues (payroll, benefits, policies, etc.)
3. Access and authentication problems
4. Training and support requests
5. System errors and bugs

For each trending topic, provide:
- A clear, descriptive topic name
- The number of tickets related to this topic
- A brief explanation of what this topic covers
- Keywords associated with this topic

Return your analysis as a valid JSON object with this exact structure. Do not include any markdown formatting or code blocks:

{{
    "topics": [
        {{
            "topic": "Password Reset Issues",
            "count": 15,
            "percentage": 25.0,
            "description": "Users unable to reset passwords or access accounts",
            "keywords": ["password", "reset", "login", "access"],
            "examples": ["Cannot reset my password", "Locked out of account"],
            "analysis_method": "gemini_llm"
        }}
    ]
}}

IMPORTANT:
- Return ONLY valid JSON, no additional text or formatting
- Use double quotes for all strings
- Do not include trailing commas
- Be specific and actionable in your topic names
- Avoid generic terms like "General Issues"
- Ensure the JSON is properly formatted and parseable""")

        # Create user message with ticket data
        tickets_text = json.dumps(ticket_summaries, indent=2)
        user_message = HumanMessage(content=f"""Please analyze these helpdesk tickets and identify the top {limit} trending topics:

{tickets_text}

Total tickets to analyze: {len(tickets)}
Tickets shown (sample): {len(ticket_summaries)}

Provide a comprehensive analysis of trending issues in JSON format.""")

        # Get response from LLM
        logger.debug("Sending trending topics analysis request to Gemini")
        response = llm.invoke([system_message, user_message])

        # Parse the response
        response_text = response.content.strip()
        logger.debug(f"Raw Gemini response: {response_text[:500]}...")

        # Extract JSON from response with robust parsing
        try:
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response length: {len(response_text)}")

            # Check if response looks like it contains JSON
            if '{' not in response_text or '}' not in response_text:
                logger.warning("LLM response does not appear to contain JSON")
                logger.debug(f"Full response: {response_text}")
                raise ValueError("No JSON structure found in response")

            # Try multiple JSON extraction methods
            parsed_response = None

            # Method 1: Try to find complete JSON block
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                try:
                    parsed_response = json.loads(json_text)
                    logger.debug("Successfully parsed JSON using method 1")
                except json.JSONDecodeError as e:
                    logger.debug(f"Method 1 failed: {e}, trying method 2")

                    # Method 2: Try to clean and fix common JSON issues
                    cleaned_json = _clean_json_response(json_text)
                    try:
                        parsed_response = json.loads(cleaned_json)
                        logger.debug("Successfully parsed JSON using method 2 (cleaned)")
                    except json.JSONDecodeError as e:
                        logger.debug(f"Method 2 failed: {e}, trying method 3")
                        logger.debug(f"Cleaned JSON that failed: {cleaned_json[:200]}...")

                        # Method 3: Try to extract just the topics array
                        topics_match = _extract_topics_array(response_text)
                        if topics_match:
                            try:
                                parsed_response = {"topics": json.loads(topics_match)}
                                logger.debug("Successfully parsed JSON using method 3 (topics array)")
                            except json.JSONDecodeError:
                                logger.debug("Method 3 failed")

            # Process the parsed response
            if parsed_response and 'topics' in parsed_response:
                topics = parsed_response['topics']

                # Validate and enhance the topics
                validated_topics = []
                for topic in topics[:limit]:
                    if isinstance(topic, dict) and 'topic' in topic:
                        # Ensure all required fields exist
                        validated_topic = {
                            "topic": topic.get('topic', 'Unknown Topic'),
                            "count": topic.get('count', 1),
                            "percentage": topic.get('percentage', round((topic.get('count', 1) / len(tickets)) * 100, 1)),
                            "description": topic.get('description', ''),
                            "keywords": topic.get('keywords', []),
                            "examples": topic.get('examples', []),
                            "analysis_method": "gemini_llm"
                        }
                        validated_topics.append(validated_topic)

                if validated_topics:
                    logger.info(f"Successfully extracted {len(validated_topics)} topics from Gemini LLM")
                    return validated_topics
                else:
                    logger.warning("No valid topics found in LLM response")
            else:
                logger.warning("No 'topics' key found in LLM response or parsing failed")

        except Exception as e:
            logger.error(f"Error processing LLM response: {e}")

        # If parsing fails, fall back to pattern matching
        logger.warning("LLM response parsing failed, falling back to pattern matching")
        return await _analyze_topics_with_llm_stub(tickets, limit)

    except Exception as e:
        logger.error(f"Error in Gemini LLM trending topics analysis: {str(e)}")
        # Fall back to pattern matching
        return await _analyze_topics_with_llm_stub(tickets, limit)


def _clean_json_response(json_text: str) -> str:
    """
    Clean common JSON formatting issues from LLM responses.

    Args:
        json_text: Raw JSON text from LLM

    Returns:
        Cleaned JSON text
    """
    try:
        # Remove markdown code blocks if present
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]

        # Remove common formatting issues
        json_text = json_text.strip()

        # Fix trailing commas before closing brackets/braces
        import re
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)

        # Fix missing commas between objects (common LLM error)
        json_text = re.sub(r'}\s*{', r'},{', json_text)

        # Fix single quotes to double quotes
        json_text = re.sub(r"'([^']*)':", r'"\1":', json_text)
        json_text = re.sub(r':\s*\'([^\']*)\'\s*([,}])', r': "\1"\2', json_text)

        # Remove any non-printable characters
        json_text = ''.join(char for char in json_text if ord(char) >= 32 or char in '\n\r\t')

        return json_text

    except Exception as e:
        logger.debug(f"Error cleaning JSON: {e}")
        return json_text


def _extract_topics_array(response_text: str) -> Optional[str]:
    """
    Extract just the topics array from LLM response when full JSON parsing fails.

    Args:
        response_text: Full LLM response text

    Returns:
        Topics array as JSON string, or None if not found
    """
    try:
        import re

        # Look for topics array pattern
        patterns = [
            r'"topics"\s*:\s*(\[.*?\])',
            r"'topics'\s*:\s*(\[.*?\])",
            r'topics\s*:\s*(\[.*?\])',
        ]

        for pattern in patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                topics_array = match.group(1)
                # Clean the array
                topics_array = _clean_json_response(topics_array)
                return topics_array

        return None

    except Exception as e:
        logger.debug(f"Error extracting topics array: {e}")
        return None


async def _analyze_topics_with_llm_stub(tickets: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """
    Fallback implementation for topic analysis when LLM is not available.
    Uses pattern matching as a backup when Gemini API is not configured or fails.

    Args:
        tickets: List of ticket documents
        limit: Maximum number of topics to return

    Returns:
        List of trending topics with metadata
    """
    
    # Simulate LLM analysis with predefined patterns
    # In production, this would be replaced with actual LLM API calls
    
    # Combine all ticket content for analysis
    all_content = []
    for ticket in tickets:
        content = f"{ticket.get('title', '')} {ticket.get('description', '')}"
        all_content.append(content.lower())

    logger.info(f"Analyzing content from {len(all_content)} tickets")
    
    # Define common IT/HR topic patterns (this would be LLM-generated in production)
    topic_patterns = {
        "password_reset": ["password", "reset", "login", "access", "forgot", "unlock"],
        "email_issues": ["email", "outlook", "mail", "smtp", "inbox", "attachment"],
        "software_installation": ["install", "software", "application", "app", "setup", "download"],
        "network_connectivity": ["network", "wifi", "internet", "connection", "vpn", "slow"],
        "hardware_problems": ["computer", "laptop", "monitor", "printer", "keyboard", "mouse"],
        "payroll_questions": ["payroll", "salary", "pay", "wages", "timesheet", "hours"],
        "benefits_inquiry": ["benefits", "insurance", "health", "dental", "401k", "vacation"],
        "leave_requests": ["leave", "vacation", "sick", "time off", "pto", "absence"],
        "training_requests": ["training", "course", "certification", "learning", "skill"],
        "policy_questions": ["policy", "procedure", "handbook", "rules", "guidelines"],
        "performance_review": ["performance", "review", "evaluation", "feedback", "goals"],
        "system_errors": ["error", "bug", "crash", "freeze", "not working", "broken"]
    }
    
    # Count topic occurrences
    topic_counts = {}
    topic_examples = {}
    
    for topic, keywords in topic_patterns.items():
        count = 0
        examples = []
        
        for i, content in enumerate(all_content):
            matches = sum(1 for keyword in keywords if keyword in content)
            if matches >= 1:  # Require at least 1 keyword match (more flexible)
                count += 1
                if len(examples) < 3:  # Keep up to 3 examples
                    examples.append({
                        "ticket_id": str(tickets[i].get("_id", f"ticket_{i}")),
                        "title": tickets[i].get("title", "No title"),
                        "department": tickets[i].get("department", "Unknown")
                    })
        
        if count > 0:
            topic_counts[topic] = count
            topic_examples[topic] = examples
            logger.info(f"Found {count} matches for topic '{topic}'")

    logger.info(f"Total topics found: {len(topic_counts)}")

    # Sort by count and format results
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)

    trending_topics = []
    for topic, count in sorted_topics:
        # Convert topic key to readable format
        readable_topic = topic.replace("_", " ").title()

        trending_topics.append({
            "topic": readable_topic,
            "count": count,
            "percentage": round((count / len(tickets)) * 100, 1),
            "examples": topic_examples.get(topic, []),
            "keywords": topic_patterns[topic][:5],  # Show top 5 keywords
            "analysis_method": "pattern_matching_fallback"  # Indicate this is fallback when LLM unavailable
        })

    # If we don't have enough topics, add some fallback ones based on general analysis
    if len(trending_topics) < 5:
        logger.info(f"Only found {len(trending_topics)} topics, generating fallback topics")
        fallback_topics = await _generate_fallback_topics(tickets, len(trending_topics))
        trending_topics.extend(fallback_topics)
        logger.info(f"After fallback: {len(trending_topics)} total topics")

    # Limit to requested number
    final_topics = trending_topics[:limit]
    logger.info(f"Returning {len(final_topics)} trending topics")
    return final_topics


async def _generate_fallback_topics(tickets: List[Dict[str, Any]], existing_count: int) -> List[Dict[str, Any]]:
    """
    Generate fallback topics when we don't have enough pattern matches.
    Uses simple keyword frequency analysis.

    Args:
        tickets: List of ticket documents
        existing_count: Number of topics already found

    Returns:
        List of fallback trending topics
    """
    try:
        # Use keyword frequency analysis as fallback
        fallback_topics = await _fallback_keyword_analysis(tickets, 10)

        # Filter out generic words and return only what we need
        needed_count = 5 - existing_count
        filtered_topics = []

        # Skip very generic words
        skip_words = {"issue", "problem", "help", "need", "please", "thanks", "hello", "ticket"}

        for topic in fallback_topics:
            if topic["topic"].lower() not in skip_words and len(filtered_topics) < needed_count:
                # Adjust the topic to be more descriptive
                topic["topic"] = f"General {topic['topic']} Issues"
                topic["analysis_method"] = "fallback_analysis"
                filtered_topics.append(topic)

        # If still not enough, add some default topics
        if len(filtered_topics) < needed_count:
            default_topics = [
                {
                    "topic": "Technical Support Requests",
                    "count": max(1, len(tickets) // 10),
                    "percentage": 10.0,
                    "examples": [],
                    "keywords": ["technical", "support"],
                    "analysis_method": "default_topic"
                },
                {
                    "topic": "Account Access Issues",
                    "count": max(1, len(tickets) // 15),
                    "percentage": 6.7,
                    "examples": [],
                    "keywords": ["account", "access"],
                    "analysis_method": "default_topic"
                },
                {
                    "topic": "General Inquiries",
                    "count": max(1, len(tickets) // 20),
                    "percentage": 5.0,
                    "examples": [],
                    "keywords": ["inquiry", "question"],
                    "analysis_method": "default_topic"
                },
                {
                    "topic": "System Configuration",
                    "count": max(1, len(tickets) // 25),
                    "percentage": 4.0,
                    "examples": [],
                    "keywords": ["system", "configuration"],
                    "analysis_method": "default_topic"
                },
                {
                    "topic": "User Training Requests",
                    "count": max(1, len(tickets) // 30),
                    "percentage": 3.3,
                    "examples": [],
                    "keywords": ["training", "help"],
                    "analysis_method": "default_topic"
                }
            ]

            remaining_needed = needed_count - len(filtered_topics)
            filtered_topics.extend(default_topics[:remaining_needed])

        return filtered_topics

    except Exception as e:
        logger.error(f"Error generating fallback topics: {str(e)}")
        return []


async def _fallback_keyword_analysis(tickets: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """
    Fallback keyword-based analysis when LLM analysis fails.
    
    Args:
        tickets: List of ticket documents
        limit: Maximum number of topics to return
        
    Returns:
        List of trending topics based on simple keyword frequency
    """
    try:
        logger.info("Using fallback keyword analysis for trending topics")
        
        # Extract all words from titles and descriptions
        all_words = []
        for ticket in tickets:
            title = ticket.get("title", "").lower()
            description = ticket.get("description", "").lower()
            
            # Simple word extraction (remove common words)
            words = title.split() + description.split()
            filtered_words = [
                word.strip(".,!?;:()[]{}\"'") 
                for word in words 
                if len(word) > 3 and word not in {
                    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", 
                    "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", 
                    "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy", 
                    "did", "she", "use", "way", "will", "with", "have", "this", "that",
                    "from", "they", "know", "want", "been", "good", "much", "some", "time",
                    "very", "when", "come", "here", "just", "like", "long", "make", "many",
                    "over", "such", "take", "than", "them", "well", "were", "what"
                }
            ]
            all_words.extend(filtered_words)
        
        # Count word frequencies
        word_counts = Counter(all_words)
        top_words = word_counts.most_common(limit)
        
        # Format as trending topics
        trending_topics = []
        for word, count in top_words:
            trending_topics.append({
                "topic": word.title(),
                "count": count,
                "percentage": round((count / len(tickets)) * 100, 1),
                "examples": [],  # No examples in fallback mode
                "keywords": [word],
                "analysis_method": "keyword_frequency"
            })
        
        return trending_topics
        
    except Exception as e:
        logger.error(f"Error in fallback keyword analysis: {str(e)}")
        return []


async def analyze_topic_trends_over_time(tickets: List[Dict[str, Any]], days_back: int = 30) -> Dict[str, Any]:
    """
    Analyze how topics trend over time periods.
    
    Args:
        tickets: List of ticket documents with timestamps
        days_back: Number of days to analyze
        
    Returns:
        Dictionary containing time-based topic trends
    """
    try:
        logger.info(f"Analyzing topic trends over {days_back} days")
        
        # Group tickets by time periods (weekly buckets)
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        weekly_buckets = {}
        
        for ticket in tickets:
            created_at = ticket.get("created_at")
            if not created_at:
                continue
                
            # Calculate which week this ticket belongs to
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            days_ago = (now - created_at).days
            week_number = days_ago // 7
            
            if week_number not in weekly_buckets:
                weekly_buckets[week_number] = []
            weekly_buckets[week_number].append(ticket)
        
        # Analyze topics for each week
        weekly_trends = {}
        for week, week_tickets in weekly_buckets.items():
            if week_tickets:
                topics = await extract_trending_topics(week_tickets, 5)
                weekly_trends[f"week_{week}"] = {
                    "period": f"{week * 7} - {(week + 1) * 7} days ago",
                    "ticket_count": len(week_tickets),
                    "top_topics": topics
                }
        
        return {
            "analysis_period": f"Last {days_back} days",
            "weekly_trends": weekly_trends,
            "total_tickets_analyzed": len(tickets)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing topic trends over time: {str(e)}")
        return {
            "analysis_period": f"Last {days_back} days",
            "weekly_trends": {},
            "total_tickets_analyzed": 0,
            "error": str(e)
        }
