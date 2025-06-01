import pytest
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import ValidationError
from app.schemas.ticket import (
    TicketCreateSchema,
    TicketUpdateSchema,
    TicketSchema,
    TicketUrgency,
    TicketStatus,
    TicketDepartment
)
from app.models.ticket import TicketModel


class TestTicketEnums:
    """Test ticket enum values"""
    
    def test_ticket_urgency_values(self):
        """Test TicketUrgency enum values"""
        assert TicketUrgency.LOW == "low"
        assert TicketUrgency.MEDIUM == "medium"
        assert TicketUrgency.HIGH == "high"
    
    def test_ticket_status_values(self):
        """Test TicketStatus enum values"""
        assert TicketStatus.OPEN == "open"
        assert TicketStatus.ASSIGNED == "assigned"
        assert TicketStatus.RESOLVED == "resolved"
        assert TicketStatus.CLOSED == "closed"
    
    def test_ticket_department_values(self):
        """Test TicketDepartment enum values"""
        assert TicketDepartment.IT == "IT"
        assert TicketDepartment.HR == "HR"


class TestTicketCreateSchema:
    """Test TicketCreateSchema validation"""
    
    def test_valid_ticket_creation(self):
        """Test creating a valid ticket"""
        ticket_data = {
            "title": "Test Ticket",
            "description": "This is a test ticket description",
            "urgency": TicketUrgency.HIGH
        }
        ticket = TicketCreateSchema(**ticket_data)
        assert ticket.title == "Test Ticket"
        assert ticket.description == "This is a test ticket description"
        assert ticket.urgency == TicketUrgency.HIGH
    
    def test_default_urgency(self):
        """Test default urgency is MEDIUM"""
        ticket_data = {
            "title": "Test Ticket",
            "description": "This is a test ticket description"
        }
        ticket = TicketCreateSchema(**ticket_data)
        assert ticket.urgency == TicketUrgency.MEDIUM
    
    def test_required_fields(self):
        """Test that title and description are required"""
        # Missing title
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(description="Test description")
        assert "title" in str(exc_info.value)
        
        # Missing description
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(title="Test title")
        assert "description" in str(exc_info.value)
    
    def test_title_length_validation(self):
        """Test title length constraints"""
        # Title too long (over 200 chars)
        long_title = "x" * 201
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(title=long_title, description="Test description")
        assert "String should have at most 200 characters" in str(exc_info.value)
        
        # Empty title
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(title="", description="Test description")
        assert "String should have at least 1 character" in str(exc_info.value)
        
        # Whitespace only title
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(title="   ", description="Test description")
        assert "Title cannot be empty" in str(exc_info.value)
    
    def test_description_length_validation(self):
        """Test description length constraints"""
        # Description too long (over 2000 chars)
        long_description = "x" * 2001
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(title="Test title", description=long_description)
        assert "String should have at most 2000 characters" in str(exc_info.value)
        
        # Empty description
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(title="Test title", description="")
        assert "String should have at least 1 character" in str(exc_info.value)
        
        # Whitespace only description
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(title="Test title", description="   ")
        assert "Description cannot be empty" in str(exc_info.value)
    
    def test_title_description_trimming(self):
        """Test that title and description are trimmed"""
        ticket = TicketCreateSchema(
            title="  Test Title  ",
            description="  Test Description  "
        )
        assert ticket.title == "Test Title"
        assert ticket.description == "Test Description"
    
    def test_invalid_urgency(self):
        """Test invalid urgency value"""
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateSchema(
                title="Test title",
                description="Test description",
                urgency="invalid"
            )
        assert "Input should be 'low', 'medium' or 'high'" in str(exc_info.value)


class TestTicketUpdateSchema:
    """Test TicketUpdateSchema validation"""
    
    def test_all_fields_optional(self):
        """Test that all fields are optional in update schema"""
        ticket = TicketUpdateSchema()
        assert ticket.title is None
        assert ticket.description is None
        assert ticket.urgency is None
        assert ticket.status is None
        assert ticket.department is None
        assert ticket.assignee_id is None
        assert ticket.feedback is None
    
    def test_partial_update(self):
        """Test partial update with some fields"""
        ticket = TicketUpdateSchema(
            title="Updated Title",
            status=TicketStatus.RESOLVED
        )
        assert ticket.title == "Updated Title"
        assert ticket.status == TicketStatus.RESOLVED
        assert ticket.description is None
    
    def test_update_validation_rules(self):
        """Test that validation rules apply to update schema"""
        # Title too long
        with pytest.raises(ValidationError):
            TicketUpdateSchema(title="x" * 201)
        
        # Empty title
        with pytest.raises(ValidationError):
            TicketUpdateSchema(title="")
        
        # Invalid status
        with pytest.raises(ValidationError):
            TicketUpdateSchema(status="invalid_status")


