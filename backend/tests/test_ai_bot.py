"""
Unit tests for AI Bot endpoints and RAG query functionality
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.services.ai.rag_query import rag_query

client = TestClient(app)


class TestRAGQueryService:
    """Test cases for the RAG query service functionality"""
    
    def test_rag_query_with_it_content(self):
        """Test RAG query with IT-related content"""
        query = "How do I reset my password?"
        
        result = rag_query(query)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "IT" in result or "technical" in result or "password" in result
    
    def test_rag_query_with_hr_content(self):
        """Test RAG query with HR-related content"""
        query = "What are the vacation policies?"
        
        result = rag_query(query)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "HR" in result or "leave" in result or "vacation" in result
    
    def test_rag_query_with_general_content(self):
        """Test RAG query with general help content"""
        query = "Hello, can you help me?"
        
        result = rag_query(query)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "help" in result.lower() or "assist" in result.lower()
    
    def test_rag_query_with_session_id(self):
        """Test RAG query with session ID"""
        query = "How do I create a ticket?"
        session_id = "test-session-123"
        
        result = rag_query(query, session_id)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "ticket" in result.lower()
    
    def test_rag_query_with_empty_query(self):
        """Test RAG query error handling with empty query"""
        with pytest.raises(ValueError):
            rag_query("")
        
        with pytest.raises(ValueError):
            rag_query("   ")
    
    def test_rag_query_with_none_query(self):
        """Test RAG query error handling with None query"""
        with pytest.raises(TypeError):
            rag_query(None)
    
    def test_rag_query_with_non_string_query(self):
        """Test RAG query error handling with non-string query"""
        with pytest.raises(TypeError):
            rag_query(123)
        
        with pytest.raises(TypeError):
            rag_query(["query"])
    
    def test_rag_query_with_invalid_session_id(self):
        """Test RAG query error handling with invalid session ID"""
        with pytest.raises(TypeError):
            rag_query("test query", 123)
    
    def test_rag_query_consistency(self):
        """Test that RAG query returns consistent results for the same input"""
        query = "Test consistency"
        
        # Call the function multiple times with the same input
        results = [rag_query(query) for _ in range(3)]
        
        # All results should be the same for the stub implementation
        assert all(result == results[0] for result in results)
        assert all(isinstance(result, str) for result in results)


class TestSelfServeQueryEndpoint:
    """Test cases for the self-serve query endpoint"""
    
    def test_self_serve_query_success(self):
        """Test successful self-serve query"""
        response = client.post(
            "/ai/self-serve-query",
            json={"query": "How do I reset my password?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
    
    def test_self_serve_query_with_session_id(self):
        """Test self-serve query with session ID"""
        response = client.post(
            "/ai/self-serve-query",
            json={
                "query": "What are the HR policies?",
                "session_id": "test-session-456"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
    
    def test_self_serve_query_various_topics(self):
        """Test self-serve query with various topic queries"""
        test_queries = [
            "How do I install software?",
            "What are the vacation policies?",
            "Hello, I need help",
            "How do I create a ticket?",
            "My computer is not working"
        ]
        
        for query in test_queries:
            response = client.post(
                "/ai/self-serve-query",
                json={"query": query}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert isinstance(data["answer"], str)
            assert len(data["answer"]) > 0
    
    def test_self_serve_query_empty_query(self):
        """Test self-serve query with empty query"""
        response = client.post(
            "/ai/self-serve-query",
            json={"query": ""}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_self_serve_query_whitespace_only(self):
        """Test self-serve query with whitespace-only query"""
        response = client.post(
            "/ai/self-serve-query",
            json={"query": "   "}
        )
        
        assert response.status_code == 400  # Bad request due to validation
    
    def test_self_serve_query_missing_query(self):
        """Test self-serve query with missing query field"""
        response = client.post(
            "/ai/self-serve-query",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_self_serve_query_too_long(self):
        """Test self-serve query with query that's too long"""
        long_query = "x" * 1001  # Exceeds 1000 character limit
        
        response = client.post(
            "/ai/self-serve-query",
            json={"query": long_query}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_self_serve_query_invalid_json(self):
        """Test self-serve query with invalid JSON"""
        response = client.post(
            "/ai/self-serve-query",
            data="invalid json"
        )
        
        assert response.status_code == 422  # Validation error


class TestSelfServeInfoEndpoint:
    """Test cases for the self-serve info endpoint"""
    
    def test_self_serve_info_success(self):
        """Test successful self-serve info retrieval"""
        response = client.get("/ai/self-serve-info")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "service" in data
        assert "description" in data
        assert "features" in data
        assert "usage" in data
        assert "examples" in data
        
        # Check data types
        assert isinstance(data["features"], list)
        assert isinstance(data["usage"], dict)
        assert isinstance(data["examples"], list)
        
        # Check usage information
        usage = data["usage"]
        assert "endpoint" in usage
        assert "method" in usage
        assert "required_fields" in usage
        assert "optional_fields" in usage
        assert "query_limits" in usage
        
        # Check examples
        examples = data["examples"]
        assert len(examples) > 0
        for example in examples:
            assert "query" in example
            assert "description" in example


class TestAIBotIntegration:
    """Integration tests for AI bot functionality"""
    
    def test_ai_bot_endpoint_accessibility(self):
        """Test that AI bot endpoints are accessible without authentication"""
        # Test self-serve query endpoint
        response = client.post(
            "/ai/self-serve-query",
            json={"query": "Test query"}
        )
        assert response.status_code == 200
        
        # Test self-serve info endpoint
        response = client.get("/ai/self-serve-info")
        assert response.status_code == 200
    
    def test_ai_bot_response_format(self):
        """Test that AI bot responses follow the expected format"""
        response = client.post(
            "/ai/self-serve-query",
            json={"query": "How can I get help?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert isinstance(data, dict)
        assert "answer" in data
        assert len(data) == 1  # Only answer field expected
        
        # Check answer content
        answer = data["answer"]
        assert isinstance(answer, str)
        assert len(answer.strip()) > 0
