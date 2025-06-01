"""
Tests for Webhook Integration

This module contains tests for webhook functionality integration
with the WebSocket chat system.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from bson import ObjectId

from app.services.webhook_service import WebhookService, fire_message_sent_webhook
from app.models.message import MessageModel
from app.schemas.message import MessageRole, MessageType, MessageFeedback
from app.routers.webhooks import MessageSentPayload


@pytest.fixture
def test_message():
    """Create a test message model"""
    return MessageModel(
        _id=ObjectId(),
        ticket_id=ObjectId(),
        sender_id=ObjectId(),
        sender_role=MessageRole.USER,
        message_type=MessageType.USER_MESSAGE,
        content="Test message content",
        isAI=False,
        feedback=MessageFeedback.NONE,
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def webhook_service():
    """Create webhook service instance"""
    return WebhookService(base_url="http://localhost:8000")


class TestWebhookService:
    """Test webhook service functionality"""

    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_fire_message_sent_webhook_success(self, mock_client, webhook_service, test_message):
        """Test successful message sent webhook firing"""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200

        # Mock the async context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client.return_value.__aexit__.return_value = None

        result = await webhook_service.fire_message_sent_webhook(test_message)

        assert result is True
        mock_client_instance.post.assert_called_once()

        # Verify the call was made with correct URL and payload
        call_args = mock_client_instance.post.call_args
        assert "/internal/webhook/on_message_sent" in call_args[0][0]  # URL is first positional arg
        assert "json" in call_args[1]

    @patch('httpx.AsyncClient.post')
    @pytest.mark.asyncio
    async def test_fire_message_sent_webhook_failure(self, mock_post, webhook_service, test_message):
        """Test message sent webhook firing with HTTP error"""
        # Mock failed HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value.__aenter__.return_value = mock_response
        
        result = await webhook_service.fire_message_sent_webhook(test_message)
        
        assert result is False

    @patch('httpx.AsyncClient.post')
    @pytest.mark.asyncio
    async def test_fire_message_sent_webhook_timeout(self, mock_post, webhook_service, test_message):
        """Test message sent webhook firing with timeout"""
        # Mock timeout exception
        import httpx
        mock_post.side_effect = httpx.TimeoutException("Request timeout")
        
        result = await webhook_service.fire_message_sent_webhook(test_message)
        
        assert result is False

    @patch('httpx.AsyncClient.post')
    @pytest.mark.asyncio
    async def test_fire_message_sent_webhook_request_error(self, mock_post, webhook_service, test_message):
        """Test message sent webhook firing with request error"""
        # Mock request error
        import httpx
        mock_post.side_effect = httpx.RequestError("Connection error")
        
        result = await webhook_service.fire_message_sent_webhook(test_message)
        
        assert result is False

    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_webhook_health_check_success(self, mock_client, webhook_service):
        """Test successful webhook health check"""
        # Mock successful health check response
        mock_response = MagicMock()
        mock_response.status_code = 200

        # Mock the async context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client.return_value.__aexit__.return_value = None

        result = await webhook_service.health_check()

        assert result is True
        mock_client_instance.get.assert_called_once()

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_webhook_health_check_failure(self, mock_get, webhook_service):
        """Test failed webhook health check"""
        # Mock failed health check response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await webhook_service.health_check()
        
        assert result is False

    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_fire_ticket_created_webhook(self, mock_client, webhook_service):
        """Test ticket created webhook firing"""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200

        # Mock the async context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client.return_value.__aexit__.return_value = None

        ticket_data = {
            "ticket_id": "TKT-123",
            "user_id": "user123",
            "title": "Test ticket",
            "status": "open"
        }

        result = await webhook_service.fire_ticket_created_webhook(ticket_data)

        assert result is True
        mock_client_instance.post.assert_called_once()

    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_fire_misuse_detected_webhook(self, mock_client, webhook_service):
        """Test misuse detected webhook firing"""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200

        # Mock the async context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client.return_value.__aexit__.return_value = None

        misuse_data = {
            "user_id": "user123",
            "ticket_id": "TKT-123",
            "misuse_type": "spam_content",
            "detected_at": datetime.utcnow().isoformat()
        }

        result = await webhook_service.fire_misuse_detected_webhook(misuse_data)

        assert result is True
        mock_client_instance.post.assert_called_once()


class TestMessageSentPayload:
    """Test message sent payload schema"""

    def test_message_sent_payload_creation(self, test_message):
        """Test creating message sent payload from message model"""
        payload = MessageSentPayload(
            message_id=str(test_message._id),
            ticket_id=str(test_message.ticket_id),
            sender_id=str(test_message.sender_id),
            sender_role=test_message.sender_role.value,
            message_type=test_message.message_type.value,
            content=test_message.content,
            isAI=test_message.isAI,
            feedback=test_message.feedback.value,
            timestamp=test_message.timestamp
        )
        
        assert payload.message_id == str(test_message._id)
        assert payload.ticket_id == str(test_message.ticket_id)
        assert payload.sender_id == str(test_message.sender_id)
        assert payload.sender_role == test_message.sender_role.value
        assert payload.message_type == test_message.message_type.value
        assert payload.content == test_message.content
        assert payload.isAI == test_message.isAI
        assert payload.feedback == test_message.feedback.value
        assert payload.timestamp == test_message.timestamp

    def test_message_sent_payload_serialization(self, test_message):
        """Test message sent payload JSON serialization"""
        payload = MessageSentPayload(
            message_id=str(test_message._id),
            ticket_id=str(test_message.ticket_id),
            sender_id=str(test_message.sender_id),
            sender_role=test_message.sender_role.value,
            message_type=test_message.message_type.value,
            content=test_message.content,
            isAI=test_message.isAI,
            feedback=test_message.feedback.value,
            timestamp=test_message.timestamp
        )
        
        # Test that payload can be serialized to JSON
        json_data = payload.model_dump()
        
        assert isinstance(json_data, dict)
        assert "message_id" in json_data
        assert "ticket_id" in json_data
        assert "content" in json_data
        assert json_data["isAI"] == test_message.isAI


class TestConvenienceFunctions:
    """Test convenience functions for webhook firing"""

    @patch('app.services.webhook_service.webhook_service.fire_message_sent_webhook')
    @pytest.mark.asyncio
    async def test_fire_message_sent_webhook_convenience(self, mock_fire, test_message):
        """Test convenience function for firing message sent webhook"""
        mock_fire.return_value = True
        
        result = await fire_message_sent_webhook(test_message)
        
        assert result is True
        mock_fire.assert_called_once_with(test_message)

    @patch('app.services.webhook_service.webhook_service.fire_ticket_created_webhook')
    @pytest.mark.asyncio
    async def test_fire_ticket_created_webhook_convenience(self, mock_fire):
        """Test convenience function for firing ticket created webhook"""
        from app.services.webhook_service import fire_ticket_created_webhook
        
        mock_fire.return_value = True
        ticket_data = {"ticket_id": "TKT-123"}
        
        result = await fire_ticket_created_webhook(ticket_data)
        
        assert result is True
        mock_fire.assert_called_once_with(ticket_data)

    @patch('app.services.webhook_service.webhook_service.health_check')
    @pytest.mark.asyncio
    async def test_webhook_health_check_convenience(self, mock_health):
        """Test convenience function for webhook health check"""
        from app.services.webhook_service import webhook_health_check
        
        mock_health.return_value = True
        
        result = await webhook_health_check()
        
        assert result is True
        mock_health.assert_called_once()


class TestWebhookIntegrationWithWebSocket:
    """Test webhook integration with WebSocket chat"""

    @patch('app.routers.ws_chat.fire_message_sent_webhook')
    @pytest.mark.asyncio
    async def test_websocket_chat_fires_webhook(self, mock_fire_webhook):
        """Test that WebSocket chat fires webhook when message is sent"""
        from app.routers.ws_chat import handle_chat_message
        from app.schemas.message import WebSocketMessageSchema
        
        # Mock webhook firing
        mock_fire_webhook.return_value = True
        
        # Mock message service
        with patch('app.routers.ws_chat.message_service') as mock_message_service:
            mock_saved_message = MagicMock()
            mock_saved_message._id = ObjectId()
            mock_saved_message.timestamp.isoformat.return_value = "2023-01-01T00:00:00"
            mock_message_service.save_message = AsyncMock(return_value=mock_saved_message)
            
            # Mock connection manager
            with patch('app.routers.ws_chat.connection_manager') as mock_manager:
                mock_manager.broadcast_to_ticket = AsyncMock()
                
                # Create test WebSocket message
                ws_message = WebSocketMessageSchema(
                    type="chat",
                    ticket_id="ticket123",
                    content="Test message",
                    message_type=MessageType.USER_MESSAGE,
                    isAI=False,
                    feedback=MessageFeedback.NONE
                )
                
                # Handle the chat message
                await handle_chat_message(ws_message, "user123", "user", "conn123")
                
                # Verify webhook was fired
                mock_fire_webhook.assert_called_once_with(mock_saved_message)

    @patch('app.routers.ws_chat.fire_message_sent_webhook')
    @pytest.mark.asyncio
    async def test_websocket_chat_handles_webhook_failure(self, mock_fire_webhook):
        """Test that WebSocket chat handles webhook firing failure gracefully"""
        from app.routers.ws_chat import handle_chat_message
        from app.schemas.message import WebSocketMessageSchema
        
        # Mock webhook firing failure
        mock_fire_webhook.return_value = False
        
        # Mock message service
        with patch('app.routers.ws_chat.message_service') as mock_message_service:
            mock_saved_message = MagicMock()
            mock_saved_message._id = ObjectId()
            mock_saved_message.timestamp.isoformat.return_value = "2023-01-01T00:00:00"
            mock_message_service.save_message = AsyncMock(return_value=mock_saved_message)
            
            # Mock connection manager
            with patch('app.routers.ws_chat.connection_manager') as mock_manager:
                mock_manager.broadcast_to_ticket = AsyncMock()
                
                # Create test WebSocket message
                ws_message = WebSocketMessageSchema(
                    type="chat",
                    ticket_id="ticket123",
                    content="Test message"
                )
                
                # Handle the chat message - should not raise exception even if webhook fails
                await handle_chat_message(ws_message, "user123", "user", "conn123")
                
                # Verify message was still saved and broadcasted
                mock_message_service.save_message.assert_called_once()
                mock_manager.broadcast_to_ticket.assert_called_once()
