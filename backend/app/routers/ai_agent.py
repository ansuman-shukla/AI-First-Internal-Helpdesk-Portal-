"""
AI Agent Router

This module provides endpoints for agent-side AI functionality,
including response suggestions and other AI-powered agent tools.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List
from app.schemas.message import MessageSchema
from app.services.ai.response_suggestion_rag import response_suggestion_rag
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-agent"])


class SuggestResponseRequest(BaseModel):
    """Request model for AI response suggestions"""
    ticket_id: str = Field(..., min_length=1, max_length=100, description="ID of the ticket")
    conversation_context: List[MessageSchema] = Field(
        ..., 
        min_items=0, 
        max_items=50, 
        description="List of messages providing conversation context"
    )


class SuggestResponseResponse(BaseModel):
    """Response model for AI response suggestions"""
    suggested_response: str = Field(..., description="AI-generated response suggestion")


def verify_agent_role(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Verify that the current user has agent role
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: User information if authorized
        
    Raises:
        HTTPException: If user is not an agent
    """
    if current_user["role"] not in ["it_agent", "hr_agent"]:
        logger.warning(f"Non-agent user {current_user['username']} attempted to access agent AI endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Agent role required."
        )
    
    logger.debug(f"Agent {current_user['username']} ({current_user['role']}) accessing AI suggestion endpoint")
    return current_user


@router.post("/suggest-response", response_model=SuggestResponseResponse)
async def suggest_response(
    request: SuggestResponseRequest,
    current_user: dict = Depends(verify_agent_role)
):
    """
    Generate AI-powered response suggestions for agents
    
    This endpoint allows agents to get AI-generated response suggestions
    based on the conversation context within a ticket. The suggestions
    help agents provide better and faster responses to user queries.
    
    - **ticket_id**: ID of the ticket for context (required)
    - **conversation_context**: List of messages providing conversation history
    
    Returns an AI-generated response suggestion that agents can use,
    modify, or use as inspiration for their own responses.
    
    **Authorization**: Only agents (it_agent, hr_agent) can access this endpoint.
    """
    try:
        logger.info(
            f"AI response suggestion requested by {current_user['username']} "
            f"for ticket {request.ticket_id} with {len(request.conversation_context)} context messages"
        )
        
        # Call the response suggestion RAG service
        suggested_response = response_suggestion_rag(
            ticket_id=request.ticket_id,
            conversation_context=request.conversation_context
        )
        
        logger.info(
            f"AI response suggestion generated successfully for ticket {request.ticket_id} "
            f"- Response length: {len(suggested_response)}"
        )
        
        return SuggestResponseResponse(suggested_response=suggested_response)
        
    except ValueError as e:
        logger.error(f"Validation error in AI response suggestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in AI response suggestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response suggestion. Please try again."
        )


@router.get("/agent-tools")
async def agent_tools_info(current_user: dict = Depends(verify_agent_role)):
    """
    Get information about available AI tools for agents
    
    Returns information about AI-powered tools available to agents,
    including response suggestions and usage guidelines.
    
    **Authorization**: Only agents (it_agent, hr_agent) can access this endpoint.
    """
    return {
        "service": "Agent AI Tools",
        "description": "AI-powered tools to help agents provide better support",
        "agent": {
            "username": current_user["username"],
            "role": current_user["role"],
            "department": "IT" if current_user["role"] == "it_agent" else "HR"
        },
        "tools": [
            {
                "name": "Response Suggestions",
                "endpoint": "/ai/suggest-response",
                "method": "POST",
                "description": "Get AI-generated response suggestions based on conversation context",
                "features": [
                    "Context-aware suggestions",
                    "Department-specific responses",
                    "Professional tone guidance",
                    "Troubleshooting assistance",
                    "Policy information support"
                ]
            }
        ],
        "usage_guidelines": [
            "Review and customize AI suggestions before sending",
            "Use suggestions as starting points for responses",
            "Maintain professional and helpful tone",
            "Verify technical information before sharing",
            "Add personal touch to AI-generated content"
        ],
        "limitations": [
            "AI suggestions are recommendations, not final answers",
            "Always review content for accuracy and appropriateness",
            "Consider user's specific context and needs",
            "Use professional judgment when applying suggestions"
        ]
    }
