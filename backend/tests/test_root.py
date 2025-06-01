import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    """Test that the root endpoint returns status 200"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "AI-First Internal Helpdesk Portal API is running"}


def test_health_endpoint():
    """Test that the health endpoint returns status 200"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "helpdesk-api"
