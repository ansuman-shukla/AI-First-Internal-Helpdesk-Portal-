#!/usr/bin/env python3
"""
Debug script to check HSA configuration and test the function directly.
"""

import os
import sys
import logging

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_environment():
    """Check if environment variables are properly configured"""
    print("=" * 60)
    print("ENVIRONMENT CONFIGURATION CHECK")
    print("=" * 60)
    
    # Check critical environment variables
    env_vars = [
        'GOOGLE_API_KEY',
        'HSA_ENABLED',
        'HSA_CONFIDENCE_THRESHOLD',
        'GEMINI_MODEL',
        'GEMINI_TEMPERATURE',
        'GEMINI_MAX_TOKENS'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var == 'GOOGLE_API_KEY':
                print(f"✅ {var}: {'*' * 20}...{value[-4:]} (length: {len(value)})")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
    
    print()

def check_ai_config():
    """Check if AI configuration module loads correctly"""
    print("=" * 60)
    print("AI CONFIGURATION MODULE CHECK")
    print("=" * 60)
    
    try:
        from app.core.ai_config import ai_config
        
        print("✅ AI config module loaded successfully")
        print(f"HSA_ENABLED: {ai_config.HSA_ENABLED}")
        print(f"GOOGLE_API_KEY configured: {bool(ai_config.GOOGLE_API_KEY)}")
        print(f"HSA_CONFIDENCE_THRESHOLD: {ai_config.HSA_CONFIDENCE_THRESHOLD}")
        print(f"GEMINI_MODEL: {ai_config.GEMINI_MODEL}")
        
        # Validate configuration
        validation = ai_config.validate_config()
        print(f"Configuration valid: {validation['valid']}")
        if validation['errors']:
            print(f"Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"Warnings: {validation['warnings']}")
            
    except Exception as e:
        print(f"❌ Error loading AI config: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()

def test_hsa_function():
    """Test the HSA function directly"""
    print("=" * 60)
    print("HSA FUNCTION DIRECT TEST")
    print("=" * 60)
    
    try:
        from app.services.ai.hsa import check_harmful
        
        # Test with explicit harmful content
        test_cases = [
            ("fuck", "this is fucking bullshit"),
            ("Buy now!", "Click here for free money!"),
            ("Normal ticket", "My printer is not working")
        ]
        
        for title, description in test_cases:
            print(f"\nTesting: '{title}' - '{description}'")
            try:
                result = check_harmful(title, description)
                print(f"Result: {'HARMFUL' if result else 'SAFE'}")
            except Exception as e:
                print(f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Error importing HSA function: {str(e)}")
        import traceback
        traceback.print_exc()

def test_ticket_creation():
    """Test ticket creation process"""
    print("=" * 60)
    print("TICKET CREATION PROCESS TEST")
    print("=" * 60)
    
    try:
        from app.services.ticket_service import TicketService
        from app.schemas.ticket import TicketCreateSchema, TicketUrgency
        
        # Create a test ticket with explicit content
        ticket_service = TicketService()
        ticket_data = TicketCreateSchema(
            title="fuck",
            description="this is fucking bullshit",
            urgency=TicketUrgency.MEDIUM
        )
        
        print("Testing ticket creation with explicit content...")
        print(f"Title: {ticket_data.title}")
        print(f"Description: {ticket_data.description}")
        
        # This would normally create a ticket, but we'll just test the HSA part
        from app.services.ai.hsa import check_harmful
        is_harmful = check_harmful(ticket_data.title, ticket_data.description)
        print(f"HSA Result: {'HARMFUL' if is_harmful else 'SAFE'}")
        
        if is_harmful:
            print("✅ HSA correctly detected harmful content")
        else:
            print("❌ HSA failed to detect harmful content")
            
    except Exception as e:
        print(f"❌ Error testing ticket creation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("HSA Debug Script")
    print("This script will help diagnose why HSA filtering is not working.")
    print()
    
    # Run all checks
    check_environment()
    check_ai_config()
    test_hsa_function()
    test_ticket_creation()
    
    print("=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)
    print("If HSA is not working:")
    print("1. Make sure GOOGLE_API_KEY is set in .env file")
    print("2. Make sure HSA_ENABLED=true in .env file")
    print("3. Check the logs above for any errors")
    print("4. Try restarting the backend server after changing .env")
