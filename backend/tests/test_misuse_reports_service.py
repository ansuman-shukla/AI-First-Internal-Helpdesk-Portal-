"""
Unit tests for the misuse reports service.

Tests the misuse reports service functionality including saving reports,
retrieving reports, and marking reports as reviewed.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from app.services.misuse_reports_service import MisuseReportsService


class TestMisuseReportsService:
    """Test cases for MisuseReportsService"""
    
    @pytest.fixture
    def reports_service(self):
        """Create a MisuseReportsService instance for testing"""
        service = MisuseReportsService()
        service.db = AsyncMock()  # Mock the database
        service.collection = AsyncMock()  # Mock the MongoDB collection
        return service
    
    @pytest.mark.asyncio
    async def test_save_misuse_report_success(self, reports_service):
        """Test successfully saving a misuse report"""
        detection_result = {
            "misuse_detected": True,
            "user_id": str(ObjectId()),
            "patterns": ["high_volume", "duplicate_titles"],
            "confidence_score": 0.8,
            "analysis_date": datetime.utcnow(),
            "analysis_metadata": {
                "tickets_analyzed": [str(ObjectId()), str(ObjectId())],
                "content_samples": ["Sample 1", "Sample 2"],
                "reasoning": "High volume and duplicate patterns detected"
            }
        }
        
        # Mock no existing report
        reports_service.collection.find_one.return_value = None
        
        # Mock successful insert
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        reports_service.collection.insert_one.return_value = mock_result
        
        report_id = await reports_service.save_misuse_report(detection_result)
        
        assert report_id is not None
        assert isinstance(report_id, str)
        
        # Verify insert was called
        reports_service.collection.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_misuse_report_no_misuse_detected(self, reports_service):
        """Test saving report when no misuse was detected"""
        detection_result = {
            "misuse_detected": False,
            "user_id": str(ObjectId()),
            "patterns": [],
            "confidence_score": 0.3
        }
        
        report_id = await reports_service.save_misuse_report(detection_result)
        
        assert report_id is None
        
        # Verify no database operations were performed
        reports_service.collection.find_one.assert_not_called()
        reports_service.collection.insert_one.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_save_misuse_report_duplicate_today(self, reports_service):
        """Test saving report when one already exists for today"""
        detection_result = {
            "misuse_detected": True,
            "user_id": str(ObjectId()),
            "patterns": ["high_volume"],
            "confidence_score": 0.8
        }
        
        # Mock existing report
        existing_report = {"_id": ObjectId()}
        reports_service.collection.find_one.return_value = existing_report
        
        report_id = await reports_service.save_misuse_report(detection_result)
        
        assert report_id == str(existing_report["_id"])
        
        # Verify no insert was attempted
        reports_service.collection.insert_one.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_save_misuse_report_missing_user_id(self, reports_service):
        """Test saving report with missing user_id"""
        detection_result = {
            "misuse_detected": True,
            "patterns": ["high_volume"],
            "confidence_score": 0.8
        }
        
        report_id = await reports_service.save_misuse_report(detection_result)
        
        assert report_id is None
    
    def test_determine_misuse_type(self, reports_service):
        """Test misuse type determination from patterns"""
        # Test abusive language (highest priority)
        assert reports_service._determine_misuse_type(["abusive_language", "high_volume"]) == "abusive_language"
        
        # Test jailbreak attempt
        assert reports_service._determine_misuse_type(["jailbreak_attempt", "duplicate_titles"]) == "jailbreak_attempt"
        
        # Test duplicate tickets
        assert reports_service._determine_misuse_type(["duplicate_titles", "short_descriptions"]) == "duplicate_tickets"
        
        # Test spam content
        assert reports_service._determine_misuse_type(["high_volume"]) == "spam_content"
        assert reports_service._determine_misuse_type(["short_descriptions"]) == "spam_content"
        
        # Test default fallback
        assert reports_service._determine_misuse_type(["unknown_pattern"]) == "spam_content"
    
    def test_determine_severity_level(self, reports_service):
        """Test severity level determination"""
        # Test high severity
        assert reports_service._determine_severity_level(["abusive_language"], 0.9) == "high"
        assert reports_service._determine_severity_level(["jailbreak_attempt"], 0.5) == "high"
        
        # Test medium severity
        assert reports_service._determine_severity_level(["high_volume"], 0.8) == "medium"
        assert reports_service._determine_severity_level(["duplicate_titles"], 0.75) == "medium"
        
        # Test low severity (low confidence)
        assert reports_service._determine_severity_level(["high_volume"], 0.6) == "low"
        
        # Test low severity (other patterns)
        assert reports_service._determine_severity_level(["short_descriptions"], 0.9) == "low"
    
    def test_create_report_document(self, reports_service):
        """Test report document creation"""
        user_id = str(ObjectId())
        detection_result = {
            "user_id": user_id,
            "patterns": ["high_volume", "duplicate_titles"],
            "confidence_score": 0.8,
            "analysis_date": datetime.utcnow(),
            "analysis_metadata": {
                "tickets_analyzed": [str(ObjectId()), str(ObjectId())],
                "content_samples": ["Sample 1", "Sample 2"],
                "reasoning": "Test reasoning"
            }
        }
        
        doc = reports_service._create_report_document(detection_result)
        
        assert doc["user_id"] == ObjectId(user_id)
        assert doc["misuse_type"] == "duplicate_tickets"
        assert doc["severity_level"] == "medium"
        assert doc["admin_reviewed"] is False
        assert doc["action_taken"] is None
        assert len(doc["evidence_data"]["ticket_ids"]) == 2
        assert len(doc["evidence_data"]["content_samples"]) == 2
        assert "pattern_analysis" in doc["evidence_data"]
        assert doc["ai_analysis_metadata"]["detection_confidence"] == 0.8
        assert "model_reasoning" in doc["ai_analysis_metadata"]
        assert "analysis_timestamp" in doc["ai_analysis_metadata"]
    
    @pytest.mark.asyncio
    async def test_get_reports_by_user_success(self, reports_service):
        """Test getting reports for a specific user"""
        user_id = str(ObjectId())
        
        mock_reports = [
            {
                "_id": ObjectId(),
                "user_id": ObjectId(user_id),
                "detection_date": datetime.utcnow(),
                "misuse_type": "spam_content",
                "evidence_data": {"ticket_ids": [ObjectId(), ObjectId()]}
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = mock_reports
        mock_cursor.sort.return_value = mock_cursor
        
        reports_service.collection.find.return_value = mock_cursor
        
        reports = await reports_service.get_reports_by_user(user_id)
        
        assert len(reports) == 1
        assert isinstance(reports[0]["_id"], str)
        assert isinstance(reports[0]["user_id"], str)
        assert isinstance(reports[0]["evidence_data"]["ticket_ids"][0], str)
    
    @pytest.mark.asyncio
    async def test_get_reports_by_user_error(self, reports_service):
        """Test handling error when getting reports by user"""
        user_id = str(ObjectId())
        
        reports_service.collection.find.side_effect = Exception("Database error")
        
        reports = await reports_service.get_reports_by_user(user_id)
        
        assert reports == []
    
    @pytest.mark.asyncio
    async def test_get_all_unreviewed_reports_success(self, reports_service):
        """Test getting all unreviewed reports"""
        mock_reports = [
            {
                "_id": ObjectId(),
                "user_id": ObjectId(),
                "admin_reviewed": False,
                "evidence_data": {"ticket_ids": [ObjectId()]}
            },
            {
                "_id": ObjectId(),
                "user_id": ObjectId(),
                "admin_reviewed": False,
                "evidence_data": {"ticket_ids": []}
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = mock_reports
        mock_cursor.sort.return_value = mock_cursor
        
        reports_service.collection.find.return_value = mock_cursor
        
        reports = await reports_service.get_all_unreviewed_reports()
        
        assert len(reports) == 2
        assert all(isinstance(report["_id"], str) for report in reports)
        assert all(isinstance(report["user_id"], str) for report in reports)
        
        # Verify query was for unreviewed reports
        reports_service.collection.find.assert_called_once_with({"admin_reviewed": False})
    
    @pytest.mark.asyncio
    async def test_get_all_unreviewed_reports_error(self, reports_service):
        """Test handling error when getting unreviewed reports"""
        reports_service.collection.find.side_effect = Exception("Database error")
        
        reports = await reports_service.get_all_unreviewed_reports()
        
        assert reports == []
    
    @pytest.mark.asyncio
    async def test_mark_report_reviewed_success(self, reports_service):
        """Test successfully marking a report as reviewed"""
        report_id = str(ObjectId())
        action_taken = "User warned"
        
        # Mock successful update
        mock_result = MagicMock()
        mock_result.modified_count = 1
        reports_service.collection.update_one.return_value = mock_result
        
        success = await reports_service.mark_report_reviewed(report_id, action_taken)
        
        assert success is True
        
        # Verify update was called with correct parameters
        reports_service.collection.update_one.assert_called_once()
        call_args = reports_service.collection.update_one.call_args
        assert call_args[0][0] == {"_id": ObjectId(report_id)}
        assert call_args[0][1]["$set"]["admin_reviewed"] is True
        assert call_args[0][1]["$set"]["action_taken"] == action_taken
        assert "reviewed_at" in call_args[0][1]["$set"]
    
    @pytest.mark.asyncio
    async def test_mark_report_reviewed_not_found(self, reports_service):
        """Test marking a report as reviewed when report doesn't exist"""
        report_id = str(ObjectId())
        
        # Mock no documents modified
        mock_result = MagicMock()
        mock_result.modified_count = 0
        reports_service.collection.update_one.return_value = mock_result
        
        success = await reports_service.mark_report_reviewed(report_id)
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_mark_report_reviewed_error(self, reports_service):
        """Test handling error when marking report as reviewed"""
        report_id = str(ObjectId())
        
        reports_service.collection.update_one.side_effect = Exception("Database error")
        
        success = await reports_service.mark_report_reviewed(report_id)
        
        assert success is False
