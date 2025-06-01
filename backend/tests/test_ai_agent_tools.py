"""
Tests for AI Agent Tools

This module tests the individual tools used by the AI agent:
- RAG database query tool
- Web search tool
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.ai.agent import query_knowledge_base, search_web, query_agent
from app.core.ai_config import ai_config


class TestRAGTool:
    """Test the RAG database query tool"""
    
    @patch('app.services.ai.agent.rag_query')
    def test_query_knowledge_base_success(self, mock_rag_query):
        """Test successful knowledge base query"""
        # Mock RAG response
        mock_rag_query.return_value = {
            "answer": "Password reset instructions: Go to login page and click 'Forgot Password'",
            "sources": ["IT Policy Document", "User Manual"]
        }
        
        # Test the tool
        result = query_knowledge_base("How do I reset my password?")
        
        # Verify the result
        assert "Password reset instructions" in result
        assert "Sources:" in result
        assert "IT Policy Document" in result
        assert "User Manual" in result
        mock_rag_query.assert_called_once_with("How do I reset my password?")
    
    @patch('app.services.ai.agent.rag_query')
    def test_query_knowledge_base_no_sources(self, mock_rag_query):
        """Test knowledge base query with no sources"""
        # Mock RAG response without sources
        mock_rag_query.return_value = {
            "answer": "No relevant information found",
            "sources": []
        }
        
        # Test the tool
        result = query_knowledge_base("Unknown topic")
        
        # Verify the result
        assert "No relevant information found" in result
        assert "Sources:" not in result
        mock_rag_query.assert_called_once_with("Unknown topic")
    
    @patch('app.services.ai.agent.rag_query')
    def test_query_knowledge_base_error(self, mock_rag_query):
        """Test knowledge base query error handling"""
        # Mock RAG error
        mock_rag_query.side_effect = Exception("Database connection failed")
        
        # Test the tool
        result = query_knowledge_base("Test query")
        
        # Verify error handling
        assert "error while searching the knowledge base" in result
        assert "Database connection failed" in result


class TestWebSearchTool:
    """Test the web search tool"""
    
    def test_search_web_disabled(self):
        """Test web search when disabled"""
        with patch.object(ai_config, 'WEB_SEARCH_ENABLED', False):
            result = search_web("test query")
            assert "Web search is currently disabled" in result
    
    def test_search_web_no_api_key(self):
        """Test web search without API key"""
        with patch.object(ai_config, 'WEB_SEARCH_ENABLED', True), \
             patch.object(ai_config, 'SERPER_API_KEY', ''):
            result = search_web("test query")
            assert "Web search is not configured" in result
    
    @patch('app.services.ai.agent.GoogleSerperAPIWrapper')
    def test_search_web_success(self, mock_serper):
        """Test successful web search"""
        # Mock Serper API
        mock_search_instance = MagicMock()
        mock_search_instance.run.return_value = "Search results for test query"
        mock_serper.return_value = mock_search_instance
        
        with patch.object(ai_config, 'WEB_SEARCH_ENABLED', True), \
             patch.object(ai_config, 'SERPER_API_KEY', 'test-key'):
            
            result = search_web("test query")
            
            # Verify the result
            assert "Web search results for 'test query'" in result
            assert "Search results for test query" in result
            assert "external sources" in result
            mock_serper.assert_called_once_with(serper_api_key='test-key', k=5)
            mock_search_instance.run.assert_called_once_with("test query")
    
    @patch('app.services.ai.agent.GoogleSerperAPIWrapper')
    def test_search_web_error(self, mock_serper):
        """Test web search error handling"""
        # Mock Serper API error
        mock_serper.side_effect = Exception("API rate limit exceeded")
        
        with patch.object(ai_config, 'WEB_SEARCH_ENABLED', True), \
             patch.object(ai_config, 'SERPER_API_KEY', 'test-key'):
            
            result = search_web("test query")
            
            # Verify error handling
            assert "error while searching the web" in result
            assert "API rate limit exceeded" in result


class TestAgentQuery:
    """Test the main agent query function"""
    
    def test_query_agent_invalid_input(self):
        """Test agent query with invalid input"""
        # Test non-string input
        with pytest.raises(TypeError):
            query_agent(123)
        
        # Test empty string
        with pytest.raises(ValueError):
            query_agent("")
        
        # Test whitespace only
        with pytest.raises(ValueError):
            query_agent("   ")
    
    @patch('app.services.ai.agent.create_helpdesk_agent')
    def test_query_agent_success(self, mock_create_agent):
        """Test successful agent query"""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                MagicMock(content="This is the agent's response to your question.")
            ]
        }
        mock_create_agent.return_value = mock_agent
        
        # Test the query
        result = query_agent("How do I reset my password?", session_id="test123")
        
        # Verify the result
        assert result["answer"] == "This is the agent's response to your question."
        assert result["session_id"] == "test123"
        assert result["sources"] == ["AI Agent with RAG and Web Search"]
        assert "query_length" in result["metadata"]
        assert "response_length" in result["metadata"]
        assert "tools_available" in result["metadata"]
    
    @patch('app.services.ai.agent.create_helpdesk_agent')
    def test_query_agent_error(self, mock_create_agent):
        """Test agent query error handling"""
        # Mock agent creation error
        mock_create_agent.side_effect = Exception("Agent initialization failed")
        
        # Test the query
        result = query_agent("Test query")
        
        # Verify error handling
        assert "error while processing your request" in result["answer"]
        assert "Agent initialization failed" in result["answer"]
        assert "error" in result["metadata"]
    
    @patch('app.services.ai.agent.create_helpdesk_agent')
    def test_query_agent_no_messages(self, mock_create_agent):
        """Test agent query with no messages in response"""
        # Mock agent with empty messages
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": []}
        mock_create_agent.return_value = mock_agent
        
        # Test the query
        result = query_agent("Test query")
        
        # Verify fallback response
        assert "couldn't generate a response" in result["answer"]


class TestAgentConfiguration:
    """Test agent configuration and validation"""
    
    def test_create_agent_no_api_key(self):
        """Test agent creation without Google API key"""
        with patch.object(ai_config, 'GOOGLE_API_KEY', ''):
            with pytest.raises(ValueError, match="Google API key is required"):
                from app.services.ai.agent import create_helpdesk_agent
                create_helpdesk_agent()
    
    @patch('app.services.ai.agent.ChatGoogleGenerativeAI')
    @patch('app.services.ai.agent.create_react_agent')
    def test_create_agent_success(self, mock_create_react, mock_chat_llm):
        """Test successful agent creation"""
        with patch.object(ai_config, 'GOOGLE_API_KEY', 'test-key'):
            from app.services.ai.agent import create_helpdesk_agent
            
            # Mock LLM and agent
            mock_llm = MagicMock()
            mock_chat_llm.return_value = mock_llm
            mock_agent = MagicMock()
            mock_create_react.return_value = mock_agent
            
            # Create agent
            result = create_helpdesk_agent()
            
            # Verify creation
            assert result == mock_agent
            mock_chat_llm.assert_called_once()
            mock_create_react.assert_called_once()
            
            # Verify LLM configuration
            call_kwargs = mock_chat_llm.call_args[1]
            assert call_kwargs['google_api_key'] == 'test-key'
            assert call_kwargs['model'] == ai_config.GEMINI_MODEL
            assert call_kwargs['temperature'] == ai_config.GEMINI_TEMPERATURE


if __name__ == "__main__":
    pytest.main([__file__])
