"""
Unit tests for HSA (Harmful/Spam Analysis) module
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.ai.hsa import check_harmful, _analyze_with_llm, HSAAnalysisResult


class TestHSAModule:
    """Test cases for the HSA module functionality"""
    
    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_hsa_disabled(self, mock_config):
        """Test HSA when disabled in configuration"""
        mock_config.HSA_ENABLED = False

        title = "Need help with printer setup"
        description = "I'm having trouble setting up my new printer. Could someone help me configure it?"

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False  # Should return False when disabled

    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_no_api_key(self, mock_config):
        """Test HSA when Google API key is not configured"""
        mock_config.HSA_ENABLED = True
        mock_config.GOOGLE_API_KEY = ""

        title = "Need help with printer setup"
        description = "I'm having trouble setting up my new printer. Could someone help me configure it?"

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False  # Should fallback to safe default

    @patch('app.services.ai.hsa._analyze_with_llm')
    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_llm_success(self, mock_config, mock_llm):
        """Test HSA with successful LLM analysis"""
        mock_config.HSA_ENABLED = True
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_llm.return_value = False

        title = "Need help with printer setup"
        description = "I'm having trouble setting up my new printer. Could someone help me configure it?"

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False
        mock_llm.assert_called_once_with(title, description)

    @patch('app.services.ai.hsa._analyze_with_llm')
    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_llm_detects_harmful(self, mock_config, mock_llm):
        """Test HSA when LLM detects harmful content"""
        mock_config.HSA_ENABLED = True
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_llm.return_value = True

        title = "This is spam content"
        description = "Buy now! Click here! Free money! Urgent action required!"

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is True
        mock_llm.assert_called_once_with(title, description)

    @patch('app.services.ai.hsa._analyze_with_llm')
    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_llm_error(self, mock_config, mock_llm):
        """Test HSA when LLM analysis fails"""
        mock_config.HSA_ENABLED = True
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_llm.side_effect = Exception("LLM API error")

        title = "Need help with printer setup"
        description = "I'm having trouble setting up my new printer. Could someone help me configure it?"

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False  # Should fallback to safe default on error
        mock_llm.assert_called_once_with(title, description)

    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_empty_strings(self, mock_config):
        """Test HSA with empty title and description"""
        mock_config.HSA_ENABLED = False  # Use disabled mode for predictable behavior

        title = ""
        description = ""

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False
    
    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_long_content(self, mock_config):
        """Test HSA with very long content"""
        mock_config.HSA_ENABLED = False  # Use disabled mode for predictable behavior

        title = "A" * 1000  # Very long title
        description = "B" * 5000  # Very long description

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False
    
    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_special_characters(self, mock_config):
        """Test HSA with special characters and unicode"""
        mock_config.HSA_ENABLED = False  # Use disabled mode for predictable behavior

        title = "Help with émojis and spëcial chars! 🚀"
        description = "I need help with unicode characters: αβγδε and symbols: @#$%^&*()"

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False
    
    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_return_type(self, mock_config):
        """Test that check_harmful always returns a boolean"""
        mock_config.HSA_ENABLED = False  # Use disabled mode for predictable behavior

        test_cases = [
            ("Normal title", "Normal description"),
            ("", ""),
            ("Short", "Long description with many words to test the function"),
            ("123", "456"),
            ("Special!@#", "Characters$%^&*()"),
        ]

        for title, description in test_cases:
            result = check_harmful(title, description)
            assert isinstance(result, bool), f"Expected bool, got {type(result)} for title='{title}'"

    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_consistency(self, mock_config):
        """Test that check_harmful returns consistent results for the same input"""
        mock_config.HSA_ENABLED = False  # Use disabled mode for predictable behavior

        title = "Test consistency"
        description = "This is a test to ensure consistent results"

        # Call the function multiple times with the same input
        results = [check_harmful(title, description) for _ in range(5)]

        # All results should be the same
        assert all(result == results[0] for result in results)
        assert all(isinstance(result, bool) for result in results)

    def test_check_harmful_with_none_values(self):
        """Test HSA error handling with None values"""
        # These should raise TypeError since the function expects strings
        with pytest.raises(TypeError):
            check_harmful(None, "description")
        
        with pytest.raises(TypeError):
            check_harmful("title", None)
        
        with pytest.raises(TypeError):
            check_harmful(None, None)
    
    def test_check_harmful_with_non_string_values(self):
        """Test HSA error handling with non-string values"""
        # These should raise TypeError since the function expects strings
        with pytest.raises(TypeError):
            check_harmful(123, "description")
        
        with pytest.raises(TypeError):
            check_harmful("title", 456)
        
        with pytest.raises(TypeError):
            check_harmful([], {})


class TestHSAEdgeCases:
    """Test edge cases for HSA module"""

    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_whitespace_only(self, mock_config):
        """Test HSA with whitespace-only content"""
        mock_config.HSA_ENABLED = False  # Use disabled mode for predictable behavior

        title = "   "
        description = "\t\n\r  "

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False

    @patch('app.services.ai.hsa.ai_config')
    def test_check_harmful_with_newlines_and_tabs(self, mock_config):
        """Test HSA with content containing newlines and tabs"""
        mock_config.HSA_ENABLED = False  # Use disabled mode for predictable behavior

        title = "Title\nwith\nnewlines"
        description = "Description\twith\ttabs\nand\nnewlines"

        result = check_harmful(title, description)

        assert isinstance(result, bool)
        assert result is False


class TestHSALLMAnalysis:
    """Test cases for LLM-based HSA analysis"""

    @patch('app.services.ai.hsa.ChatGoogleGenerativeAI')
    @patch('app.services.ai.hsa.ai_config')
    def test_analyze_with_llm_success(self, mock_config, mock_llm_class):
        """Test successful LLM analysis"""
        # Setup config
        mock_config.GEMINI_MODEL = "gemini-1.5-flash"
        mock_config.GEMINI_TEMPERATURE = 0.1
        mock_config.GEMINI_MAX_TOKENS = 1000
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_config.HSA_CONFIDENCE_THRESHOLD = 0.7

        # Setup mock LLM response
        mock_response = HSAAnalysisResult(
            is_harmful=False,
            confidence=0.9,
            reason="Content appears to be a legitimate helpdesk request"
        )

        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_response

        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm_instance

        # Test the function
        result = _analyze_with_llm("Need help with printer", "My printer is not working")

        assert result is False
        mock_llm_class.assert_called_once()
        mock_structured_llm.invoke.assert_called_once()

    @patch('app.services.ai.hsa.ChatGoogleGenerativeAI')
    @patch('app.services.ai.hsa.ai_config')
    def test_analyze_with_llm_detects_harmful(self, mock_config, mock_llm_class):
        """Test LLM detecting harmful content"""
        # Setup config
        mock_config.GEMINI_MODEL = "gemini-1.5-flash"
        mock_config.GEMINI_TEMPERATURE = 0.1
        mock_config.GEMINI_MAX_TOKENS = 1000
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_config.HSA_CONFIDENCE_THRESHOLD = 0.7

        # Setup mock LLM response for harmful content
        mock_response = HSAAnalysisResult(
            is_harmful=True,
            confidence=0.95,
            reason="Content contains spam and promotional language"
        )

        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_response

        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm_instance

        # Test the function
        result = _analyze_with_llm("Buy now!", "Click here for free money!")

        assert result is True
        mock_llm_class.assert_called_once()
        mock_structured_llm.invoke.assert_called_once()

    @patch('app.services.ai.hsa.ChatGoogleGenerativeAI')
    @patch('app.services.ai.hsa.ai_config')
    def test_analyze_with_llm_low_confidence(self, mock_config, mock_llm_class):
        """Test LLM with low confidence response"""
        # Setup config
        mock_config.GEMINI_MODEL = "gemini-1.5-flash"
        mock_config.GEMINI_TEMPERATURE = 0.1
        mock_config.GEMINI_MAX_TOKENS = 1000
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_config.HSA_CONFIDENCE_THRESHOLD = 0.7

        # Setup mock LLM response with low confidence
        mock_response = HSAAnalysisResult(
            is_harmful=True,
            confidence=0.5,  # Below threshold
            reason="Uncertain about content classification"
        )

        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_response

        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm_instance

        # Test the function
        result = _analyze_with_llm("Ambiguous content", "This might be spam")

        assert result is False  # Should default to safe when confidence is low
        mock_llm_class.assert_called_once()
        mock_structured_llm.invoke.assert_called_once()


class TestHSAFallbackAnalysis:
    """Test cases for fallback text analysis"""

    def test_fallback_text_analysis_safe_content(self):
        """Test fallback analysis with safe content"""
        from app.services.ai.hsa import _fallback_text_analysis

        result = _fallback_text_analysis("Printer issue", "My printer is not working properly")
        assert result is False

    def test_fallback_text_analysis_spam_content(self):
        """Test fallback analysis with obvious spam"""
        from app.services.ai.hsa import _fallback_text_analysis

        result = _fallback_text_analysis("Buy now!", "Click here for free money! Limited time offer!")
        assert result is True

    def test_fallback_text_analysis_harmful_language(self):
        """Test fallback analysis with harmful language"""
        from app.services.ai.hsa import _fallback_text_analysis

        result = _fallback_text_analysis("This is bullshit", "F*** this system, it's shit")
        assert result is True

    def test_fallback_text_analysis_promotional_overload(self):
        """Test fallback analysis with excessive promotional language"""
        from app.services.ai.hsa import _fallback_text_analysis

        result = _fallback_text_analysis("Urgent! Free! Now!", "Act now! Limited! Free! Urgent! Now! Get it!")
        assert result is True
