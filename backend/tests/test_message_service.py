"""
Tests for Message Service

This module contains comprehensive tests for message database operations
in the helpdesk system's real-time chat functionality.
"""

import pytest
from datetime import datetime
from bson import ObjectId

from app.services.message_service import MessageService, message_service
from app.schemas.message import MessageRole, MessageType, MessageFeedback
from app.core.database import get_database


@pytest.fixture
async def test_message_service():
    """Create a test message service instance"""
    return MessageService()


@pytest.fixture
async def test_ticket_id():
    """Create a test ticket ID"""
    return str(ObjectId())


@pytest.fixture
async def test_user_id():
    """Create a test user ID"""
    return str(ObjectId())


@pytest.fixture
async def cleanup_messages():
    """Clean up test messages after each test"""
    yield
    # Clean up any test messages
    db = get_database()
    if db:
        await db.messages.delete_many({"content": {"$regex": "^Test message"}})


@pytest.mark.asyncio
async def test_save_message_success(test_message_service, test_ticket_id, test_user_id, cleanup_messages):
    """Test successful message saving"""
    content = "Test message content"
    
    message = await test_message_service.save_message(
        ticket_id=test_ticket_id,
        sender_id=test_user_id,
        sender_role=MessageRole.USER,
        content=content,
        message_type=MessageType.USER_MESSAGE,
        isAI=False,
        feedback=MessageFeedback.NONE
    )
    
    assert message is not None
    assert message._id is not None
    assert str(message.ticket_id) == test_ticket_id
    assert str(message.sender_id) == test_user_id
    assert message.sender_role == MessageRole.USER
    assert message.content == content
    assert message.message_type == MessageType.USER_MESSAGE
    assert message.isAI is False
    assert message.feedback == MessageFeedback.NONE
    assert isinstance(message.timestamp, datetime)


@pytest.mark.asyncio
async def test_save_ai_message(test_message_service, test_ticket_id, test_user_id, cleanup_messages):
    """Test saving AI-generated message"""
    content = "Test AI response message"
    
    message = await test_message_service.save_message(
        ticket_id=test_ticket_id,
        sender_id=test_user_id,
        sender_role=MessageRole.IT_AGENT,
        content=content,
        message_type=MessageType.AGENT_MESSAGE,
        isAI=True,
        feedback=MessageFeedback.UP
    )
    
    assert message.isAI is True
    assert message.message_type == MessageType.AGENT_MESSAGE
    assert message.feedback == MessageFeedback.UP
    assert message.sender_role == MessageRole.IT_AGENT


@pytest.mark.asyncio
async def test_save_message_invalid_ids(test_message_service):
    """Test saving message with invalid IDs"""
    with pytest.raises(Exception):
        await test_message_service.save_message(
            ticket_id="invalid_id",
            sender_id="invalid_id",
            sender_role=MessageRole.USER,
            content="Test content"
        )


@pytest.mark.asyncio
async def test_save_message_empty_content(test_message_service, test_ticket_id, test_user_id):
    """Test saving message with empty content"""
    with pytest.raises(ValueError, match="Content cannot be empty"):
        await test_message_service.save_message(
            ticket_id=test_ticket_id,
            sender_id=test_user_id,
            sender_role=MessageRole.USER,
            content=""
        )


@pytest.mark.asyncio
async def test_save_message_long_content(test_message_service, test_ticket_id, test_user_id):
    """Test saving message with content exceeding limit"""
    long_content = "x" * 1001  # Exceeds 1000 character limit
    
    with pytest.raises(ValueError, match="Content cannot exceed 1000 characters"):
        await test_message_service.save_message(
            ticket_id=test_ticket_id,
            sender_id=test_user_id,
            sender_role=MessageRole.USER,
            content=long_content
        )


