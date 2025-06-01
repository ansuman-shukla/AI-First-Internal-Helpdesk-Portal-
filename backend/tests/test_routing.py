#!/usr/bin/env python3
"""
Test script for AI routing function
Tests the real LLM routing implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ai.routing import assign_department

def test_routing_function():
    """Test the AI routing function with various ticket scenarios"""
    print("Testing AI Routing Function with Real LLM...")
    print("=" * 50)
    
    test_cases = [
        {
            "title": "Computer won't start",
            "description": "My laptop is not turning on and the power button doesn't work. I tried charging it but no lights come on.",
            "expected": "IT"
        },
        {
            "title": "Password reset needed",
            "description": "I forgot my password and can't log into my email account. Need help resetting it.",
            "expected": "IT"
        },
        {
            "title": "Vacation request",
            "description": "I need to request vacation time for next month. What's the process for submitting leave requests?",
            "expected": "HR"
        },
        {
            "title": "Benefits question",
            "description": "I want to know about health insurance options and 401k enrollment. When is open enrollment?",
            "expected": "HR"
        },
        {
            "title": "Software installation",
            "description": "I need to install Adobe Photoshop for my design work. How do I request software installation?",
            "expected": "IT"
        },
        {
            "title": "Performance review",
            "description": "My annual performance review is coming up. What should I prepare and when is it due?",
            "expected": "HR"
        },
        {
            "title": "Network connectivity issue",
            "description": "I can't connect to the company WiFi and VPN is not working from home.",
            "expected": "IT"
        },
        {
            "title": "Payroll question",
            "description": "There's an issue with my last paycheck. Some deductions don't look right.",
            "expected": "HR"
        }
    ]
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['title']}")
        print(f"Description: {test_case['description']}")
        print(f"Expected: {test_case['expected']}")
        
        try:
            result = assign_department(test_case['title'], test_case['description'])
            print(f"Predicted: {result}")
            
            if result == test_case['expected']:
                print("✓ CORRECT")
                correct_predictions += 1
            else:
                print("✗ INCORRECT")
                
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"Routing Test Results:")
    print(f"Correct predictions: {correct_predictions}/{total_tests}")
    print(f"Accuracy: {(correct_predictions/total_tests)*100:.1f}%")
    
    if correct_predictions == total_tests:
        print("🎉 Perfect routing accuracy!")
    elif correct_predictions >= total_tests * 0.8:
        print("✅ Good routing accuracy!")
    else:
        print("⚠️ Routing accuracy could be improved")

if __name__ == "__main__":
    test_routing_function()
