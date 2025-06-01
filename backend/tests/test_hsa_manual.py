#!/usr/bin/env python3
"""
Manual test script for HSA (Harmful/Spam Analysis) function.

This script allows you to test the HSA function with various inputs
to verify it's working correctly with real LLM integration.

Usage:
    python test_hsa_manual.py
"""

import os
import sys
import logging

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai.hsa import check_harmful

# Configure logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_hsa_function():
    """Test the HSA function with various inputs"""
    
    print("=" * 60)
    print("HSA (Harmful/Spam Analysis) Manual Test")
    print("=" * 60)
    
    # Test cases: (title, description, expected_result)
    test_cases = [
        # Safe content
        ("Printer not working", "My printer is not printing documents. Can someone help me fix it?", False),
        ("Password reset", "I forgot my password and need help resetting it", False),
        ("Software installation", "Need help installing Microsoft Office on my computer", False),
        
        # Spam content
        ("Buy now!", "Limited time offer! Click here for free money! Act now!", True),
        ("Free money!", "Congratulations! You won $1000! Click here to claim your prize!", True),
        ("Work from home", "Make money fast! No experience needed! Earn $5000 per week!", True),
        
        # Inappropriate content
        ("This is bullshit", "F*** this system, it's complete shit and doesn't work", True),
        ("You're an idiot", "The IT team are morons and don't know what they're doing", True),
        
        # System misuse
        ("Dating advice", "Can you help me write a good dating profile for Tinder?", True),
        ("Movie downloads", "Where can I download the latest movies for free?", True),
    ]
    
    print(f"\nTesting {len(test_cases)} cases...\n")
    
    results = []
    for i, (title, description, expected) in enumerate(test_cases, 1):
        print(f"Test {i}: {title}")
        print(f"Description: {description}")
        print(f"Expected: {'HARMFUL' if expected else 'SAFE'}")
        
        try:
            result = check_harmful(title, description)
            status = "HARMFUL" if result else "SAFE"
            correct = result == expected
            
            print(f"Result: {status}")
            print(f"Correct: {'✅ YES' if correct else '❌ NO'}")
            
            results.append({
                'test': i,
                'title': title,
                'expected': expected,
                'result': result,
                'correct': correct
            })
            
        except Exception as e:
            print(f"Error: {str(e)}")
            results.append({
                'test': i,
                'title': title,
                'expected': expected,
                'result': None,
                'correct': False,
                'error': str(e)
            })
        
        print("-" * 40)
    
    # Summary
    print("\nSUMMARY:")
    print("=" * 60)
    
    correct_count = sum(1 for r in results if r['correct'])
    total_count = len(results)
    accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0
    
    print(f"Total tests: {total_count}")
    print(f"Correct: {correct_count}")
    print(f"Accuracy: {accuracy:.1f}%")
    
    print("\nDetailed Results:")
    for r in results:
        status = "✅" if r['correct'] else "❌"
        expected_str = "HARMFUL" if r['expected'] else "SAFE"
        result_str = "HARMFUL" if r['result'] else "SAFE" if r['result'] is not None else "ERROR"
        print(f"{status} Test {r['test']}: {r['title']} | Expected: {expected_str} | Got: {result_str}")
        if 'error' in r:
            print(f"    Error: {r['error']}")
    
    return results

def interactive_test():
    """Interactive test mode"""
    print("\n" + "=" * 60)
    print("INTERACTIVE TEST MODE")
    print("=" * 60)
    print("Enter ticket content to test HSA analysis.")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            title = input("Enter ticket title: ").strip()
            if title.lower() == 'quit':
                break
            
            description = input("Enter ticket description: ").strip()
            if description.lower() == 'quit':
                break
            
            print("\nAnalyzing...")
            result = check_harmful(title, description)
            
            print(f"Result: {'HARMFUL - Content flagged' if result else 'SAFE - Content approved'}")
            print("-" * 40)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    print("HSA Manual Test Script")
    print("Make sure you have set GOOGLE_API_KEY in your environment variables.")
    print("Set HSA_ENABLED=true to test real LLM functionality.")
    
    # Check if API key is configured
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n⚠️  WARNING: GOOGLE_API_KEY not found in environment variables.")
        print("The HSA function will use fallback mode or disabled mode.")
    else:
        print(f"\n✅ GOOGLE_API_KEY configured (length: {len(api_key)})")
    
    # Run automated tests
    test_hsa_function()
    
    # Ask if user wants interactive mode
    response = input("\nWould you like to run interactive tests? (y/n): ").strip().lower()
    if response in ['y', 'yes']:
        interactive_test()
    
    print("\nTest complete!")
