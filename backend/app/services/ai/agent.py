"""
AI Agent Module

This module provides an intelligent agent that can query the RAG database and search the web
to provide comprehensive answers to user queries. The agent uses LangGraph's create_react_agent
with two main tools: RAG database querying and web search.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import GoogleSerperAPIWrapper
from langgraph.prebuilt import create_react_agent
from app.core.ai_config import ai_config
from app.services.ai.rag import rag_query

logger = logging.getLogger(__name__)


@tool
def query_knowledge_base(query: str) -> str:
    """
    Query the internal knowledge base using RAG (Retrieval-Augmented Generation).

    This tool searches through company documents, policies, procedures, IT guidelines,
    HR information, and other internal knowledge to provide accurate answers based on company information.
    Use this FIRST for any company-related questions.

    Args:
        query (str): The question or search query for the knowledge base

    Returns:
        str: Answer from the knowledge base with source information, or indication if no relevant info found
    """
    logger.info(f"Knowledge base query requested: '{query[:50]}...'")

    try:
        # Use existing RAG functionality
        result = rag_query(query)

        # Format the response with sources
        answer = result.get("answer", "")
        sources = result.get("sources", [])

        # Check if the answer indicates no information was found
        no_info_indicators = [
            "no answer found",
            "no relevant information",
            "couldn't find relevant information",
            "not found in the knowledge base",
            "no information available"
        ]

        answer_lower = answer.lower()
        has_no_info = any(indicator in answer_lower for indicator in no_info_indicators)

        if has_no_info or not answer.strip() or len(answer.strip()) < 20:
            return f"No relevant information found in the company knowledge base for '{query}'. You may want to try a web search for external information or contact the appropriate department for assistance."

        # Format successful response with sources
        if sources:
            formatted_sources = "\n\n📚 Sources from company knowledge base:\n" + "\n".join([f"• {source}" for source in sources])
            return f"From company knowledge base:\n\n{answer}{formatted_sources}"
        else:
            return f"From company knowledge base:\n\n{answer}"

    except Exception as e:
        logger.error(f"Knowledge base query failed: {str(e)}")
        return f"I encountered an error while searching the company knowledge base: {str(e)}. Please try a web search or contact support for assistance."


@tool
def search_web(query: str) -> str:
    """
    Search the web for current information and external resources.

    This tool searches the internet for up-to-date information, news, external
    resources, stock prices, general knowledge, and anything not in the company knowledge base.
    Use this for: stock prices, current events, external software, general tech questions,
    latest versions, market data, and when knowledge base has insufficient information.

    Args:
        query (str): The search query for web search

    Returns:
        str: Web search results with relevant information
    """
    logger.info(f"Web search requested: '{query[:50]}...'")

    # Check if web search is enabled and configured
    if not ai_config.WEB_SEARCH_ENABLED:
        logger.info("Web search is disabled, providing fallback response")
        return _provide_web_search_fallback(query)

    if not ai_config.SERPER_API_KEY:
        logger.warning("Serper API key not configured, providing fallback response")
        return _provide_web_search_fallback(query)

    try:
        # Initialize Google Serper API wrapper
        search = GoogleSerperAPIWrapper(
            serper_api_key=ai_config.SERPER_API_KEY,
            k=5  # Return top 5 results
        )

        # Perform web search
        search_results = search.run(query)

        logger.debug(f"Web search completed - Query: '{query[:50]}...', Results length: {len(search_results)}")

        # Format results for better readability
        if search_results and search_results.strip():
            formatted_results = f"""Based on web search results for '{query}':

{search_results}

📌 Note: This information is from external sources. For company-specific policies or procedures, please refer to internal documentation or contact your supervisor."""
            return formatted_results
        else:
            return _provide_web_search_fallback(query)

    except Exception as e:
        logger.error(f"Web search failed: {str(e)}")
        return _provide_web_search_fallback(query)


def _provide_web_search_fallback(query: str) -> str:
    """
    Provide helpful fallback responses when web search is unavailable.

    Args:
        query: The original search query

    Returns:
        Helpful fallback response based on query content
    """
    query_lower = query.lower()

    # Stock/financial queries
    if any(word in query_lower for word in ["stock", "price", "market", "trading", "financial", "investment"]):
        return """For current stock prices and market information, I recommend:
• Check financial websites like Yahoo Finance, Google Finance, or Bloomberg
• Use your broker's app or website for real-time data
• For company stock information, check the investor relations page on the company website
• Consider consulting with a financial advisor for investment decisions"""

    # Technology/software queries
    elif any(word in query_lower for word in ["software", "download", "install", "update", "version", "tech"]):
        return """For software and technology information:
• Visit the official website of the software/service you're asking about
• Check the software's documentation or help section
• For company-approved software, contact IT support
• For general tech questions, try official support forums or documentation"""

    # General troubleshooting
    elif any(word in query_lower for word in ["troubleshoot", "fix", "problem", "issue", "error"]):
        return """For troubleshooting assistance:
• Check the official documentation or support pages
• Try searching for your specific error message online
• For company systems, contact IT support
• For general issues, consider checking user forums or community support"""

    # Current events/news
    elif any(word in query_lower for word in ["news", "current", "latest", "recent", "today"]):
        return """For current information and news:
• Check reputable news websites like BBC, Reuters, or AP News
• For industry-specific news, visit relevant trade publications
• For company news, check internal communications or company website
• Use news aggregators like Google News for comprehensive coverage"""

    # Default fallback
    else:
        return f"""I'm unable to search the web for '{query}' at the moment. Here are some alternatives:

