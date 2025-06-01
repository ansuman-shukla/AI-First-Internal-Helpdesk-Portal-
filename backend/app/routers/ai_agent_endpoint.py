"""
AI Agent Endpoint for Dashboard Integration

This module provides the endpoint for the "Resolve with AI" functionality
that can be integrated with the dashboard frontend.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
from app.services.ai.agent import query_agent
from app.core.auth import get_current_user
from app.schemas.user import UserSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Agent"])


class AIQueryRequest(BaseModel):
    """Request model for AI agent queries"""
    query: str = Field(..., min_length=1, max_length=1000, description="The user's question or request")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation tracking")


class AIQueryResponse(BaseModel):
    """Response model for AI agent queries"""
    success: bool = Field(..., description="Whether the query was successful")
    answer: str = Field(..., description="The AI agent's response")
    sources: list[str] = Field(default_factory=list, description="Sources used for the response")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the response")
    error: Optional[str] = Field(None, description="Error message if query failed")


@router.post("/resolve", response_model=AIQueryResponse)
async def resolve_with_ai(
    request: AIQueryRequest,
    current_user: UserSchema = Depends(get_current_user)
) -> AIQueryResponse:
    """
    Resolve user queries using the AI agent with RAG and web search capabilities.
    
    This endpoint powers the "Resolve with AI" button on the dashboard.
    
    Args:
        request: The AI query request containing the user's question
        current_user: The authenticated user making the request
        
    Returns:
        AIQueryResponse: The AI agent's response with metadata
        
    Raises:
        HTTPException: If the query fails or user is not authenticated
    """
    logger.info(f"AI resolve request from user {current_user.email}: '{request.query[:50]}...'")
    
    try:
        # Generate session ID if not provided
        session_id = request.session_id or f"user_{current_user.user_id}_{hash(request.query) % 10000}"
        
        # Query the AI agent
        result = query_agent(request.query, session_id=session_id)
        
        # Log successful resolution
        logger.info(f"AI resolution successful for user {current_user.email} - Response length: {len(result['answer'])}")
        
        return AIQueryResponse(
            success=True,
            answer=result["answer"],
            sources=result.get("sources", []),
            session_id=result.get("session_id"),
            metadata={
                **result.get("metadata", {}),
                "user_id": current_user.user_id,
                "user_email": current_user.email,
                "response_time": "< 2s"  # Would be calculated in real implementation
            }
        )
        
    except ValueError as e:
        # Handle validation errors
        logger.warning(f"AI resolve validation error for user {current_user.email}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"AI resolve failed for user {current_user.email}: {str(e)}")
        
        return AIQueryResponse(
            success=False,
            answer="I'm currently unable to process your request. Please try again later or contact support for assistance.",
            sources=[],
            session_id=request.session_id,
            metadata={
                "user_id": current_user.user_id,
                "user_email": current_user.email,
                "error_type": type(e).__name__
            },
            error=str(e)
        )


@router.get("/status")
async def get_ai_status() -> Dict[str, Any]:
    """
    Get the current status of the AI agent and its capabilities.
    
    Returns:
        Dict containing the AI agent status and configuration
    """
    try:
        from app.core.ai_config import ai_config
        
        config = ai_config.get_safe_config()
        
        return {
            "status": "operational",
            "capabilities": {
                "knowledge_base_search": config["rag_enabled"],
                "web_search": config["web_search_enabled"] and config["serper_api_key_configured"],
                "llm_model": config["gemini_model"],
                "tools_available": ["knowledge_base", "web_search"]
            },
            "configuration": {
                "google_api_configured": config["google_api_key_configured"],
                "rag_enabled": config["rag_enabled"],
                "web_search_enabled": config["web_search_enabled"],
                "serper_api_configured": config["serper_api_key_configured"]
            },
            "health": "healthy" if config["google_api_key_configured"] else "degraded"
        }
        
    except Exception as e:
        logger.error(f"Failed to get AI status: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "health": "unhealthy"
        }


@router.post("/test")
async def test_ai_agent(
    current_user: UserSchema = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test the AI agent with predefined queries to verify functionality.
    
    This endpoint is useful for testing and debugging the AI agent.
    
    Args:
        current_user: The authenticated user (admin only recommended)
        
    Returns:
        Dict containing test results
    """
    logger.info(f"AI agent test requested by user {current_user.email}")
    
    test_queries = [
        "What is the current price of Apple stock?",
        "How do I reset my password?",
        "What are the latest cybersecurity trends?",
        "Company vacation policy"
    ]
    
    results = []
    
    for query in test_queries:
        try:
            result = query_agent(query, session_id=f"test_{current_user.user_id}")
            results.append({
                "query": query,
                "success": True,
                "response_length": len(result["answer"]),
                "sources": result.get("sources", []),
                "preview": result["answer"][:100] + "..." if len(result["answer"]) > 100 else result["answer"]
            })
        except Exception as e:
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    return {
        "test_completed": True,
        "total_queries": len(test_queries),
        "successful_queries": sum(1 for r in results if r["success"]),
        "results": results,
        "tester": current_user.email
    }


# Example frontend integration code (JavaScript)
FRONTEND_INTEGRATION_EXAMPLE = """
// Frontend integration example for the "Resolve with AI" button

async function resolveWithAI(userQuery) {
    try {
        const response = await fetch('/api/ai/resolve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                query: userQuery,
                session_id: `user_${userId}_${Date.now()}`
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Display the AI response
            displayAIResponse(result.answer, result.sources);
        } else {
            // Handle error
            displayError(result.error || 'AI service unavailable');
        }
        
    } catch (error) {
        console.error('AI resolve failed:', error);
        displayError('Failed to connect to AI service');
    }
}

// Usage in dashboard
document.getElementById('resolve-ai-btn').addEventListener('click', () => {
    const userQuery = document.getElementById('user-query').value;
    if (userQuery.trim()) {
        resolveWithAI(userQuery);
    }
});
"""
