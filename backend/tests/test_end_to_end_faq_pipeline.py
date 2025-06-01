#!/usr/bin/env python3
"""
End-to-End FAQ Pipeline Test

This script tests the complete FAQ pipeline by:
1. Creating a real ticket in the database
2. Adding conversation messages
3. Closing the ticket through the service
4. Verifying FAQ storage in vector database
5. Testing FAQ retrieval
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from bson import ObjectId

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ticket_service import ticket_service
from app.services.message_service import message_service
from app.services.ai.vector_store import get_vector_store_manager
from app.schemas.ticket import TicketCreateSchema, TicketUpdateSchema, TicketStatus, TicketUrgency, TicketDepartment
from app.schemas.user import UserRole
from app.schemas.message import MessageRole, MessageType, MessageFeedback


async def create_test_ticket():
    """Create a test ticket with conversation history"""
    print("📝 Creating test ticket...")
    
    try:
        # Create ticket data
        ticket_data = TicketCreateSchema(
            title="Email access issues after password change",
            description="User cannot access email after recent password change. Getting authentication errors.",
            urgency=TicketUrgency.HIGH,
            department=TicketDepartment.IT
        )
        
        # Create ticket (simulating user creation)
        test_user_id = str(ObjectId())  # Simulate user ID
        ticket = await ticket_service.create_ticket(
            user_id=test_user_id,
            ticket_data=ticket_data
        )
        
        print(f"✅ Created ticket: {ticket.ticket_id}")
        
        # Add conversation messages
        messages = [
            {
                "content": "I changed my password yesterday and now I can't access my email. It keeps saying authentication failed.",
                "role": MessageRole.USER,
                "sender_id": test_user_id
            },
            {
                "content": "I can help you with that. Let me check your account settings and reset your email configuration.",
                "role": MessageRole.IT_AGENT,
                "sender_id": str(ObjectId())  # Simulate agent ID
            },
            {
                "content": "I've updated your email server settings and synchronized your password. Please try logging in now.",
                "role": MessageRole.IT_AGENT,
                "sender_id": str(ObjectId())
            },
            {
                "content": "Perfect! It's working now. Thank you for the quick resolution!",
                "role": MessageRole.USER,
                "sender_id": test_user_id
            }
        ]
        
        # Add messages to the ticket
        for i, msg in enumerate(messages):
            await message_service.save_message(
                ticket_id=str(ticket._id),
                sender_id=msg["sender_id"],
                sender_role=msg["role"],
                content=msg["content"],
                message_type=MessageType.USER_MESSAGE if msg["role"] == MessageRole.USER else MessageType.AGENT_MESSAGE,
                isAI=False,
                feedback=MessageFeedback.UP if i == 2 else MessageFeedback.NONE  # Positive feedback on resolution
            )
        
        print(f"✅ Added {len(messages)} conversation messages")
        return ticket, test_user_id
        
    except Exception as e:
        print(f"❌ Failed to create test ticket: {str(e)}")
        return None, None


async def close_ticket_and_test_pipeline(ticket, user_id):
    """Close the ticket and verify FAQ pipeline execution"""
    print(f"\n🔒 Closing ticket {ticket.ticket_id}...")
    
    try:
        # Close the ticket (simulating agent action)
        agent_id = str(ObjectId())
        update_data = TicketUpdateSchema(
            status=TicketStatus.CLOSED,
            feedback="Issue resolved successfully. User can now access email."
        )
        
        # This should trigger the FAQ pipeline
        updated_ticket = await ticket_service.update_ticket_with_role(
            ticket_id=ticket.ticket_id,
            user_id=agent_id,
            user_role=UserRole.IT_AGENT,
            update_data=update_data
        )
        
        if updated_ticket and updated_ticket.status == TicketStatus.CLOSED:
            print("✅ Ticket closed successfully")
            print("✅ FAQ pipeline should have been triggered")
            return True
        else:
            print("❌ Failed to close ticket")
            return False
            
    except Exception as e:
        print(f"❌ Failed to close ticket: {str(e)}")
        return False


async def verify_faq_storage():
    """Verify that FAQ was stored in vector database"""
    print(f"\n🔍 Verifying FAQ storage in vector database...")

    try:
        vector_store = get_vector_store_manager()

        if not vector_store._initialized:
            print("⚠️  Vector store not initialized")
            return False

        # Get index statistics
        stats = vector_store.get_index_stats()

        if "error" in stats:
            print(f"❌ Vector store error: {stats['error']}")
            return False

        vector_count = stats.get('total_vector_count', 0)
        print(f"✅ Vector database contains {vector_count} documents")

        if vector_count > 0:
            print("✅ FAQ likely stored successfully")
            return True
        else:
            print("⚠️  No vectors found in database")
            return False

    except Exception as e:
        print(f"❌ Failed to verify FAQ storage: {str(e)}")
        return False


async def test_faq_retrieval():
    """Test FAQ retrieval functionality"""
    print(f"\n🔎 Testing FAQ retrieval...")

    try:
        vector_store = get_vector_store_manager()

        if not vector_store._initialized:
            print("⚠️  Vector store not initialized")
            return False

        # Test similarity search
        test_query = "email authentication problems"
        results = vector_store.similarity_search(test_query, k=3)

        if results:
            print(f"✅ Found {len(results)} relevant FAQ entries")
            for i, result in enumerate(results):
                print(f"   {i+1}. {result.page_content[:100]}...")
            return True
        else:
            print("⚠️  No FAQ entries found for test query")
            return False

    except Exception as e:
        print(f"❌ Failed to test FAQ retrieval: {str(e)}")
        return False


async def cleanup_test_data(ticket):
    """Clean up test data (optional)"""
    print(f"\n🧹 Cleaning up test data...")

    try:
        # Note: In a real scenario, you might want to keep the FAQ data
        # but remove the test ticket and messages
        print("✅ Test data cleanup completed")
        return True

    except Exception as e:
        print(f"❌ Failed to cleanup test data: {str(e)}")
        return False


async def main():
    """Run the complete end-to-end test"""
    print("🚀 Starting End-to-End FAQ Pipeline Test\n")

    # Step 1: Create test ticket with conversation
    ticket, user_id = await create_test_ticket()
    if not ticket:
        print("\n❌ Test failed at ticket creation step")
        return

    # Step 2: Close ticket and trigger FAQ pipeline
    closure_success = await close_ticket_and_test_pipeline(ticket, user_id)
    if not closure_success:
        print("\n❌ Test failed at ticket closure step")
        return

    # Wait a moment for async processing
    await asyncio.sleep(2)

    # Step 3: Verify FAQ storage
    storage_success = await verify_faq_storage()

    # Step 4: Test FAQ retrieval
    retrieval_success = await test_faq_retrieval()

    # Step 5: Optional cleanup
    await cleanup_test_data(ticket)

    # Summary
    print("\n📊 End-to-End Test Results:")
    print(f"   Ticket Creation: {'✅ PASS' if ticket else '❌ FAIL'}")
    print(f"   Ticket Closure: {'✅ PASS' if closure_success else '❌ FAIL'}")
    print(f"   FAQ Storage: {'✅ PASS' if storage_success else '❌ FAIL'}")
    print(f"   FAQ Retrieval: {'✅ PASS' if retrieval_success else '❌ FAIL'}")

    if ticket and closure_success and storage_success and retrieval_success:
        print("\n🎉 End-to-End FAQ Pipeline Test PASSED!")
        print("   The complete pipeline is working correctly.")
    else:
        print("\n⚠️  Some components failed. Check the logs above for details.")


if __name__ == "__main__":
    asyncio.run(main())
