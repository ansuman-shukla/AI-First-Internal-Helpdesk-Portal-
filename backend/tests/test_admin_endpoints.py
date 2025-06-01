"""
Unit tests for admin endpoints.

Tests the admin router functionality including manual misuse detection triggers,
misuse reports management, and scheduler status endpoints.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from bson import ObjectId

from main import app
from app.models.user import UserModel, UserRole


class TestAdminEndpoints:
    """Test cases for admin endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)
    
    @pytest.fixture
    def admin_user(self):
        """Create a mock admin user"""
        return UserModel(
            id=str(ObjectId()),
            username="admin_user",
            email="admin@test.com",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def regular_user(self):
        """Create a mock regular user"""
        return UserModel(
            id=str(ObjectId()),
            username="regular_user",
            email="user@test.com",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_trigger_manual_misuse_detection_success(self, client, admin_user):
        """Test successful manual misuse detection trigger"""
        mock_result = {
            "job_type": "manual_misuse_detection",
            "status": "Completed successfully",
            "statistics": {
                "users_processed": 5,
                "misuse_detected": 1,
                "reports_created": 1,
                "errors": 0
            }
        }
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.scheduler_service.trigger_manual_misuse_detection', 
                   return_value=mock_result) as mock_trigger:
            
            response = client.post("/admin/trigger-misuse-detection")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["message"] == "Misuse detection job completed"
            assert data["triggered_by"] == admin_user.username
            assert data["result"] == mock_result
            
            mock_trigger.assert_called_once_with(None)
    
    def test_trigger_manual_misuse_detection_with_window(self, client, admin_user):
        """Test manual misuse detection trigger with custom window"""
        mock_result = {"status": "Completed"}
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.scheduler_service.trigger_manual_misuse_detection', 
                   return_value=mock_result) as mock_trigger:
            
            response = client.post("/admin/trigger-misuse-detection?window_hours=48")
            
            assert response.status_code == 200
            mock_trigger.assert_called_once_with(48)
    
    def test_trigger_manual_misuse_detection_unauthorized(self, client, regular_user):
        """Test manual misuse detection trigger with non-admin user"""
        with patch('app.routers.admin.require_admin', side_effect=Exception("Unauthorized")):
            response = client.post("/admin/trigger-misuse-detection")
            
            assert response.status_code == 500  # Exception handling
    
    def test_trigger_manual_misuse_detection_error(self, client, admin_user):
        """Test manual misuse detection trigger with service error"""
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.scheduler_service.trigger_manual_misuse_detection', 
                   side_effect=Exception("Service error")):
            
            response = client.post("/admin/trigger-misuse-detection")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to trigger misuse detection" in data["detail"]
    
    def test_get_misuse_reports_success(self, client, admin_user):
        """Test successful retrieval of misuse reports"""
        mock_reports = [
            {
                "_id": str(ObjectId()),
                "user_id": str(ObjectId()),
                "detection_date": datetime.utcnow(),
                "misuse_type": "spam_content",
                "severity_level": "medium",
                "evidence_data": {
                    "ticket_ids": [str(ObjectId())],
                    "content_samples": ["Sample content"],
                    "pattern_analysis": "High volume detected"
                },
                "admin_reviewed": False,
                "action_taken": None,
                "ai_analysis_metadata": {
                    "detection_confidence": 0.8,
                    "model_reasoning": "Pattern analysis",
                    "analysis_timestamp": datetime.utcnow()
                }
            }
        ]
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.misuse_reports_service.get_all_unreviewed_reports', 
                   return_value=mock_reports):
            
            response = client.get("/admin/misuse-reports")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data["reports"]) == 1
            assert data["total_count"] == 1
            assert data["unreviewed_count"] == 1
            assert data["page"] == 1
            assert data["limit"] == 20
    
    def test_get_misuse_reports_pagination(self, client, admin_user):
        """Test misuse reports retrieval with pagination"""
        mock_reports = []
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.misuse_reports_service.get_all_unreviewed_reports', 
                   return_value=mock_reports):
            
            response = client.get("/admin/misuse-reports?page=2&limit=10")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["page"] == 2
            assert data["limit"] == 10
    
    def test_get_misuse_reports_unreviewed_only(self, client, admin_user):
        """Test getting only unreviewed misuse reports"""
        mock_reports = []
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.misuse_reports_service.get_all_unreviewed_reports', 
                   return_value=mock_reports) as mock_get_unreviewed:
            
            response = client.get("/admin/misuse-reports?unreviewed_only=true")
            
            assert response.status_code == 200
            mock_get_unreviewed.assert_called_once()
    
    def test_get_misuse_reports_error(self, client, admin_user):
        """Test handling error when getting misuse reports"""
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.misuse_reports_service.get_all_unreviewed_reports', 
                   side_effect=Exception("Database error")):
            
            response = client.get("/admin/misuse-reports")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to get misuse reports" in data["detail"]
    
    def test_mark_misuse_report_reviewed_success(self, client, admin_user):
        """Test successfully marking a misuse report as reviewed"""
        report_id = str(ObjectId())
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.misuse_reports_service.mark_report_reviewed', 
                   return_value=True) as mock_mark:
            
            response = client.post(f"/admin/misuse-reports/{report_id}/mark-reviewed?action_taken=User warned")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["message"] == "Misuse report marked as reviewed"
            assert data["report_id"] == report_id
            assert data["reviewed_by"] == admin_user.username
            assert data["action_taken"] == "User warned"
            
            mock_mark.assert_called_once_with(report_id, "User warned")
    
    def test_mark_misuse_report_reviewed_not_found(self, client, admin_user):
        """Test marking a non-existent misuse report as reviewed"""
        report_id = str(ObjectId())
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.misuse_reports_service.mark_report_reviewed', 
                   return_value=False):
            
            response = client.post(f"/admin/misuse-reports/{report_id}/mark-reviewed")
            
            assert response.status_code == 404
            data = response.json()
            assert f"Misuse report {report_id} not found" in data["detail"]
    
    def test_mark_misuse_report_reviewed_error(self, client, admin_user):
        """Test handling error when marking report as reviewed"""
        report_id = str(ObjectId())
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.misuse_reports_service.mark_report_reviewed', 
                   side_effect=Exception("Database error")):
            
            response = client.post(f"/admin/misuse-reports/{report_id}/mark-reviewed")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to mark report as reviewed" in data["detail"]
    
    def test_get_scheduler_status_success(self, client, admin_user):
        """Test successfully getting scheduler status"""
        mock_status = {
            "running": True,
            "jobs": [
                {
                    "id": "daily_misuse_detection",
                    "name": "Daily Misuse Detection Job",
                    "next_run": "2024-01-01T02:00:00",
                    "trigger": "cron"
                }
            ],
            "configuration": {
                "misuse_detection_enabled": True,
                "schedule": "0 2 * * *",
                "window_hours": 24
            }
        }
        
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.scheduler_service.get_scheduler_status', 
                   return_value=mock_status):
            
            response = client.get("/admin/scheduler-status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["message"] == "Scheduler status retrieved"
            assert data["requested_by"] == admin_user.username
            assert data["scheduler_status"] == mock_status
    
    def test_get_scheduler_status_error(self, client, admin_user):
        """Test handling error when getting scheduler status"""
        with patch('app.routers.admin.require_admin', return_value=admin_user), \
             patch('app.routers.admin.scheduler_service.get_scheduler_status', 
                   side_effect=Exception("Scheduler error")):
            
            response = client.get("/admin/scheduler-status")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to get scheduler status" in data["detail"]
    
    def test_get_misuse_report_by_id_not_implemented(self, client, admin_user):
        """Test getting a specific misuse report by ID (not yet implemented)"""
        report_id = str(ObjectId())
        
        with patch('app.routers.admin.require_admin', return_value=admin_user):
            response = client.get(f"/admin/misuse-reports/{report_id}")
            
            assert response.status_code == 501
            data = response.json()
            assert "Get report by ID not yet implemented" in data["detail"]