@pytest.mark.asyncio
async def test_get_ticket_messages(test_message_service, test_ticket_id, test_user_id, cleanup_messages):
    """Test retrieving messages for a ticket"""
    # Save multiple messages
    messages_data = [
        ("Test message 1", MessageType.USER_MESSAGE),
        ("Test message 2", MessageType.AGENT_MESSAGE),
        ("Test message 3", MessageType.SYSTEM_MESSAGE)
    ]
    
    saved_messages = []
    for content, msg_type in messages_data:
        message = await test_message_service.save_message(
            ticket_id=test_ticket_id,
            sender_id=test_user_id,
            sender_role=MessageRole.USER,
            content=content,
            message_type=msg_type
        )
        saved_messages.append(message)
    
    # Retrieve messages
    retrieved_messages = await test_message_service.get_ticket_messages(test_ticket_id)
    
    assert len(retrieved_messages) == 3
    assert all(str(msg.ticket_id) == test_ticket_id for msg in retrieved_messages)
    
    # Check order (should be ascending by timestamp)
    timestamps = [msg.timestamp for msg in retrieved_messages]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_get_ticket_messages_with_pagination(test_message_service, test_ticket_id, test_user_id, cleanup_messages):
    """Test retrieving messages with pagination"""
    # Save 5 messages
    for i in range(5):
        await test_message_service.save_message(
            ticket_id=test_ticket_id,
            sender_id=test_user_id,
            sender_role=MessageRole.USER,
            content=f"Test message {i+1}"
        )
    
    # Test pagination
    first_page = await test_message_service.get_ticket_messages(
        test_ticket_id, limit=2, skip=0
    )
    second_page = await test_message_service.get_ticket_messages(
        test_ticket_id, limit=2, skip=2
    )
    
    assert len(first_page) == 2
    assert len(second_page) == 2
    assert first_page[0].content != second_page[0].content


@pytest.mark.asyncio
async def test_get_message_by_id(test_message_service, test_ticket_id, test_user_id, cleanup_messages):
    """Test retrieving a specific message by ID"""
    content = "Test message for ID retrieval"
    
    saved_message = await test_message_service.save_message(
        ticket_id=test_ticket_id,
        sender_id=test_user_id,
        sender_role=MessageRole.USER,
        content=content
    )
    
    retrieved_message = await test_message_service.get_message_by_id(str(saved_message._id))
    
    assert retrieved_message is not None
    assert retrieved_message._id == saved_message._id
    assert retrieved_message.content == content


@pytest.mark.asyncio
async def test_get_message_by_id_not_found(test_message_service):
    """Test retrieving non-existent message"""
    fake_id = str(ObjectId())
    
    message = await test_message_service.get_message_by_id(fake_id)
    
    assert message is None


@pytest.mark.asyncio
async def test_update_message_feedback(test_message_service, test_ticket_id, test_user_id, cleanup_messages):
    """Test updating message feedback"""
    saved_message = await test_message_service.save_message(
        ticket_id=test_ticket_id,
        sender_id=test_user_id,
        sender_role=MessageRole.USER,
        content="Test message for feedback update"
    )
    
    # Update feedback
    success = await test_message_service.update_message_feedback(
        str(saved_message._id), MessageFeedback.UP
    )
    
    assert success is True
    
    # Verify update
    updated_message = await test_message_service.get_message_by_id(str(saved_message._id))
    assert updated_message.feedback == MessageFeedback.UP


@pytest.mark.asyncio
async def test_update_message_feedback_not_found(test_message_service):
    """Test updating feedback for non-existent message"""
    fake_id = str(ObjectId())
    
    success = await test_message_service.update_message_feedback(fake_id, MessageFeedback.UP)
    
    assert success is False


@pytest.mark.asyncio
async def test_get_message_count_for_ticket(test_message_service, test_ticket_id, test_user_id, cleanup_messages):
    """Test counting messages for a ticket"""
    # Initially no messages
    count = await test_message_service.get_message_count_for_ticket(test_ticket_id)
    assert count == 0
    
    # Add messages
    for i in range(3):
        await test_message_service.save_message(
            ticket_id=test_ticket_id,
            sender_id=test_user_id,
            sender_role=MessageRole.USER,
            content=f"Test message {i+1}"
        )
    
    count = await test_message_service.get_message_count_for_ticket(test_ticket_id)
    assert count == 3


@pytest.mark.asyncio
async def test_delete_messages_for_ticket(test_message_service, test_ticket_id, test_user_id, cleanup_messages):
    """Test deleting all messages for a ticket"""
    # Add messages
    for i in range(3):
        await test_message_service.save_message(
            ticket_id=test_ticket_id,
            sender_id=test_user_id,
            sender_role=MessageRole.USER,
            content=f"Test message {i+1}"
        )
    
    # Delete messages
    deleted_count = await test_message_service.delete_messages_for_ticket(test_ticket_id)
    assert deleted_count == 3
    
    # Verify deletion
    remaining_messages = await test_message_service.get_ticket_messages(test_ticket_id)
    assert len(remaining_messages) == 0


@pytest.mark.asyncio
async def test_global_message_service_instance():
    """Test that global message service instance is available"""
    assert message_service is not None
    assert isinstance(message_service, MessageService)