• Try searching online using search engines like Google, Bing, or DuckDuckGo
• Check official websites or documentation related to your question
• For company-specific information, contact the appropriate department
• If this is urgent, please create a support ticket or contact your supervisor

I apologize for the inconvenience. Is there anything else I can help you with using our internal knowledge base?"""


def create_helpdesk_agent():
    """
    Create and configure the helpdesk AI agent with RAG and web search capabilities.
    
    Returns:
        CompiledStateGraph: The configured agent ready for use
    """
    logger.info("Initializing helpdesk AI agent")
    
    # Check if Google API key is configured
    if not ai_config.GOOGLE_API_KEY:
        logger.error("Google API key not configured")
        raise ValueError("Google API key is required for the AI agent")
    
    try:
        # Initialize the LLM with optimized settings for agent use
        llm = ChatGoogleGenerativeAI(
            model=ai_config.GEMINI_MODEL,
            temperature=max(0.3, ai_config.GEMINI_TEMPERATURE),  # Ensure minimum creativity for better responses
            max_tokens=max(2000, ai_config.GEMINI_MAX_TOKENS),   # Ensure sufficient response length
            google_api_key=ai_config.GOOGLE_API_KEY,
            max_retries=3,  # Increased retries for better reliability
            timeout=90      # Increased timeout for complex queries
        )
        
        # Define available tools
        tools = [query_knowledge_base, search_web]
        
        # Create system prompt for the agent
        system_prompt = """You are an intelligent AI assistant for an internal company helpdesk system. You have access to two powerful tools to help employees:

🔍 **Available Tools:**
1. **query_knowledge_base**: Search internal company documents, policies, procedures, IT guidelines, and HR information
2. **search_web**: Search the internet for current information, external resources, and general knowledge

📋 **Decision Making Rules:**

**ALWAYS use query_knowledge_base FIRST for:**
- Company policies and procedures
- Internal IT guidelines and troubleshooting
- HR information and benefits
- Internal software and systems
- Company-specific processes

**Use search_web when:**
- Knowledge base returns "No answer found" or insufficient information
- Questions about external software, tools, or services
- Current events, news, or recent developments
- General technical questions not specific to the company
- Stock prices, market information, or external data
- Latest versions of software or technology trends

**IMPORTANT BEHAVIOR:**
- If knowledge_base search fails or returns insufficient information, IMMEDIATELY try search_web
- For questions about external topics (like stock prices, general software, current events), use search_web directly
- Always provide helpful responses - never say you cannot help without trying both tools
- Combine information from both sources when relevant
- Clearly indicate which source provided which information

**Response Quality:**
- Be comprehensive and helpful
- Provide step-by-step instructions when applicable
- Include relevant links or references when available from web search
- If both tools fail, provide general guidance and suggest contacting support

Remember: Your goal is to be maximally helpful. Always try to find an answer using your available tools before saying you cannot help."""
        
        # Create the ReAct agent
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
            debug=ai_config.AI_LOG_LEVEL == "DEBUG"
        )
        
        logger.info("Helpdesk AI agent initialized successfully")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to initialize helpdesk AI agent: {str(e)}")
        raise


def query_agent(query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Query the helpdesk AI agent with a user question.
    
    Args:
        query (str): The user's question or request
        session_id (Optional[str]): Optional session ID for conversation tracking
        
    Returns:
        Dict[str, Any]: Response containing the agent's answer and metadata
    """
    logger.info(f"Agent query requested - Query length: {len(query)}, Session: {session_id}")
    logger.debug(f"Agent query content: '{query[:100]}...' (truncated)")
    
    # Input validation
    if not isinstance(query, str):
        raise TypeError(f"query must be a string, got {type(query).__name__}")
    
    if not query.strip():
        raise ValueError("query cannot be empty or only whitespace")
    
    try:
        # Create agent instance
        agent = create_helpdesk_agent()
        
        # Prepare input for the agent
        agent_input = {
            "messages": [("user", query)]
        }
        
        # Run the agent
        logger.debug("Running agent with user query")
        result = agent.invoke(agent_input)
        
        # Extract the final response
        messages = result.get("messages", [])
        if messages:
            final_message = messages[-1]
            response_content = final_message.content if hasattr(final_message, 'content') else str(final_message)
        else:
            response_content = "I apologize, but I couldn't generate a response. Please try rephrasing your question."
        
        logger.info(f"Agent query completed - Response length: {len(response_content)}")
        
        return {
            "answer": response_content,
            "session_id": session_id,
            "sources": ["AI Agent with RAG and Web Search"],
            "metadata": {
                "query_length": len(query),
                "response_length": len(response_content),
                "tools_available": ["knowledge_base", "web_search"]
            }
        }
        
    except Exception as e:
        logger.error(f"Agent query failed: {str(e)}")
        return {
            "answer": f"I encountered an error while processing your request: {str(e)}. Please try rephrasing your question or contact support for assistance.",
            "session_id": session_id,
            "sources": [],
            "metadata": {
                "error": str(e),
                "query_length": len(query)
            }
        }


# Global agent instance (lazy initialization)
_agent_instance = None


def get_agent():
    """
    Get the global agent instance (lazy initialization).
    
    Returns:
        CompiledStateGraph: The configured agent
    """
    global _agent_instance
    
    if _agent_instance is None:
        logger.info("Creating global agent instance")
        _agent_instance = create_helpdesk_agent()
    
    return _agent_instance


def reset_agent():
    """
    Reset the global agent instance (useful for testing or configuration changes).
    """
    global _agent_instance
    logger.info("Resetting global agent instance")
    _agent_instance = None
