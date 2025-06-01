"""
Unit tests for the misuse detector module.

Tests the detect_misuse_for_user function and related functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from app.services.ai.misuse_detector import detect_misuse_for_user, _collect_user_tickets, _is_misuse_detection_enabled
from app.models.ticket import TicketModel, TicketStatus, TicketUrgency, TicketDepartment


class TestDetectMisuseForUser:
    """Test cases for detect_misuse_for_user function"""

    @pytest.mark.asyncio
    async def test_detect_misuse_valid_user_no_tickets(self):
        """Test misuse detection for user with no tickets"""
        user_id = str(ObjectId())
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = []
            
            result = await detect_misuse_for_user(user_id)
            
            assert isinstance(result, dict)
            assert result["misuse_detected"] is False
            assert result["patterns"] == []
            assert result["user_id"] == user_id
            assert result["ticket_count"] == 0
            assert isinstance(result["analysis_date"], datetime)
            assert result["confidence_score"] == 0.5
            assert "analysis_metadata" in result
            assert result["analysis_metadata"]["detection_method"] == "safe_default"
            assert "No tickets to analyze" in result["analysis_metadata"]["reasoning"]

    @pytest.mark.asyncio
    async def test_detect_misuse_valid_user_few_tickets(self):
        """Test misuse detection for user with few normal tickets"""
        user_id = str(ObjectId())
        
        # Create mock tickets
        tickets = [
            self._create_mock_ticket("Password reset issue", "I can't reset my password"),
            self._create_mock_ticket("Software installation", "Need help installing Office")
        ]
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            with patch('app.services.ai.misuse_detector._is_misuse_detection_enabled', return_value=True):
                with patch('app.services.ai.misuse_detector.ai_config.GOOGLE_API_KEY', 'test-key'):
                    mock_collect.return_value = tickets
                    
                    result = await detect_misuse_for_user(user_id)
                    
                    assert isinstance(result, dict)
                    assert result["misuse_detected"] is False
                    assert result["patterns"] == []
                    assert result["user_id"] == user_id
                    assert result["ticket_count"] == 2
                    assert isinstance(result["analysis_date"], datetime)
                    assert result["confidence_score"] == 0.9
                    assert "analysis_metadata" in result
                    assert result["analysis_metadata"]["detection_method"] == "llm_stub"

    @pytest.mark.asyncio
    async def test_detect_misuse_high_volume_tickets(self):
        """Test misuse detection for user with high volume of tickets"""
        user_id = str(ObjectId())
        
        # Create 6 tickets (high volume)
        tickets = [
            self._create_mock_ticket(f"Issue {i}", f"Description {i}")
            for i in range(6)
        ]
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            with patch('app.services.ai.misuse_detector._is_misuse_detection_enabled', return_value=True):
                with patch('app.services.ai.misuse_detector.ai_config.GOOGLE_API_KEY', 'test-key'):
                    mock_collect.return_value = tickets
                    
                    result = await detect_misuse_for_user(user_id)
                    
                    assert isinstance(result, dict)
                    assert result["misuse_detected"] is False  # Only 1 pattern, need 2 for detection
                    assert "high_volume" in result["patterns"]
                    assert result["user_id"] == user_id
                    assert result["ticket_count"] == 6
                    assert result["confidence_score"] == 0.6

    @pytest.mark.asyncio
    async def test_detect_misuse_duplicate_titles(self):
        """Test misuse detection for user with duplicate ticket titles"""
        user_id = str(ObjectId())
        
        # Create tickets with duplicate titles
        tickets = [
            self._create_mock_ticket("Help me", "I need help with something"),
            self._create_mock_ticket("Help me", "I need help with another thing"),
            self._create_mock_ticket("Help me", "I need help again")
        ]
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            with patch('app.services.ai.misuse_detector._is_misuse_detection_enabled', return_value=True):
                with patch('app.services.ai.misuse_detector.ai_config.GOOGLE_API_KEY', 'test-key'):
                    mock_collect.return_value = tickets
                    
                    result = await detect_misuse_for_user(user_id)
                    
                    assert isinstance(result, dict)
                    assert result["misuse_detected"] is False  # Only 1 pattern, need 2 for detection
                    assert "duplicate_titles" in result["patterns"]
                    assert result["user_id"] == user_id
                    assert result["ticket_count"] == 3

    @pytest.mark.asyncio
    async def test_detect_misuse_short_descriptions(self):
        """Test misuse detection for user with many short descriptions"""
        user_id = str(ObjectId())
        
        # Create tickets with short descriptions (< 10 chars)
        tickets = [
            self._create_mock_ticket("Issue 1", "help"),
            self._create_mock_ticket("Issue 2", "fix"),
            self._create_mock_ticket("Issue 3", "broken")
        ]
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            with patch('app.services.ai.misuse_detector._is_misuse_detection_enabled', return_value=True):
                with patch('app.services.ai.misuse_detector.ai_config.GOOGLE_API_KEY', 'test-key'):
                    mock_collect.return_value = tickets
                    
                    result = await detect_misuse_for_user(user_id)
                    
                    assert isinstance(result, dict)
                    assert result["misuse_detected"] is False  # Only 1 pattern, need 2 for detection
                    assert "short_descriptions" in result["patterns"]
                    assert result["user_id"] == user_id
                    assert result["ticket_count"] == 3

    @pytest.mark.asyncio
    async def test_detect_misuse_multiple_patterns(self):
        """Test misuse detection for user with multiple suspicious patterns"""
        user_id = str(ObjectId())
        
        # Create tickets with multiple patterns: high volume + duplicate titles
        tickets = [
            self._create_mock_ticket("Help", "I need help"),
            self._create_mock_ticket("Help", "I need help"),
            self._create_mock_ticket("Help", "I need help"),
            self._create_mock_ticket("Help", "I need help"),
            self._create_mock_ticket("Help", "I need help"),
            self._create_mock_ticket("Help", "I need help")  # 6 tickets with same title
        ]
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            with patch('app.services.ai.misuse_detector._is_misuse_detection_enabled', return_value=True):
                with patch('app.services.ai.misuse_detector.ai_config.GOOGLE_API_KEY', 'test-key'):
                    mock_collect.return_value = tickets
                    
                    result = await detect_misuse_for_user(user_id)
                    
                    assert isinstance(result, dict)
                    assert result["misuse_detected"] is True  # 2+ patterns detected
                    assert "high_volume" in result["patterns"]
                    assert "duplicate_titles" in result["patterns"]
                    assert result["user_id"] == user_id
                    assert result["ticket_count"] == 6
                    assert result["confidence_score"] == 0.7

    @pytest.mark.asyncio
    async def test_detect_misuse_disabled(self):
        """Test misuse detection when disabled in configuration"""
        user_id = str(ObjectId())
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            with patch('app.services.ai.misuse_detector._is_misuse_detection_enabled', return_value=False):
                mock_collect.return_value = []
                
                result = await detect_misuse_for_user(user_id)
                
                assert isinstance(result, dict)
                assert result["misuse_detected"] is False
                assert result["patterns"] == []
                assert result["analysis_metadata"]["detection_method"] == "safe_default"
                assert "Misuse detection disabled" in result["analysis_metadata"]["reasoning"]

    @pytest.mark.asyncio
    async def test_detect_misuse_no_api_key(self):
        """Test misuse detection when Google API key is not configured"""
        user_id = str(ObjectId())
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            with patch('app.services.ai.misuse_detector._is_misuse_detection_enabled', return_value=True):
                with patch('app.services.ai.misuse_detector.ai_config.GOOGLE_API_KEY', ''):
                    mock_collect.return_value = []
                    
                    result = await detect_misuse_for_user(user_id)
                    
                    assert isinstance(result, dict)
                    assert result["misuse_detected"] is False
                    assert result["patterns"] == []
                    assert result["analysis_metadata"]["detection_method"] == "safe_default"
                    assert "API key not configured" in result["analysis_metadata"]["reasoning"]

    @pytest.mark.asyncio
    async def test_detect_misuse_custom_window(self):
        """Test misuse detection with custom time window"""
        user_id = str(ObjectId())
        window_hours = 48
        
        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = []
            
            result = await detect_misuse_for_user(user_id, window_hours)
            
            assert isinstance(result, dict)
            assert result["analysis_metadata"]["window_hours"] == window_hours
            mock_collect.assert_called_once_with(user_id, window_hours)

    @pytest.mark.asyncio
    async def test_detect_misuse_invalid_user_id_type(self):
        """Test misuse detection with invalid user_id type"""
        with pytest.raises(TypeError, match="user_id must be a string"):
            await detect_misuse_for_user(123)

    @pytest.mark.asyncio
    async def test_detect_misuse_invalid_window_hours_type(self):
        """Test misuse detection with invalid window_hours type"""
        user_id = str(ObjectId())
        with pytest.raises(TypeError, match="window_hours must be an integer"):
            await detect_misuse_for_user(user_id, "24")

    @pytest.mark.asyncio
    async def test_detect_misuse_empty_user_id(self):
        """Test misuse detection with empty user_id"""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await detect_misuse_for_user("")

    @pytest.mark.asyncio
    async def test_detect_misuse_negative_window_hours(self):
        """Test misuse detection with negative window_hours"""
        user_id = str(ObjectId())
        with pytest.raises(ValueError, match="window_hours must be positive"):
            await detect_misuse_for_user(user_id, -1)

    @pytest.mark.asyncio
    async def test_detect_misuse_database_error(self):
        """Test misuse detection when database query fails"""
        user_id = str(ObjectId())

        with patch('app.services.ai.misuse_detector._collect_user_tickets', new_callable=AsyncMock) as mock_collect:
            mock_collect.side_effect = Exception("Database connection failed")

            result = await detect_misuse_for_user(user_id)

            assert isinstance(result, dict)
            assert result["misuse_detected"] is False
            assert result["patterns"] == []
            assert result["analysis_metadata"]["detection_method"] == "error"
            assert "Database connection failed" in result["analysis_metadata"]["reasoning"]

    def _create_mock_ticket(self, title: str, description: str) -> TicketModel:
        """Helper method to create mock ticket"""
        return TicketModel(
            title=title,
            description=description,
            user_id=ObjectId(),
            urgency=TicketUrgency.MEDIUM,
            status=TicketStatus.OPEN,
            department=TicketDepartment.IT,
            assignee_id=None,
            misuse_flag=False,
            feedback=None,
            _id=ObjectId()
        )


class TestCollectUserTickets:
    """Test cases for _collect_user_tickets function"""

    @pytest.mark.asyncio
    async def test_collect_user_tickets_success(self):
        """Test successful ticket collection"""
        user_id = str(ObjectId())
        window_hours = 24

        # Mock database response
        mock_tickets_data = [
            {
                "_id": ObjectId(),
                "ticket_id": "TKT-123",
                "title": "Test ticket",
                "description": "Test description",
                "urgency": "medium",
                "status": "open",
                "user_id": ObjectId(user_id),
                "department": "IT",
                "assignee_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "closed_at": None,
                "misuse_flag": False,
                "feedback": None
            }
        ]

        with patch('app.services.ai.misuse_detector.get_database') as mock_get_db:
            mock_collection = MagicMock()
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=mock_tickets_data)
            mock_cursor.sort = MagicMock(return_value=mock_cursor)
            mock_collection.find = MagicMock(return_value=mock_cursor)
            mock_db = MagicMock()
            mock_db.__getitem__.return_value = mock_collection
            mock_get_db.return_value = mock_db

            tickets = await _collect_user_tickets(user_id, window_hours)

            assert len(tickets) == 1
            assert isinstance(tickets[0], TicketModel)
            assert tickets[0].title == "Test ticket"

    @pytest.mark.asyncio
    async def test_collect_user_tickets_empty_result(self):
        """Test ticket collection with no results"""
        user_id = str(ObjectId())
        window_hours = 24

        with patch('app.services.ai.misuse_detector.get_database') as mock_get_db:
            mock_collection = MagicMock()
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_cursor.sort = MagicMock(return_value=mock_cursor)
            mock_collection.find = MagicMock(return_value=mock_cursor)
            mock_db = MagicMock()
            mock_db.__getitem__.return_value = mock_collection
            mock_get_db.return_value = mock_db

            tickets = await _collect_user_tickets(user_id, window_hours)

            assert len(tickets) == 0
            assert isinstance(tickets, list)

    @pytest.mark.asyncio
    async def test_collect_user_tickets_database_error(self):
        """Test ticket collection with database error"""
        user_id = str(ObjectId())
        window_hours = 24

        with patch('app.services.ai.misuse_detector.get_database') as mock_get_db:
            mock_get_db.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception, match="Database connection failed"):
                await _collect_user_tickets(user_id, window_hours)


class TestMisuseDetectionEnabled:
    """Test cases for _is_misuse_detection_enabled function"""

    def test_misuse_detection_enabled_true(self):
        """Test when misuse detection is enabled"""
        with patch('app.services.ai.misuse_detector.ai_config.HSA_ENABLED', True):
            assert _is_misuse_detection_enabled() is True

    def test_misuse_detection_enabled_false(self):
        """Test when misuse detection is disabled"""
        with patch('app.services.ai.misuse_detector.ai_config.HSA_ENABLED', False):
            assert _is_misuse_detection_enabled() is False
