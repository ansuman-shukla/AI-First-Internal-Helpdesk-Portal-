#!/usr/bin/env python3
"""
Test script to verify content flagging flow works correctly.

This script tests the new HSA flow where harmful content prevents ticket creation
and returns detailed error information for the frontend to handle.
"""

import os
import sys
import asyncio
import logging

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ticket_service import TicketService
from app.schemas.ticket import TicketCreateSchema, TicketUrgency

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_content_flagging():
    """Test the content flagging flow"""
    
    print("=" * 60)
    print("CONTENT FLAGGING FLOW TEST")
    print("=" * 60)
    
    ticket_service = TicketService()
    
    # Test cases: (title, description, expected_to_be_flagged)
    test_cases = [
        # Should be flagged
        ("fuck", "this is fucking bullshit", True),
        ("Buy now!", "Click here for free money! Limited time offer!", True),
        ("Dating help", "Can you help me with my Tinder profile?", True),
        
        # Should be safe
        ("Printer issue", "My printer is not working properly", False),
        ("Password reset", "I forgot my password and need help", False),
    ]
    
    print(f"Testing {len(test_cases)} cases...\n")
    
    for i, (title, description, should_be_flagged) in enumerate(test_cases, 1):
        print(f"Test {i}: {title}")
        print(f"Description: {description}")
        print(f"Expected: {'FLAGGED' if should_be_flagged else 'SAFE'}")
        
        try:
            # Create ticket data
            ticket_data = TicketCreateSchema(
                title=title,
                description=description,
                urgency=TicketUrgency.MEDIUM
            )
            
            # Try to create ticket
            result = await ticket_service.create_ticket(ticket_data, "test_user_id")
            
            # If we get here, ticket was created (not flagged)
            print(f"Result: TICKET CREATED (not flagged)")
            print(f"Ticket ID: {result.ticket_id}")
            print(f"Status: {result.status}")
            print(f"Department: {result.department}")
            print(f"Misuse Flag: {result.misuse_flag}")
            
            if should_be_flagged:
                print("❌ ERROR: Content should have been flagged but wasn't!")
            else:
                print("✅ CORRECT: Content was safe and ticket was created")
                
        except ValueError as e:
            error_message = str(e)
            print(f"Result: CONTENT FLAGGED")
            print(f"Error: {error_message}")
            
            if error_message.startswith("CONTENT_FLAGGED:"):
                # Parse the error message
                parts = error_message.split(":", 2)
                if len(parts) == 3:
                    content_type = parts[1]
                    user_message = parts[2]
                    print(f"Content Type: {content_type}")
                    print(f"User Message: {user_message}")
                    
                    if should_be_flagged:
                        print("✅ CORRECT: Content was flagged as expected")
                    else:
                        print("❌ ERROR: Content should have been safe but was flagged!")
                else:
                    print("❌ ERROR: Invalid error message format")
            else:
                print(f"❌ ERROR: Unexpected error format: {error_message}")
                
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("-" * 40)
    
    print("\nTEST COMPLETE!")

async def test_detailed_hsa():
    """Test the detailed HSA function directly"""
    
    print("=" * 60)
    print("DETAILED HSA FUNCTION TEST")
    print("=" * 60)
    
    from app.services.ai.hsa import check_harmful_detailed
    
    test_cases = [
        ("fuck", "this is fucking bullshit"),
        ("Buy now!", "Click here for free money!"),
        ("Printer issue", "My printer is not working"),
    ]
    
    for title, description in test_cases:
        print(f"\nTesting: '{title}' - '{description}'")
        try:
            result = check_harmful_detailed(title, description)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Content Flagging Test Script")
    print("This script tests the new HSA flow that prevents ticket creation for harmful content.")
    print()
    
    # Check environment
    api_key = os.getenv("GOOGLE_API_KEY")
    hsa_enabled = os.getenv("HSA_ENABLED", "false").lower() == "true"
    
    print(f"GOOGLE_API_KEY configured: {bool(api_key)}")
    print(f"HSA_ENABLED: {hsa_enabled}")
    print()
    
    # Run tests
    asyncio.run(test_detailed_hsa())
    print()
    asyncio.run(test_content_flagging())
