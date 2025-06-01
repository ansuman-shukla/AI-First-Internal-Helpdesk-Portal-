"""
Tests for Analytics Service

Tests the analytics service functionality including overview analytics,
trending topics analysis, and user activity metrics.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.analytics_service import analytics_service


class TestAnalyticsService:
    """Test cases for AnalyticsService"""
    
    @pytest.fixture
    def mock_db_collections(self):
        """Mock database collections for testing"""
        mock_tickets = AsyncMock()
        mock_users = AsyncMock()
        mock_misuse_reports = AsyncMock()
        mock_messages = AsyncMock()

        # Mock the aggregate method to return a cursor with to_list method
        mock_tickets_cursor = AsyncMock()
        mock_tickets_cursor.to_list = AsyncMock()
        mock_tickets.aggregate = MagicMock(return_value=mock_tickets_cursor)

        mock_misuse_cursor = AsyncMock()
        mock_misuse_cursor.to_list = AsyncMock()
        mock_misuse_reports.aggregate = MagicMock(return_value=mock_misuse_cursor)

        analytics_service.tickets_collection = mock_tickets
        analytics_service.users_collection = mock_users
        analytics_service.misuse_reports_collection = mock_misuse_reports
        analytics_service.messages_collection = mock_messages
        analytics_service.db = MagicMock()

        return {
            "tickets": mock_tickets,
            "tickets_cursor": mock_tickets_cursor,
            "users": mock_users,
            "misuse_reports": mock_misuse_reports,
            "misuse_cursor": mock_misuse_cursor,
            "messages": mock_messages
        }
    
    @pytest.mark.asyncio
    async def test_get_overview_analytics_success(self, mock_db_collections):
        """Test successful overview analytics generation"""
        # Mock ticket statistics - need to mock multiple calls to aggregate
        ticket_stats = {
            "total_tickets": 100,
            "open_tickets": 20,
            "assigned_tickets": 30,
            "resolved_tickets": 25,
            "closed_tickets": 25,
            "it_tickets": 60,
            "hr_tickets": 40,
            "high_urgency": 10,
            "medium_urgency": 70,
            "low_urgency": 20,
            "flagged_tickets": 5
        }

        # Mock multiple aggregate calls for different analytics
        mock_db_collections["tickets_cursor"].to_list = AsyncMock(side_effect=[
            [ticket_stats],  # ticket volume stats
            [{"active_users": 25}],  # user activity stats
            []  # resolution time stats (empty for this test)
        ])

        # Mock user statistics
        mock_db_collections["users"].count_documents = AsyncMock(return_value=50)

        # Mock misuse statistics
        mock_db_collections["misuse_cursor"].to_list = AsyncMock(return_value=[{
            "total_reports": 10,
            "unreviewed_reports": 3,
            "high_severity": 2,
            "medium_severity": 5,
            "low_severity": 3
        }])

        result = await analytics_service.get_overview_analytics(30)

        assert result is not None
        assert "period" in result
        assert "ticket_statistics" in result
        assert "user_statistics" in result
        assert "misuse_statistics" in result
        assert "resolution_statistics" in result
        assert result["period"] == "Last 30 days"
        assert result["ticket_statistics"]["total_tickets"] == 100
    
    @pytest.mark.asyncio
    async def test_get_overview_analytics_all_time(self, mock_db_collections):
        """Test overview analytics for all-time period"""
        # Mock empty results
        mock_db_collections["tickets_cursor"].to_list = AsyncMock(side_effect=[
            [],  # ticket volume stats (empty)
            [],  # user activity stats (empty)
            []   # resolution time stats (empty)
        ])
        mock_db_collections["users"].count_documents = AsyncMock(return_value=0)
        mock_db_collections["misuse_cursor"].to_list = AsyncMock(return_value=[])

        result = await analytics_service.get_overview_analytics(None)

        assert result is not None
        assert result["period"] == "All time"
        assert result["ticket_statistics"]["total_tickets"] == 0
    
    @pytest.mark.asyncio
    async def test_get_trending_topics_success(self, mock_db_collections):
        """Test successful trending topics analysis"""
        # Mock ticket data
        mock_tickets = [
            {
                "_id": "ticket1",
                "title": "Password reset issue",
                "description": "Cannot reset my password",
                "department": "IT",
                "created_at": datetime.utcnow()
            },
            {
                "_id": "ticket2", 
                "title": "Email not working",
                "description": "Outlook email application not working",
                "department": "IT",
                "created_at": datetime.utcnow()
            },
            {
                "_id": "ticket3",
                "title": "Payroll question",
                "description": "Question about my payroll",
                "department": "HR",
                "created_at": datetime.utcnow()
            }
        ]
        
        mock_db_collections["tickets_cursor"].to_list = AsyncMock(return_value=mock_tickets)

        result = await analytics_service.get_trending_topics(30, 10)

        assert result is not None
        assert "period" in result
        assert "total_tickets_analyzed" in result
        assert "trending_topics" in result
        assert result["total_tickets_analyzed"] == 3
        assert isinstance(result["trending_topics"], list)

    @pytest.mark.asyncio
    async def test_get_trending_topics_no_tickets(self, mock_db_collections):
        """Test trending topics with no tickets"""
        mock_db_collections["tickets_cursor"].to_list = AsyncMock(return_value=[])

        result = await analytics_service.get_trending_topics(30, 10)

        assert result is not None
        assert result["total_tickets_analyzed"] == 0
        assert result["trending_topics"] == []
    
    @pytest.mark.asyncio
    async def test_get_flagged_users_analytics_success(self, mock_db_collections):
        """Test successful flagged users analytics"""
        # Mock flagged users data
        mock_flagged_users = [
            {
                "_id": "user1",
                "total_violations": 3,
                "violation_types": ["spam_content", "abusive_language"],
                "severity_levels": ["medium", "high"],
                "latest_violation": datetime.utcnow(),
                "unreviewed_count": 1
            }
        ]
        
        # Mock multiple aggregate calls for flagged users analytics
        mock_db_collections["misuse_cursor"].to_list = AsyncMock(side_effect=[
            mock_flagged_users,  # First call for flagged users
            []  # Second call for violation summary
        ])

        # Mock user details
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_user_data = [{
            "_id": "user1",
            "username": "testuser",
            "email": "test@example.com",
            "created_at": datetime.utcnow()
        }]

        mock_db_collections["users"].find = MagicMock(return_value=MockAsyncIterator(mock_user_data))

        result = await analytics_service.get_flagged_users_analytics(30)
        
        assert result is not None
        assert "period" in result
        assert "total_flagged_users" in result
        assert "flagged_users" in result
        assert "violation_summary" in result
        assert result["period"] == "Last 30 days"
    
    @pytest.mark.asyncio
    async def test_get_user_activity_analytics_success(self, mock_db_collections):
        """Test successful user activity analytics"""
        # Mock active users data
        mock_active_users = [
            {
                "_id": "user1",
                "ticket_count": 5,
                "open_tickets": 1,
                "resolved_tickets": 2,
                "closed_tickets": 2,
                "latest_ticket": datetime.utcnow()
            }
        ]
        
        mock_db_collections["tickets_cursor"].to_list = AsyncMock(return_value=mock_active_users)

        # Mock user details
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_active_user_data = [{
            "_id": "user1",
            "username": "activeuser",
            "email": "active@example.com",
            "role": "user"
        }]

        mock_db_collections["users"].find = MagicMock(return_value=MockAsyncIterator(mock_active_user_data))

        result = await analytics_service.get_user_activity_analytics(30)
        
        assert result is not None
        assert "period" in result
        assert "most_active_users" in result
        assert result["period"] == "Last 30 days"
        assert len(result["most_active_users"]) == 1
        assert result["most_active_users"][0]["username"] == "activeuser"
        assert result["most_active_users"][0]["resolution_rate"] == 40.0  # 2/5 * 100
    
    @pytest.mark.asyncio
    async def test_date_filter_generation(self, mock_db_collections):
        """Test date filter generation for different periods"""
        # Test with specific days
        date_filter = analytics_service._get_date_filter(7)
        assert "created_at" in date_filter
        assert "$gte" in date_filter["created_at"]
        
        # Test with None (all-time)
        date_filter = analytics_service._get_date_filter(None)
        assert date_filter == {}
    
    @pytest.mark.asyncio
    async def test_analytics_service_error_handling(self, mock_db_collections):
        """Test error handling in analytics service"""
        # Mock database error
        mock_db_collections["tickets_cursor"].to_list.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            await analytics_service.get_overview_analytics(30)

        assert "Database error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_resolution_time_calculation(self, mock_db_collections):
        """Test resolution time calculation logic"""
        # Mock resolution time data
        mock_resolution_data = [
            {
                "_id": "IT",
                "avg_resolution_time": 24.5,  # hours
                "min_resolution_time": 2.0,
                "max_resolution_time": 72.0,
                "total_resolved": 10
            },
            {
                "_id": "HR",
                "avg_resolution_time": 48.0,  # hours
                "min_resolution_time": 4.0,
                "max_resolution_time": 120.0,
                "total_resolved": 5
            }
        ]
        
        # Mock the aggregation pipeline calls
        mock_db_collections["tickets_cursor"].to_list = AsyncMock(side_effect=[
            # First call for ticket stats
            [{
                "total_tickets": 15,
                "open_tickets": 0,
                "assigned_tickets": 0,
                "resolved_tickets": 0,
                "closed_tickets": 15,
                "it_tickets": 10,
                "hr_tickets": 5,
                "high_urgency": 3,
                "medium_urgency": 10,
                "low_urgency": 2,
                "flagged_tickets": 0
            }],
            # Second call for user activity
            [{"active_users": 8}],
            # Third call for resolution times
            mock_resolution_data
        ])

        mock_db_collections["users"].count_documents = AsyncMock(return_value=20)
        mock_db_collections["misuse_cursor"].to_list = AsyncMock(return_value=[{
            "total_reports": 0,
            "unreviewed_reports": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0
        }])
        
        result = await analytics_service.get_overview_analytics(30)
        
        resolution_stats = result["resolution_statistics"]
        assert "overall" in resolution_stats
        assert "by_department" in resolution_stats
        assert resolution_stats["overall"]["total_resolved"] == 15
        assert "IT" in resolution_stats["by_department"]
        assert "HR" in resolution_stats["by_department"]
        assert resolution_stats["by_department"]["IT"]["avg_resolution_hours"] == 24.5
        assert resolution_stats["by_department"]["HR"]["avg_resolution_hours"] == 48.0
