"""
Tests for Admin Analytics Endpoints

Tests the admin analytics API endpoints including overview, trending topics,
flagged users, user activity, and resolution time analytics.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


class TestAdminAnalyticsEndpoints:
    """Test cases for admin analytics endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def admin_user(self):
        """Mock admin user for authentication"""
        return {
            "user_id": "admin123",
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin"
        }
    
    @pytest.fixture
    def non_admin_user(self):
        """Mock non-admin user for authentication"""
        return {
            "user_id": "user123",
            "username": "user",
            "email": "user@example.com",
            "role": "user"
        }
    
    def test_analytics_overview_success(self, client, admin_user):
        """Test successful analytics overview retrieval"""
        mock_analytics = {
            "period": "Last 30 days",
            "generated_at": "2024-01-01T00:00:00",
            "ticket_statistics": {
                "total_tickets": 100,
                "open_tickets": 20,
                "closed_tickets": 50
            },
            "user_statistics": {
                "total_registered_users": 50,
                "active_users": 25
            },
            "misuse_statistics": {
                "total_reports": 5,
                "unreviewed_reports": 2
            },
            "resolution_statistics": {
                "overall": {"avg_hours": 24.5, "total_resolved": 50}
            }
        }
        
        with patch("app.routers.admin.analytics_service.get_overview_analytics", new_callable=AsyncMock) as mock_service:
            with patch("app.routers.admin.require_admin", return_value=admin_user):
                mock_service.return_value = mock_analytics

                response = client.get("/admin/analytics/overview?days=30")
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Analytics overview retrieved successfully"
                assert data["requested_by"] == "admin"
                assert data["analytics"]["ticket_statistics"]["total_tickets"] == 100
    
    def test_analytics_overview_all_time(self, client, admin_user):
        """Test analytics overview for all-time period"""
        mock_analytics = {
            "period": "All time",
            "generated_at": "2024-01-01T00:00:00",
            "ticket_statistics": {"total_tickets": 500},
            "user_statistics": {"total_registered_users": 100},
            "misuse_statistics": {"total_reports": 20},
            "resolution_statistics": {"overall": {"avg_hours": 30.0}}
        }
        
        with patch("routers.admin.analytics_service.get_overview_analytics", new_callable=AsyncMock) as mock_service:
            with patch("routers.admin.require_admin", return_value=admin_user):
                mock_service.return_value = mock_analytics

                response = client.get("/admin/analytics/overview")
                
                assert response.status_code == 200
                data = response.json()
                assert data["analytics"]["period"] == "All time"
    
    def test_trending_topics_success(self, client, admin_user):
        """Test successful trending topics retrieval"""
        mock_topics = {
            "period": "Last 30 days",
            "total_tickets_analyzed": 100,
            "trending_topics": [
                {
                    "topic": "Password Reset",
                    "count": 25,
                    "percentage": 25.0,
                    "examples": [{"ticket_id": "TKT-123", "title": "Password reset issue"}]
                },
                {
                    "topic": "Email Issues",
                    "count": 20,
                    "percentage": 20.0,
                    "examples": [{"ticket_id": "TKT-124", "title": "Email not working"}]
                }
            ]
        }
        
        with patch("routers.admin.analytics_service.get_trending_topics", new_callable=AsyncMock) as mock_service:
            with patch("routers.admin.require_admin", return_value=admin_user):
                mock_service.return_value = mock_topics

                response = client.get("/admin/analytics/trending-topics?days=30&limit=10")
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Trending topics retrieved successfully"
                assert len(data["topics_analysis"]["trending_topics"]) == 2
                assert data["topics_analysis"]["trending_topics"][0]["topic"] == "Password Reset"
    
    def test_flagged_users_analytics_success(self, client, admin_user):
        """Test successful flagged users analytics retrieval"""
        mock_flagged_analytics = {
            "period": "Last 30 days",
            "total_flagged_users": 3,
            "flagged_users": [
                {
                    "user_id": "user1",
                    "username": "problematic_user",
                    "total_violations": 5,
                    "violation_types": ["spam_content", "abusive_language"],
                    "unreviewed_count": 2
                }
            ],
            "violation_summary": [
                {"violation_type": "spam_content", "total_violations": 8, "unique_users_count": 3}
            ]
        }
        
        with patch("routers.admin.analytics_service.get_flagged_users_analytics", new_callable=AsyncMock) as mock_service:
            with patch("routers.admin.require_admin", return_value=admin_user):
                mock_service.return_value = mock_flagged_analytics

                response = client.get("/admin/analytics/flagged-users?days=30")
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Flagged users analytics retrieved successfully"
                assert data["flagged_users_analytics"]["total_flagged_users"] == 3
                assert len(data["flagged_users_analytics"]["flagged_users"]) == 1
    
    def test_user_activity_analytics_success(self, client, admin_user):
        """Test successful user activity analytics retrieval"""
        mock_activity_analytics = {
            "period": "Last 30 days",
            "most_active_users": [
                {
                    "user_id": "user1",
                    "username": "active_user",
                    "ticket_count": 15,
                    "resolution_rate": 80.0
                },
                {
                    "user_id": "user2",
                    "username": "another_user",
                    "ticket_count": 10,
                    "resolution_rate": 70.0
                }
            ]
        }
        
        with patch("routers.admin.analytics_service.get_user_activity_analytics", new_callable=AsyncMock) as mock_service:
            with patch("routers.admin.require_admin", return_value=admin_user):
                mock_service.return_value = mock_activity_analytics

                response = client.get("/admin/analytics/user-activity?days=30")
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "User activity analytics retrieved successfully"
                assert len(data["user_activity_analytics"]["most_active_users"]) == 2
                assert data["user_activity_analytics"]["most_active_users"][0]["username"] == "active_user"
    
    def test_resolution_time_analytics_success(self, client, admin_user):
        """Test successful resolution time analytics retrieval"""
        mock_overview = {
            "resolution_statistics": {
                "overall": {"avg_hours": 24.5, "total_resolved": 100},
                "by_department": {
                    "IT": {"avg_resolution_hours": 20.0, "total_resolved": 60},
                    "HR": {"avg_resolution_hours": 32.0, "total_resolved": 40}
                }
            }
        }
        
        with patch("routers.admin.analytics_service.get_overview_analytics", new_callable=AsyncMock) as mock_service:
            with patch("routers.admin.require_admin", return_value=admin_user):
                mock_service.return_value = mock_overview

                response = client.get("/admin/analytics/resolution-times?days=30")
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Resolution time analytics retrieved successfully"
                assert data["resolution_analytics"]["overall"]["avg_hours"] == 24.5
                assert "IT" in data["resolution_analytics"]["by_department"]
                assert "HR" in data["resolution_analytics"]["by_department"]
    
    def test_ticket_volume_analytics_success(self, client, admin_user):
        """Test successful ticket volume analytics retrieval"""
        mock_overview = {
            "ticket_statistics": {
                "total_tickets": 200,
                "open_tickets": 30,
                "assigned_tickets": 50,
                "resolved_tickets": 60,
                "closed_tickets": 60,
                "it_tickets": 120,
                "hr_tickets": 80,
                "high_urgency": 20,
                "medium_urgency": 150,
                "low_urgency": 30
            }
        }
        
        with patch("routers.admin.analytics_service.get_overview_analytics", new_callable=AsyncMock) as mock_service:
            with patch("routers.admin.require_admin", return_value=admin_user):
                mock_service.return_value = mock_overview

                response = client.get("/admin/analytics/ticket-volume?days=30")
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Ticket volume analytics retrieved successfully"
                assert data["ticket_volume_analytics"]["total_tickets"] == 200
                assert data["ticket_volume_analytics"]["it_tickets"] == 120
                assert data["ticket_volume_analytics"]["hr_tickets"] == 80
    
    def test_analytics_access_denied_non_admin(self, client, non_admin_user):
        """Test access denied for non-admin users"""
        with patch("routers.admin.require_admin") as mock_auth:
            mock_auth.side_effect = Exception("Access denied")

            response = client.get("/admin/analytics/overview")
            
            # The require_admin dependency should raise an exception
            # which FastAPI converts to a 500 error in test environment
            assert response.status_code == 500
    
    def test_analytics_invalid_parameters(self, client, admin_user):
        """Test analytics endpoints with invalid parameters"""
        with patch("routers.admin.require_admin", return_value=admin_user):
            # Test invalid days parameter (too large)
            response = client.get("/admin/analytics/overview?days=400")
            assert response.status_code == 422  # Validation error

            # Test invalid limit parameter (too large)
            response = client.get("/admin/analytics/trending-topics?limit=100")
            assert response.status_code == 422  # Validation error

            # Test negative days parameter
            response = client.get("/admin/analytics/user-activity?days=-5")
            assert response.status_code == 422  # Validation error
    
    def test_analytics_service_error_handling(self, client, admin_user):
        """Test error handling when analytics service fails"""
        with patch("routers.admin.analytics_service.get_overview_analytics", new_callable=AsyncMock) as mock_service:
            with patch("routers.admin.require_admin", return_value=admin_user):
                mock_service.side_effect = Exception("Database connection failed")

                response = client.get("/admin/analytics/overview")
                
                assert response.status_code == 500
                data = response.json()
                assert "Failed to get analytics overview" in data["detail"]
    
    def test_trending_topics_service_error(self, client, admin_user):
        """Test error handling for trending topics endpoint"""
        with patch("routers.admin.analytics_service.get_trending_topics", new_callable=AsyncMock) as mock_service:
            with patch("routers.admin.require_admin", return_value=admin_user):
                mock_service.side_effect = Exception("LLM service unavailable")

                response = client.get("/admin/analytics/trending-topics")
                
                assert response.status_code == 500
                data = response.json()
                assert "Failed to get trending topics" in data["detail"]
