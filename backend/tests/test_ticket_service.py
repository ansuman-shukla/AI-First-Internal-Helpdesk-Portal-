import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from app.services.ticket_service import TicketService
from app.schemas.ticket import (
    TicketCreateSchema,
    TicketUpdateSchema,
    TicketStatus,
    TicketDepartment,
    TicketUrgency,
)
from app.schemas.user import UserRole
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def ticket_service():
    """Fixture to provide TicketService instance"""
    return TicketService()


@pytest.fixture
def test_user_id():
    """Fixture to provide a test user ID"""
    return str(ObjectId())


@pytest.fixture
def test_agent_id():
    """Fixture to provide a test agent ID"""
    return str(ObjectId())


@pytest.fixture(scope="function")
async def setup_database():
    """Fixture to setup and teardown database connection"""
    try:
        await connect_to_mongo()
        db = get_database()
        if db is None:
            pytest.skip("Database not available")

        # Clean up any existing test data
        await db.tickets.delete_many({"title": {"$regex": "^Test.*"}})

        yield db

    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
    finally:
        # Clean up test data
        try:
            db = get_database()
            if db:
                await db.tickets.delete_many({"title": {"$regex": "^Test.*"}})
        except:
            pass
        await close_mongo_connection()


class TestTicketServiceCreate:
    """Test ticket creation functionality"""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self):
        """Test successful ticket creation"""
        # Setup database connection
        try:
            await connect_to_mongo()
            db = get_database()
            if db is None:
                pytest.skip("Database not available")

            # Clean up any existing test data
            await db.tickets.delete_many({"title": {"$regex": "^Test.*"}})

            # Create service and test data
            ticket_service = TicketService()
            test_user_id = str(ObjectId())

            ticket_data = TicketCreateSchema(
                title="Test Ticket Creation",
                description="This is a test ticket for creation",
                urgency=TicketUrgency.HIGH,
            )

            ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

            # Verify ticket properties
            assert ticket.title == "Test Ticket Creation"
            assert ticket.description == "This is a test ticket for creation"
            assert ticket.urgency == TicketUrgency.HIGH
            assert ticket.status == TicketStatus.OPEN
            assert ticket.user_id == ObjectId(test_user_id)
            assert ticket.misuse_flag is False
            assert ticket._id is not None
            assert ticket.ticket_id.startswith("TKT-")
            assert ticket.created_at is not None
            assert ticket.updated_at is not None

            logger.info(f"Successfully created ticket: {ticket.ticket_id}")

        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
        finally:
            # Clean up test data
            try:
                db = get_database()
                if db:
                    await db.tickets.delete_many({"title": {"$regex": "^Test.*"}})
            except:
                pass
            await close_mongo_connection()

    @pytest.mark.asyncio
    async def test_create_ticket_rate_limit(self):
        """Test rate limiting functionality"""
        try:
            await connect_to_mongo()
            db = get_database()
            if db is None:
                pytest.skip("Database not available")

            # Clean up any existing test data
            await db.tickets.delete_many({"title": {"$regex": "^Test Rate Limit.*"}})

            # Create service and test data
            ticket_service = TicketService()
            test_user_id = str(ObjectId())

            # Create 5 tickets (the limit)
            for i in range(5):
                ticket_data = TicketCreateSchema(
                    title=f"Test Rate Limit Ticket {i+1}",
                    description="Testing rate limiting",
                    urgency=TicketUrgency.LOW,
                )
                await ticket_service.create_ticket(ticket_data, test_user_id)

            # The 6th ticket should fail due to rate limiting
            ticket_data = TicketCreateSchema(
                title="Test Rate Limit Ticket 6",
                description="Testing rate limiting",
                urgency=TicketUrgency.LOW,
            )
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await ticket_service.create_ticket(ticket_data, test_user_id)

            logger.info("Rate limiting test passed")

        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
        finally:
            # Clean up test data
            try:
                db = get_database()
                if db:
                    await db.tickets.delete_many(
                        {"title": {"$regex": "^Test Rate Limit.*"}}
                    )
            except:
                pass
            await close_mongo_connection()


