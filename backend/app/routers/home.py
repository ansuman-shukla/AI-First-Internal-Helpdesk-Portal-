from fastapi import APIRouter, Depends
from app.routers.auth import get_current_user

router = APIRouter(tags=["home"])


@router.get("/user/home")
async def user_home(current_user: dict = Depends(get_current_user)):
    """User homepage with comprehensive self-serve bot instructions"""
    return {
        "message": "Welcome to the User Home Page",
        "user": current_user["username"],
        "role": current_user["role"],
        "features": [
            "Create and manage your tickets",
            "Chat with agents in real-time",
            "Use the self-serve AI bot for quick answers",
        ],
        "self_serve_bot": {
            "title": "AI-Powered Self-Serve Assistant",
            "description": "Get instant answers to common IT and HR questions using our intelligent AI bot. Save time by getting immediate help before creating a ticket.",
            "endpoint": "/ai/self-serve-query",
            "method": "POST",
            "capabilities": [
                "Answer common IT troubleshooting questions",
                "Provide HR policy information and guidance",
                "Help with software installation and configuration",
                "Explain company procedures and workflows",
                "Assist with password reset and account issues"
            ],
            "usage_instructions": {
                "how_to_use": "Send a POST request to the endpoint with your question",
                "request_format": {
                    "query": "Your question here (required)",
                    "session_id": "Optional session identifier for context"
                },
                "response_format": {
                    "answer": "AI-generated response to your query"
                }
            },
            "example_queries": [
                "How do I reset my password?",
                "What is the company's remote work policy?",
                "How to install Microsoft Office?",
                "What are the steps to request vacation time?",
                "My computer is running slowly, what should I do?"
            ],
            "tips": [
                "Be specific in your questions for better answers",
                "Include relevant details about your issue",
                "Try rephrasing if the first answer isn't helpful",
                "For complex issues, consider creating a ticket for human assistance"
            ],
            "limitations": "The AI bot provides general guidance. For urgent issues or complex problems, please create a support ticket for direct agent assistance."
        },
    }


@router.get("/agent/home")
async def agent_home(current_user: dict = Depends(get_current_user)):
    """Agent homepage"""
    # Verify user is an agent
    if current_user["role"] not in ["it_agent", "hr_agent"]:
        return {"error": "Access denied. Agent role required."}

    return {
        "message": "Welcome to the Agent Home Page",
        "agent": current_user["username"],
        "role": current_user["role"],
        "department": "IT" if current_user["role"] == "it_agent" else "HR",
        "features": [
            "View and manage assigned tickets",
            "Chat with users in real-time",
            "Use AI suggestions for responses",
            "Close resolved tickets",
        ],
    }


@router.get("/admin/home")
async def admin_home(current_user: dict = Depends(get_current_user)):
    """Admin homepage"""
    # Verify user is an admin
    if current_user["role"] != "admin":
        return {"error": "Access denied. Admin role required."}

    return {
        "message": "Welcome to the Admin Home Page",
        "admin": current_user["username"],
        "role": current_user["role"],
        "features": [
            "View all tickets across departments",
            "Monitor misuse reports",
            "Review flagged content",
            "Manage system settings",
        ],
    }
