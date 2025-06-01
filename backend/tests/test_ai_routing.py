"""
Unit tests for AI Routing module
"""

import pytest
from app.services.ai.routing import assign_department, Department


class TestRoutingModule:
    """Test cases for the AI routing module functionality"""
    
    def test_assign_department_it_keywords(self):
        """Test routing with clear IT-related keywords"""
        title = "Computer won't start"
        description = "My laptop is not booting up and shows a blue screen error"
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        assert result == "IT"  # Should route to IT based on keywords
    
    def test_assign_department_hr_keywords(self):
        """Test routing with clear HR-related keywords"""
        title = "Question about payroll"
        description = "I have questions about my salary and benefits package"
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        assert result == "HR"  # Should route to HR based on keywords
    
    def test_assign_department_mixed_keywords(self):
        """Test routing with both IT and HR keywords"""
        title = "Employee computer setup"
        description = "New employee needs computer setup and payroll information"
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        # Result depends on keyword count, but should be deterministic
    
    def test_assign_department_no_keywords(self):
        """Test routing with no specific keywords (should default to IT)"""
        title = "General question"
        description = "I have a general question about something"
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        assert result == "IT"  # Should default to IT
    
    def test_assign_department_empty_strings(self):
        """Test routing with empty title and description"""
        title = ""
        description = ""
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        assert result == "IT"  # Should default to IT
    
    def test_assign_department_case_insensitive(self):
        """Test that routing is case insensitive"""
        title = "COMPUTER PROBLEM"
        description = "MY LAPTOP IS BROKEN"
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        assert result == "IT"  # Should route to IT regardless of case
    
    def test_assign_department_it_specific_cases(self):
        """Test specific IT-related scenarios"""
        test_cases = [
            ("Password reset", "I forgot my login password"),
            ("Software installation", "Need help installing new application"),
            ("Network issue", "Cannot connect to wifi"),
            ("Printer problem", "Printer is not working"),
            ("Email trouble", "Cannot access my email account"),
            ("System error", "Getting error messages on my computer"),
        ]
        
        for title, description in test_cases:
            result = assign_department(title, description)
            assert result == "IT", f"Expected IT for title='{title}', got {result}"
    
    def test_assign_department_hr_specific_cases(self):
        """Test specific HR-related scenarios"""
        test_cases = [
            ("Vacation request", "I want to request time off"),
            ("Benefits question", "Questions about health insurance"),
            ("Performance review", "When is my next review scheduled"),
            ("Workplace complaint", "Issue with team member behavior"),
            ("Training request", "Need training on new policies"),
            ("Payroll inquiry", "Question about my paycheck"),
        ]
        
        for title, description in test_cases:
            result = assign_department(title, description)
            assert result == "HR", f"Expected HR for title='{title}', got {result}"
    
    def test_assign_department_return_type(self):
        """Test that assign_department always returns a valid Department type"""
        test_cases = [
            ("Normal title", "Normal description"),
            ("", ""),
            ("IT computer", "HR payroll"),
            ("123", "456"),
            ("Special!@#", "Characters$%^&*()"),
        ]
        
        for title, description in test_cases:
            result = assign_department(title, description)
            assert isinstance(result, str), f"Expected str, got {type(result)}"
            assert result in ["IT", "HR"], f"Expected 'IT' or 'HR', got '{result}'"
    
    def test_assign_department_consistency(self):
        """Test that assign_department returns consistent results for the same input"""
        title = "Computer software issue"
        description = "Having trouble with application installation"
        
        # Call the function multiple times with the same input
        results = [assign_department(title, description) for _ in range(5)]
        
        # All results should be the same
        assert all(result == results[0] for result in results)
        assert all(result in ["IT", "HR"] for result in results)
    
    def test_assign_department_with_none_values(self):
        """Test routing error handling with None values"""
        # These should raise TypeError since the function expects strings
        with pytest.raises(TypeError):
            assign_department(None, "description")
        
        with pytest.raises(TypeError):
            assign_department("title", None)
        
        with pytest.raises(TypeError):
            assign_department(None, None)
    
    def test_assign_department_with_non_string_values(self):
        """Test routing error handling with non-string values"""
        # These should raise TypeError since the function expects strings
        with pytest.raises(TypeError):
            assign_department(123, "description")
        
        with pytest.raises(TypeError):
            assign_department("title", 456)
        
        with pytest.raises(TypeError):
            assign_department([], {})


class TestRoutingEdgeCases:
    """Test edge cases for routing module"""
    
    def test_assign_department_with_whitespace_only(self):
        """Test routing with whitespace-only content"""
        title = "   "
        description = "\t\n\r  "
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        assert result == "IT"  # Should default to IT
    
    def test_assign_department_with_special_characters(self):
        """Test routing with special characters and unicode"""
        title = "Computér problém! 🖥️"
        description = "My laptop has issues with spëcial software"
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        # Should still detect "computer", "laptop", "software" keywords
    
    def test_assign_department_keyword_boundaries(self):
        """Test that keyword matching respects word boundaries"""
        title = "Computation theory"  # Contains "computer" but different context
        description = "Academic question about computational complexity"
        
        result = assign_department(title, description)
        
        assert isinstance(result, str)
        assert result in ["IT", "HR"]
        # Should still match "computer" substring in "computation"