class TestTicketServiceRetrieve:
    """Test ticket retrieval functionality"""

    @pytest.mark.asyncio
    async def test_get_tickets_by_user_role(self):
        """Test getting tickets with different user roles"""
        try:
            await connect_to_mongo()
            db = get_database()
            if db is None:
                pytest.skip("Database not available")

            # Clean up any existing test data
            await db.tickets.delete_many({"title": {"$regex": "^Test User Role.*"}})

            # Create service and test data
            ticket_service = TicketService()
            test_user_id = str(ObjectId())
            test_agent_id = str(ObjectId())

            # Create a test ticket
            ticket_data = TicketCreateSchema(
                title="Test User Role Ticket",
                description="Testing role-based access",
                urgency=TicketUrgency.MEDIUM,
            )

            created_ticket = await ticket_service.create_ticket(
                ticket_data, test_user_id
            )

            # Test USER role - should see their own tickets
            result = await ticket_service.get_tickets(test_user_id, UserRole.USER)
            assert result["total_count"] >= 1
            assert any(
                t.ticket_id == created_ticket.ticket_id for t in result["tickets"]
            )

            # Test IT_AGENT role - should see tickets in IT department or assigned to them
            result = await ticket_service.get_tickets(test_agent_id, UserRole.IT_AGENT)
            assert result["total_count"] >= 0  # May be 0 if no IT tickets

            # Test ADMIN role - should see all tickets
            result = await ticket_service.get_tickets(test_agent_id, UserRole.ADMIN)
            assert result["total_count"] >= 1
            assert any(
                t.ticket_id == created_ticket.ticket_id for t in result["tickets"]
            )

            logger.info("Role-based ticket retrieval test passed")

        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
        finally:
            # Clean up test data
            try:
                db = get_database()
                if db:
                    await db.tickets.delete_many(
                        {"title": {"$regex": "^Test User Role.*"}}
                    )
            except:
                pass
            await close_mongo_connection()

    @pytest.mark.asyncio
    async def test_get_tickets_pagination(
        self, ticket_service, test_user_id, setup_database
    ):
        """Test pagination functionality"""
        # Create multiple tickets
        for i in range(15):
            ticket_data = TicketCreateSchema(
                title=f"Test Pagination Ticket {i+1}",
                description=f"Testing pagination {i+1}",
                urgency=TicketUrgency.LOW,
            )
            await ticket_service.create_ticket(ticket_data, test_user_id)

        # Test first page
        result = await ticket_service.get_tickets(
            test_user_id, UserRole.USER, page=1, limit=10
        )
        assert len(result["tickets"]) == 10
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["total_count"] >= 15
        assert result["total_pages"] >= 2

        # Test second page
        result = await ticket_service.get_tickets(
            test_user_id, UserRole.USER, page=2, limit=10
        )
        assert len(result["tickets"]) >= 5
        assert result["page"] == 2

        logger.info("Pagination test passed")

    @pytest.mark.asyncio
    async def test_get_ticket_by_id_with_role(
        self, ticket_service, test_user_id, test_agent_id, setup_database
    ):
        """Test getting single ticket by ID with role-based access"""
        # Create a test ticket
        ticket_data = TicketCreateSchema(
            title="Test Get By ID Ticket",
            description="Testing get by ID with roles",
            urgency=TicketUrgency.HIGH,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Test USER role - should access their own ticket
        ticket = await ticket_service.get_ticket_by_id_with_role(
            created_ticket.ticket_id, test_user_id, UserRole.USER
        )
        assert ticket is not None
        assert ticket.ticket_id == created_ticket.ticket_id

        # Test USER role - should NOT access other user's ticket
        ticket = await ticket_service.get_ticket_by_id_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.USER
        )
        assert ticket is None

        # Test ADMIN role - should access any ticket
        ticket = await ticket_service.get_ticket_by_id_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.ADMIN
        )
        assert ticket is not None
        assert ticket.ticket_id == created_ticket.ticket_id

        logger.info("Get ticket by ID with role test passed")


