"""
Unit tests for webhook endpoints

Tests the webhook stub implementations for ticket creation and misuse detection.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from main import app

client = TestClient(app)


class TestWebhookEndpoints:
    """Test webhook endpoint functionality"""

    def test_on_ticket_created_webhook_success(self):
        """Test successful ticket creation webhook"""
        payload = {
            "ticket_id": "TKT-20240101-ABC123",
            "user_id": "507f1f77bcf86cd799439011",
            "title": "Computer won't start",
            "description": "My laptop is not booting up",
            "urgency": "medium",
            "status": "assigned",
            "department": "IT",
            "misuse_flag": False,
            "created_at": "2024-01-01T12:00:00Z"
        }
        
        response = client.post("/internal/webhook/on_ticket_created", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "TKT-20240101-ABC123" in data["message"]
        assert "timestamp" in data

    def test_on_ticket_created_webhook_with_misuse_flag(self):
        """Test ticket creation webhook with misuse flag"""
        payload = {
            "ticket_id": "TKT-20240101-DEF456",
            "user_id": "507f1f77bcf86cd799439012",
            "title": "Harmful content test",
            "description": "This is flagged content",
            "urgency": "low",
            "status": "open",
            "department": None,
            "misuse_flag": True,
            "created_at": "2024-01-01T12:00:00Z"
        }
        
        response = client.post("/internal/webhook/on_ticket_created", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "TKT-20240101-DEF456" in data["message"]

    def test_on_ticket_created_webhook_validation_error(self):
        """Test ticket creation webhook with invalid payload"""
        payload = {
            "ticket_id": "TKT-20240101-GHI789",
            # Missing required fields
            "urgency": "medium"
        }
        
        response = client.post("/internal/webhook/on_ticket_created", json=payload)
        
        assert response.status_code == 422  # Validation error

    def test_on_misuse_detected_webhook_success(self):
        """Test successful misuse detection webhook"""
        payload = {
            "user_id": "507f1f77bcf86cd799439013",
            "ticket_id": "TKT-20240101-JKL012",
            "misuse_type": "spam",
            "confidence_score": 0.95,
            "detected_at": "2024-01-01T12:00:00Z"
        }
        
        response = client.post("/internal/webhook/on_misuse_detected", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "507f1f77bcf86cd799439013" in data["message"]
        assert "timestamp" in data

    def test_on_misuse_detected_webhook_without_confidence(self):
        """Test misuse detection webhook without confidence score"""
        payload = {
            "user_id": "507f1f77bcf86cd799439014",
            "ticket_id": "TKT-20240101-MNO345",
            "misuse_type": "harassment",
            "detected_at": "2024-01-01T12:00:00Z"
        }
        
        response = client.post("/internal/webhook/on_misuse_detected", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_on_misuse_detected_webhook_validation_error(self):
        """Test misuse detection webhook with invalid payload"""
        payload = {
            "user_id": "507f1f77bcf86cd799439015",
            # Missing required fields
            "confidence_score": 0.8
        }
        
        response = client.post("/internal/webhook/on_misuse_detected", json=payload)
        
        assert response.status_code == 422  # Validation error

    def test_on_message_sent_webhook_success(self):
        """Test successful message sent webhook"""
        payload = {
            "message_id": "507f1f77bcf86cd799439020",
            "ticket_id": "TKT-20240101-PQR678",
            "sender_id": "507f1f77bcf86cd799439016",
            "sender_role": "user",
            "message_type": "user_message",
            "content": "This is a test message",
            "isAI": False,
            "feedback": "none",
            "timestamp": "2024-01-01T12:00:00Z"
        }

        response = client.post("/internal/webhook/on_message_sent", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Message webhook processed for ticket TKT-20240101-PQR678" in data["message"]
        assert "timestamp" in data

    def test_on_message_sent_webhook_empty_payload(self):
        """Test message sent webhook with empty payload"""
        payload = {}

        response = client.post("/internal/webhook/on_message_sent", json=payload)

        assert response.status_code == 422  # Validation error for missing required fields

    def test_webhook_health_check(self):
        """Test webhook health check endpoint"""
        response = client.get("/internal/webhook/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "webhook-system"
        assert "timestamp" in data

    def test_webhook_endpoints_logging(self, caplog):
        """Test that webhook endpoints generate appropriate logs"""
        import logging
        caplog.set_level(logging.INFO)

        payload = {
            "ticket_id": "TKT-20240101-STU901",
            "user_id": "507f1f77bcf86cd799439017",
            "title": "Test ticket",
            "description": "Test description",
            "urgency": "medium",
            "status": "assigned",
            "department": "IT",
            "misuse_flag": False,
            "created_at": "2024-01-01T12:00:00Z"
        }

        response = client.post("/internal/webhook/on_ticket_created", json=payload)

        assert response.status_code == 200
        # Check that appropriate log messages were generated
        assert "Webhook: Ticket created" in caplog.text
        assert "TKT-20240101-STU901" in caplog.text

    def test_webhook_endpoints_with_different_content_types(self):
        """Test webhook endpoints handle different content types appropriately"""
        # Test with form data (should fail)
        response = client.post(
            "/internal/webhook/on_ticket_created",
            data={"ticket_id": "test"}
        )
        assert response.status_code == 422

        # Test with valid JSON
        payload = {
            "ticket_id": "TKT-20240101-VWX234",
            "user_id": "507f1f77bcf86cd799439018",
            "title": "Test ticket",
            "description": "Test description",
            "urgency": "medium",
            "status": "assigned",
            "department": "IT",
            "misuse_flag": False,
            "created_at": "2024-01-01T12:00:00Z"
        }
        
        response = client.post("/internal/webhook/on_ticket_created", json=payload)
        assert response.status_code == 200
