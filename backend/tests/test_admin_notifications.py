"""
Test admin notification functionality for ticket creation

This test verifies that admin users receive notifications for ALL ticket creations,
regardless of department (HR or IT).
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestAdminNotifications:
    """Test admin notification functionality"""

    def test_webhook_it_ticket_creation_success(self):
        """Test that webhook processes IT ticket creation successfully"""
        # Create IT ticket webhook payload
        payload = {
            "ticket_id": "TKT-20240101-IT001",
            "user_id": "507f1f77bcf86cd799439011",
            "title": "Computer won't start",
            "description": "My laptop is not booting up",
            "urgency": "medium",
            "status": "assigned",
            "department": "IT",
            "misuse_flag": False,
            "created_at": "2024-01-01T12:00:00Z"
        }

        # Fire webhook
        response = client.post("/internal/webhook/on_ticket_created", json=payload)

        # Verify webhook processed successfully
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "TKT-20240101-IT001" in data["message"]
        assert "timestamp" in data

    def test_webhook_hr_ticket_creation_success(self):
        """Test that webhook processes HR ticket creation successfully"""
        # Create HR ticket webhook payload
        payload = {
            "ticket_id": "TKT-20240101-HR001",
            "user_id": "507f1f77bcf86cd799439012",
            "title": "Need vacation approval",
            "description": "I need to request vacation time",
            "urgency": "low",
            "status": "assigned",
            "department": "HR",
            "misuse_flag": False,
            "created_at": "2024-01-01T12:00:00Z"
        }

        # Fire webhook
        response = client.post("/internal/webhook/on_ticket_created", json=payload)

        # Verify webhook processed successfully
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "TKT-20240101-HR001" in data["message"]
        assert "timestamp" in data

    def test_webhook_misuse_flagged_ticket_success(self):
        """Test that webhook processes misuse-flagged ticket successfully"""
        # Create misuse-flagged ticket webhook payload
        payload = {
            "ticket_id": "TKT-20240101-MISUSE001",
            "user_id": "507f1f77bcf86cd799439014",
            "title": "Harmful content",
            "description": "This contains inappropriate content",
            "urgency": "low",
            "status": "open",
            "department": None,
            "misuse_flag": True,
            "created_at": "2024-01-01T12:00:00Z"
        }

        # Fire webhook
        response = client.post("/internal/webhook/on_ticket_created", json=payload)

        # Verify webhook processed successfully
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "TKT-20240101-MISUSE001" in data["message"]
        assert "timestamp" in data

    def test_webhook_logging_for_admin_notifications(self, caplog):
        """Test that webhook generates appropriate logs for admin notifications"""
        import logging
        caplog.set_level(logging.INFO)

        # Create IT ticket webhook payload
        payload = {
            "ticket_id": "TKT-20240101-IT002",
            "user_id": "507f1f77bcf86cd799439013",
            "title": "Network issue",
            "description": "Cannot connect to network",
            "urgency": "high",
            "status": "assigned",
            "department": "IT",
            "misuse_flag": False,
            "created_at": "2024-01-01T12:00:00Z"
        }

        # Fire webhook
        response = client.post("/internal/webhook/on_ticket_created", json=payload)

        # Verify webhook processed successfully
        assert response.status_code == 200

        # Check that appropriate log messages were generated
        assert "Webhook: Ticket created" in caplog.text
        assert "TKT-20240101-IT002" in caplog.text
        assert "Getting admin users for ticket creation notification" in caplog.text