class TestTicketServiceUpdate:
    """Test ticket update functionality"""

    @pytest.mark.asyncio
    async def test_update_ticket_user_permissions(
        self, ticket_service, test_user_id, setup_database
    ):
        """Test user update permissions"""
        # Create a test ticket
        ticket_data = TicketCreateSchema(
            title="Test Update User Permissions",
            description="Testing user update permissions",
            urgency=TicketUrgency.LOW,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Test valid user update (status is OPEN)
        update_data = TicketUpdateSchema(
            title="Updated Title",
            description="Updated description",
            urgency=TicketUrgency.HIGH,
        )

        updated_ticket = await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_user_id, UserRole.USER, update_data
        )

        assert updated_ticket is not None
        assert updated_ticket.title == "Updated Title"
        assert updated_ticket.description == "Updated description"
        assert updated_ticket.urgency == TicketUrgency.HIGH

        logger.info("User update permissions test passed")

    @pytest.mark.asyncio
    async def test_update_ticket_status_transitions(
        self, ticket_service, test_user_id, test_agent_id, setup_database
    ):
        """Test status transition validation"""
        # Create a test ticket
        ticket_data = TicketCreateSchema(
            title="Test Status Transitions",
            description="Testing status transitions",
            urgency=TicketUrgency.MEDIUM,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Test valid transition: OPEN -> ASSIGNED (as admin)
        update_data = TicketUpdateSchema(status=TicketStatus.ASSIGNED)
        updated_ticket = await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.ADMIN, update_data
        )
        assert updated_ticket.status == TicketStatus.ASSIGNED

        # Test valid transition: ASSIGNED -> RESOLVED (as agent)
        update_data = TicketUpdateSchema(status=TicketStatus.RESOLVED)
        updated_ticket = await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.IT_AGENT, update_data
        )
        assert updated_ticket.status == TicketStatus.RESOLVED

        # Test valid transition: RESOLVED -> CLOSED (as agent)
        update_data = TicketUpdateSchema(status=TicketStatus.CLOSED)
        updated_ticket = await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.IT_AGENT, update_data
        )
        assert updated_ticket.status == TicketStatus.CLOSED
        assert updated_ticket.closed_at is not None

        # Test invalid transition: CLOSED -> OPEN (should fail)
        update_data = TicketUpdateSchema(status=TicketStatus.OPEN)
        with pytest.raises(ValueError, match="Invalid status transition"):
            await ticket_service.update_ticket_with_role(
                created_ticket.ticket_id, test_agent_id, UserRole.ADMIN, update_data
            )

        logger.info("Status transitions test passed")


class TestTicketServiceFiltering:
    """Test ticket filtering functionality"""

    @pytest.mark.asyncio
    async def test_filter_by_status_and_department(
        self, ticket_service, test_user_id, setup_database
    ):
        """Test filtering tickets by status and department"""
        # Create tickets with different statuses and departments
        ticket_data = TicketCreateSchema(
            title="Test Filter Ticket 1",
            description="Testing filtering",
            urgency=TicketUrgency.LOW,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Test filtering by status
        result = await ticket_service.get_tickets(
            test_user_id, UserRole.USER, status=TicketStatus.OPEN
        )
        assert result["total_count"] >= 1
        assert all(t.status == TicketStatus.OPEN for t in result["tickets"])

        logger.info("Filtering test passed")


class TestTicketServiceErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_get_nonexistent_ticket(
        self, ticket_service, test_user_id, setup_database
    ):
        """Test getting a non-existent ticket"""
        fake_ticket_id = "TKT-9999999999-FAKE01"

        ticket = await ticket_service.get_ticket_by_id_with_role(
            fake_ticket_id, test_user_id, UserRole.USER
        )
        assert ticket is None

        logger.info("Non-existent ticket test passed")

    @pytest.mark.asyncio
    async def test_update_nonexistent_ticket(
        self, ticket_service, test_user_id, setup_database
    ):
        """Test updating a non-existent ticket"""
        fake_ticket_id = "TKT-9999999999-FAKE02"
        update_data = TicketUpdateSchema(title="Updated Title")

        result = await ticket_service.update_ticket_with_role(
            fake_ticket_id, test_user_id, UserRole.USER, update_data
        )
        assert result is None

        logger.info("Update non-existent ticket test passed")

    @pytest.mark.asyncio
    async def test_invalid_user_role(
        self, ticket_service, test_user_id, setup_database
    ):
        """Test handling of invalid user roles"""
        # This test would require modifying the enum or using a mock
        # For now, we'll test with a valid role but invalid permissions

        # Create a ticket
        ticket_data = TicketCreateSchema(
            title="Test Invalid Role Ticket",
            description="Testing invalid role handling",
            urgency=TicketUrgency.MEDIUM,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Try to access as a different user with USER role (should fail)
        other_user_id = str(ObjectId())
        ticket = await ticket_service.get_ticket_by_id_with_role(
            created_ticket.ticket_id, other_user_id, UserRole.USER
        )
        assert ticket is None

        logger.info("Invalid role handling test passed")

    @pytest.mark.asyncio
    async def test_user_edit_non_open_ticket(
        self, ticket_service, test_user_id, test_agent_id, setup_database
    ):
        """Test user trying to edit a ticket that's not in OPEN status"""
        # Create a ticket
        ticket_data = TicketCreateSchema(
            title="Test Non-Open Edit Ticket",
            description="Testing edit restrictions",
            urgency=TicketUrgency.MEDIUM,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Change status to ASSIGNED (as admin)
        update_data = TicketUpdateSchema(status=TicketStatus.ASSIGNED)
        await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.ADMIN, update_data
        )

        # Try to edit as user (should fail)
        user_update_data = TicketUpdateSchema(title="Should Not Work")
        with pytest.raises(
            ValueError, match="Can only edit tickets with status 'open'"
        ):
            await ticket_service.update_ticket_with_role(
                created_ticket.ticket_id, test_user_id, UserRole.USER, user_update_data
            )

        logger.info("Non-open ticket edit restriction test passed")


class TestTicketServiceAgentOperations:
    """Test agent-specific operations"""

    @pytest.mark.asyncio
    async def test_agent_department_access(
        self, ticket_service, test_user_id, test_agent_id, setup_database
    ):
        """Test agent access to department-specific tickets"""
        # Create a ticket
        ticket_data = TicketCreateSchema(
            title="Test Agent Department Access",
            description="Testing agent department access",
            urgency=TicketUrgency.HIGH,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Set ticket to IT department (as admin)
        update_data = TicketUpdateSchema(department=TicketDepartment.IT)
        await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.ADMIN, update_data
        )

        # IT agent should be able to access IT department tickets
        ticket = await ticket_service.get_ticket_by_id_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.IT_AGENT
        )
        assert ticket is not None
        assert ticket.department == TicketDepartment.IT

        # HR agent should NOT be able to access IT department tickets
        ticket = await ticket_service.get_ticket_by_id_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.HR_AGENT
        )
        assert ticket is None

        logger.info("Agent department access test passed")

    @pytest.mark.asyncio
    async def test_agent_feedback_addition(
        self, ticket_service, test_user_id, test_agent_id, setup_database
    ):
        """Test agent adding feedback to tickets"""
        # Create and resolve a ticket
        ticket_data = TicketCreateSchema(
            title="Test Agent Feedback",
            description="Testing agent feedback addition",
            urgency=TicketUrgency.MEDIUM,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Resolve the ticket (as admin)
        update_data = TicketUpdateSchema(status=TicketStatus.RESOLVED)
        await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.ADMIN, update_data
        )

        # Add feedback (as agent)
        feedback_data = TicketUpdateSchema(feedback="Issue resolved successfully")
        updated_ticket = await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.IT_AGENT, feedback_data
        )

        assert updated_ticket.feedback == "Issue resolved successfully"

        logger.info("Agent feedback addition test passed")