class TestTicketSchema:
    """Test TicketSchema (response schema)"""
    
    def test_complete_ticket_schema(self):
        """Test complete ticket schema with all fields"""
        now = datetime.now(timezone.utc)
        ticket_data = {
            "id": str(ObjectId()),
            "ticket_id": "TKT-1234567890-ABC123",
            "title": "Test Ticket",
            "description": "Test Description",
            "urgency": TicketUrgency.HIGH,
            "status": TicketStatus.OPEN,
            "department": TicketDepartment.IT,
            "assignee_id": str(ObjectId()),
            "user_id": str(ObjectId()),
            "created_at": now,
            "updated_at": now,
            "closed_at": None,
            "misuse_flag": False,
            "feedback": None
        }
        ticket = TicketSchema(**ticket_data)
        assert ticket.ticket_id == "TKT-1234567890-ABC123"
        assert ticket.urgency == TicketUrgency.HIGH
        assert ticket.status == TicketStatus.OPEN
        assert ticket.department == TicketDepartment.IT


class TestTicketModel:
    """Test TicketModel functionality"""
    
    def test_ticket_id_generation(self):
        """Test automatic ticket ID generation"""
        user_id = ObjectId()
        ticket = TicketModel(
            title="Test Ticket",
            description="Test Description",
            user_id=user_id
        )
        assert ticket.ticket_id.startswith("TKT-")
        assert len(ticket.ticket_id.split("-")) == 3
        assert len(ticket.ticket_id.split("-")[2]) == 6  # Random suffix length
    
    def test_ticket_id_uniqueness(self):
        """Test that generated ticket IDs are unique"""
        user_id = ObjectId()
        ticket1 = TicketModel(title="Test 1", description="Desc 1", user_id=user_id)
        ticket2 = TicketModel(title="Test 2", description="Desc 2", user_id=user_id)
        assert ticket1.ticket_id != ticket2.ticket_id
    
    def test_default_values(self):
        """Test default values in TicketModel"""
        user_id = ObjectId()
        ticket = TicketModel(
            title="Test Ticket",
            description="Test Description",
            user_id=user_id
        )
        assert ticket.urgency == TicketUrgency.MEDIUM
        assert ticket.status == TicketStatus.OPEN
        assert ticket.department is None
        assert ticket.assignee_id is None
        assert ticket.misuse_flag is False
        assert ticket.feedback is None
        assert ticket.closed_at is None
        assert isinstance(ticket.created_at, datetime)
        assert isinstance(ticket.updated_at, datetime)
    
    def test_to_dict_conversion(self):
        """Test converting TicketModel to dictionary"""
        user_id = ObjectId()
        ticket = TicketModel(
            title="Test Ticket",
            description="Test Description",
            user_id=user_id,
            urgency=TicketUrgency.HIGH,
            status=TicketStatus.ASSIGNED,
            department=TicketDepartment.IT
        )
        data = ticket.to_dict()
        
        assert data["title"] == "Test Ticket"
        assert data["description"] == "Test Description"
        assert data["urgency"] == "high"
        assert data["status"] == "assigned"
        assert data["department"] == "IT"
        assert data["user_id"] == user_id
        assert data["misuse_flag"] is False
    
    def test_from_dict_conversion(self):
        """Test creating TicketModel from dictionary"""
        user_id = ObjectId()
        data = {
            "_id": ObjectId(),
            "ticket_id": "TKT-1234567890-ABC123",
            "title": "Test Ticket",
            "description": "Test Description",
            "urgency": "high",
            "status": "assigned",
            "department": "IT",
            "user_id": user_id,
            "assignee_id": ObjectId(),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "misuse_flag": True,
            "feedback": "Great service!"
        }
        
        ticket = TicketModel.from_dict(data)
        assert ticket.ticket_id == "TKT-1234567890-ABC123"
        assert ticket.title == "Test Ticket"
        assert ticket.urgency == TicketUrgency.HIGH
        assert ticket.status == TicketStatus.ASSIGNED
        assert ticket.department == TicketDepartment.IT
        assert ticket.misuse_flag is True
        assert ticket.feedback == "Great service!"
    
    def test_status_update_methods(self):
        """Test status update helper methods"""
        user_id = ObjectId()
        agent_id = ObjectId()
        ticket = TicketModel(
            title="Test Ticket",
            description="Test Description",
            user_id=user_id
        )
        
        # Test assign_to_agent
        ticket.assign_to_agent(agent_id)
        assert ticket.assignee_id == agent_id
        assert ticket.status == TicketStatus.ASSIGNED
        
        # Test update_status to closed
        ticket.update_status(TicketStatus.CLOSED)
        assert ticket.status == TicketStatus.CLOSED
        assert ticket.closed_at is not None
        
        # Test flag_misuse
        ticket.flag_misuse(True)
        assert ticket.misuse_flag is True
        
        # Test add_feedback
        ticket.add_feedback("Excellent support!")
        assert ticket.feedback == "Excellent support!"
