"""
AI Bot Router

This module provides endpoints for the self-serve AI bot functionality.
Users can query the AI bot for instant help without authentication.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from app.services.ai.agent import query_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-bot"])


class SelfServeQueryRequest(BaseModel):
    """Request model for self-serve AI bot queries"""
    query: str = Field(..., min_length=1, max_length=1000, description="User's question or query")
    session_id: Optional[str] = Field(None, max_length=100, description="Optional session identifier")


class SelfServeQueryResponse(BaseModel):
    """Response model for self-serve AI bot queries"""
    answer: str = Field(..., description="AI-generated response to the query")


@router.post("/self-serve-query", response_model=SelfServeQueryResponse)
async def self_serve_query(request: SelfServeQueryRequest):
    """
    Enhanced self-serve AI bot endpoint with RAG and web search capabilities

    This endpoint uses an intelligent AI agent that can search both the internal
    knowledge base and the web to provide comprehensive answers. The agent
    automatically chooses the best source for each query.

    - **query**: User's question or query (required, 1-1000 characters)
    - **session_id**: Optional session identifier for conversation tracking

    Features:
    - Internal knowledge base search for company-specific information
    - Web search for external information, current events, and general knowledge
    - Intelligent tool selection based on query context
    - Comprehensive fallback responses when services are unavailable

    Returns an AI-generated response to help the user.
    """
    try:
        logger.info(f"Self-serve query received - Query length: {len(request.query)}, Session: {request.session_id}")

        # Use the enhanced AI agent with RAG and web search capabilities
        agent_result = query_agent(request.query, session_id=request.session_id)

        # Extract answer from agent result
        answer = agent_result.get("answer", "I'm sorry, I couldn't process your query at the moment.")

        logger.info(f"Self-serve query processed successfully with enhanced agent - Response length: {len(answer)}")

        return SelfServeQueryResponse(answer=answer)
        
    except ValueError as e:
        logger.warning(f"Invalid query input: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query: {str(e)}"
        )
    except TypeError as e:
        logger.warning(f"Type error in query processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input type: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing self-serve query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process your query. Please try again later."
        )


@router.get("/self-serve-info")
async def self_serve_info():
    """
    Get information about the self-serve AI bot
    
    Returns information about how to use the self-serve AI bot,
    including available features and usage guidelines.
    """
    return {
        "service": "Enhanced Self-Serve AI Bot",
        "description": "Get intelligent AI assistance with RAG and web search capabilities",
        "features": [
            "No authentication required",
            "Internal knowledge base search for company information",
            "Web search for external information and current events",
            "Intelligent tool selection based on query context",
            "Comprehensive responses for stock prices, tech questions, and more",
            "Fallback guidance when services are unavailable",
            "Session tracking support"
        ],
        "usage": {
            "endpoint": "/ai/self-serve-query",
            "method": "POST",
            "required_fields": ["query"],
            "optional_fields": ["session_id"],
            "query_limits": {
                "min_length": 1,
                "max_length": 1000
            }
        },
        "examples": [
            {
                "query": "How do I reset my password?",
                "description": "Get guidance on password reset procedures (uses knowledge base)"
            },
            {
                "query": "What is the current price of Apple stock?",
                "description": "Get current stock information (uses web search)"
            },
            {
                "query": "What are the vacation policies?",
                "description": "Learn about leave and vacation policies (uses knowledge base)"
            },
            {
                "query": "How to troubleshoot wifi connection?",
                "description": "Get troubleshooting guidance (uses both sources as needed)"
            },
            {
                "query": "Latest cybersecurity trends 2024",
                "description": "Get current information about cybersecurity (uses web search)"
            }
        ]
    }