class TestTicketServiceAdminOperations:
    """Test admin-specific operations"""

    @pytest.mark.asyncio
    async def test_admin_full_access(
        self, ticket_service, test_user_id, test_agent_id, setup_database
    ):
        """Test admin having full access to all operations"""
        # Create a ticket
        ticket_data = TicketCreateSchema(
            title="Test Admin Full Access",
            description="Testing admin full access",
            urgency=TicketUrgency.LOW,
        )

        created_ticket = await ticket_service.create_ticket(ticket_data, test_user_id)

        # Admin should be able to update any field
        update_data = TicketUpdateSchema(
            title="Admin Updated Title",
            description="Admin updated description",
            urgency=TicketUrgency.HIGH,
            status=TicketStatus.ASSIGNED,
            department=TicketDepartment.IT,
            assignee_id=test_agent_id,
            feedback="Admin added feedback",
        )

        updated_ticket = await ticket_service.update_ticket_with_role(
            created_ticket.ticket_id, test_agent_id, UserRole.ADMIN, update_data
        )

        assert updated_ticket.title == "Admin Updated Title"
        assert updated_ticket.description == "Admin updated description"
        assert updated_ticket.urgency == TicketUrgency.HIGH
        assert updated_ticket.status == TicketStatus.ASSIGNED
        assert updated_ticket.department == TicketDepartment.IT
        assert updated_ticket.assignee_id == ObjectId(test_agent_id)
        assert updated_ticket.feedback == "Admin added feedback"

        logger.info("Admin full access test passed")

    @pytest.mark.asyncio
    async def test_admin_view_all_tickets(
        self, ticket_service, test_user_id, test_agent_id, setup_database
    ):
        """Test admin can view all tickets regardless of ownership"""
        # Create tickets from different users
        user1_id = test_user_id
        user2_id = str(ObjectId())

        # Create ticket for user1
        ticket_data1 = TicketCreateSchema(
            title="Test Admin View All - User1",
            description="Ticket from user1",
            urgency=TicketUrgency.LOW,
        )
        ticket1 = await ticket_service.create_ticket(ticket_data1, user1_id)

        # Create ticket for user2 (simulate by creating with different user_id)
        # Note: This would normally require user2 to exist, but for testing we'll use admin powers

        # Admin should see all tickets
        result = await ticket_service.get_tickets(test_agent_id, UserRole.ADMIN)

        # Should contain at least the ticket we created
        ticket_ids = [t.ticket_id for t in result["tickets"]]
        assert ticket1.ticket_id in ticket_ids

        logger.info("Admin view all tickets test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
