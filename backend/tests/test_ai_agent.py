"""
Unit tests for AI Agent endpoints
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.routers.auth import get_current_user

# Create a test client
client = TestClient(app)


def override_auth_dependency(user_data):
    """Helper function to override authentication dependency"""
    async def mock_get_current_user():
        return user_data
    return mock_get_current_user


class TestAIAgentEndpoints:
    """Test cases for AI agent endpoint functionality"""
    
    @pytest.fixture
    def mock_agent_user(self):
        """Mock agent user for authentication"""
        return {
            "username": "test_agent",
            "user_id": "507f1f77bcf86cd799439011",
            "role": "it_agent"
        }
    
    @pytest.fixture
    def mock_user_user(self):
        """Mock regular user for authorization testing"""
        return {
            "username": "test_user",
            "user_id": "507f1f77bcf86cd799439012",
            "role": "user"
        }
    
    @pytest.fixture
    def sample_conversation_context(self):
        """Sample conversation context for testing"""
        return [
            {
                "id": "msg1",
                "ticket_id": "TKT-123",
                "sender_id": "507f1f77bcf86cd799439012",
                "sender_role": "user",
                "message_type": "user_message",
                "content": "My computer won't start up",
                "isAI": False,
                "feedback": "none",
                "timestamp": "2023-01-01T10:00:00Z"
            },
            {
                "id": "msg2",
                "ticket_id": "TKT-123",
                "sender_id": "507f1f77bcf86cd799439011",
                "sender_role": "it_agent",
                "message_type": "agent_message",
                "content": "Can you tell me what happens when you press the power button?",
                "isAI": False,
                "feedback": "none",
                "timestamp": "2023-01-01T10:01:00Z"
            },
            {
                "id": "msg3",
                "ticket_id": "TKT-123",
                "sender_id": "507f1f77bcf86cd799439012",
                "sender_role": "user",
                "message_type": "user_message",
                "content": "Nothing happens at all, no lights or sounds",
                "isAI": False,
                "feedback": "none",
                "timestamp": "2023-01-01T10:02:00Z"
            }
        ]
    
    def test_suggest_response_success_it_agent(self, mock_agent_user, sample_conversation_context):
        """Test successful response suggestion for IT agent"""
        # Override the dependency
        async def mock_get_current_user():
            return mock_agent_user

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            response = client.post(
                "/ai/suggest-response",
                json={
                    "ticket_id": "TKT-123",
                    "conversation_context": sample_conversation_context
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "suggested_response" in data
            assert isinstance(data["suggested_response"], str)
            assert len(data["suggested_response"]) > 0

            # Verify response content is contextual and helpful
            suggestion = data["suggested_response"].lower()
            # Check for general indicators of a helpful technical response
            helpful_indicators = [
                "troubleshoot", "technical", "help", "issue", "problem", "solution",
                "try", "check", "verify", "ensure", "please", "let me know",
                "steps", "power", "computer", "cable", "outlet", "button"
            ]
            assert any(word in suggestion for word in helpful_indicators), f"Response doesn't contain helpful indicators: {suggestion}"
        finally:
            # Clean up the override
            app.dependency_overrides.clear()
    
    def test_suggest_response_success_hr_agent(self, sample_conversation_context):
        """Test successful response suggestion for HR agent"""
        hr_agent = {
            "username": "hr_agent",
            "user_id": "507f1f77bcf86cd799439013",
            "role": "hr_agent"
        }

        app.dependency_overrides[get_current_user] = override_auth_dependency(hr_agent)

        try:
            response = client.post(
                "/ai/suggest-response",
                json={
                    "ticket_id": "TKT-456",
                    "conversation_context": sample_conversation_context
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "suggested_response" in data
            assert isinstance(data["suggested_response"], str)
        finally:
            app.dependency_overrides.clear()

    def test_suggest_response_empty_context(self, mock_agent_user):
        """Test response suggestion with empty conversation context"""
        app.dependency_overrides[get_current_user] = override_auth_dependency(mock_agent_user)

        try:
            response = client.post(
                "/ai/suggest-response",
                json={
                    "ticket_id": "TKT-789",
                    "conversation_context": []
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "suggested_response" in data
            assert len(data["suggested_response"]) > 0
        finally:
            app.dependency_overrides.clear()

    def test_suggest_response_unauthorized_user(self, mock_user_user, sample_conversation_context):
        """Test response suggestion access denied for regular user"""
        app.dependency_overrides[get_current_user] = override_auth_dependency(mock_user_user)

        try:
            response = client.post(
                "/ai/suggest-response",
                json={
                    "ticket_id": "TKT-123",
                    "conversation_context": sample_conversation_context
                }
            )

            assert response.status_code == 403
            data = response.json()
            assert "detail" in data
            assert "Agent role required" in data["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_suggest_response_no_authentication(self, sample_conversation_context):
        """Test response suggestion without authentication"""
        response = client.post(
            "/ai/suggest-response",
            json={
                "ticket_id": "TKT-123",
                "conversation_context": sample_conversation_context
            }
        )

        assert response.status_code == 403  # FastAPI returns 403 for missing auth
    
    def test_suggest_response_invalid_ticket_id(self, mock_agent_user, sample_conversation_context):
        """Test response suggestion with invalid ticket ID"""
        app.dependency_overrides[get_current_user] = override_auth_dependency(mock_agent_user)

        try:
            response = client.post(
                "/ai/suggest-response",
                json={
                    "ticket_id": "",  # Empty ticket ID
                    "conversation_context": sample_conversation_context
                }
            )

            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_suggest_response_missing_ticket_id(self, mock_agent_user, sample_conversation_context):
        """Test response suggestion with missing ticket ID"""
        app.dependency_overrides[get_current_user] = override_auth_dependency(mock_agent_user)

        try:
            response = client.post(
                "/ai/suggest-response",
                json={
                    "conversation_context": sample_conversation_context
                }
            )

            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_suggest_response_invalid_context_format(self, mock_agent_user):
        """Test response suggestion with invalid conversation context format"""
        app.dependency_overrides[get_current_user] = override_auth_dependency(mock_agent_user)

        try:
            response = client.post(
                "/ai/suggest-response",
                json={
                    "ticket_id": "TKT-123",
                    "conversation_context": "invalid_format"  # Should be a list
                }
            )

            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()
    
    def test_suggest_response_too_many_context_messages(self, mock_agent_user):
        """Test response suggestion with too many context messages"""
        # Create more than 50 messages (the limit)
        large_context = []
        for i in range(51):
            large_context.append({
                "id": f"msg{i}",
                "ticket_id": "TKT-123",
                "sender_id": "507f1f77bcf86cd799439012",
                "sender_role": "user",
                "message_type": "user_message",
                "content": f"Message {i}",
                "isAI": False,
                "feedback": "none",
                "timestamp": "2023-01-01T10:00:00Z"
            })

        app.dependency_overrides[get_current_user] = override_auth_dependency(mock_agent_user)

        try:
            response = client.post(
                "/ai/suggest-response",
                json={
                    "ticket_id": "TKT-123",
                    "conversation_context": large_context
                }
            )

            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_agent_tools_info_success(self, mock_agent_user):
        """Test agent tools info endpoint success"""
        app.dependency_overrides[get_current_user] = override_auth_dependency(mock_agent_user)

        try:
            response = client.get("/ai/agent-tools")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "service" in data
            assert "description" in data
            assert "agent" in data
            assert "tools" in data
            assert "usage_guidelines" in data
            assert "limitations" in data

            # Verify agent information
            assert data["agent"]["username"] == "test_agent"
            assert data["agent"]["role"] == "it_agent"
            assert data["agent"]["department"] == "IT"

            # Verify tools information
            assert len(data["tools"]) > 0
            assert any(tool["name"] == "Response Suggestions" for tool in data["tools"])
        finally:
            app.dependency_overrides.clear()

    def test_agent_tools_info_hr_agent(self):
        """Test agent tools info for HR agent"""
        hr_agent = {
            "username": "hr_agent",
            "user_id": "507f1f77bcf86cd799439013",
            "role": "hr_agent"
        }

        app.dependency_overrides[get_current_user] = override_auth_dependency(hr_agent)

        try:
            response = client.get("/ai/agent-tools")

            assert response.status_code == 200
            data = response.json()
            assert data["agent"]["department"] == "HR"
        finally:
            app.dependency_overrides.clear()

    def test_agent_tools_info_unauthorized(self, mock_user_user):
        """Test agent tools info access denied for regular user"""
        app.dependency_overrides[get_current_user] = override_auth_dependency(mock_user_user)

        try:
            response = client.get("/ai/agent-tools")

            assert response.status_code == 403
            data = response.json()
            assert "Agent role required" in data["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_agent_tools_info_no_authentication(self):
        """Test agent tools info without authentication"""
        response = client.get("/ai/agent-tools")
        assert response.status_code == 403  # FastAPI returns 403 for missing auth
