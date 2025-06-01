"""
Unit tests for RAG (Retrieval-Augmented Generation) module
"""

import pytest
from app.services.ai.rag import rag_query


class TestRagQuery:
    """Test cases for rag_query function"""

    def test_rag_query_basic_functionality(self):
        """Test basic functionality with valid query"""
        query = "What is the weather today?"
        result = rag_query(query)

        # Check return type and structure
        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result

        # Check specific values for V1 stub
        assert result["answer"] == "stub"
        assert result["sources"] == []
        assert isinstance(result["sources"], list)

    def test_rag_query_with_context(self):
        """Test functionality with context provided"""
        query = "How do I reset my password?"
        context = ["IT policies", "User manual", "FAQ section"]
        result = rag_query(query, context)

        # Check return type and structure
        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result

        # Check specific values for V1 stub
        assert result["answer"] == "stub"
        assert result["sources"] == []

    def test_rag_query_with_empty_context(self):
        """Test functionality with empty context list"""
        query = "What are the office hours?"
        context = []
        result = rag_query(query, context)

        # Check return type and structure
        assert isinstance(result, dict)
        assert result["answer"] == "stub"
        assert result["sources"] == []

    def test_rag_query_with_none_context(self):
        """Test functionality with None context (default)"""
        query = "How do I submit a ticket?"
        result = rag_query(query, None)

        # Check return type and structure
        assert isinstance(result, dict)
        assert result["answer"] == "stub"
        assert result["sources"] == []

    def test_rag_query_long_query(self):
        """Test with a long query string"""
        query = "This is a very long query " * 50  # Create a long string
        result = rag_query(query)

        assert isinstance(result, dict)
        assert result["answer"] == "stub"
        assert result["sources"] == []

    def test_rag_query_special_characters(self):
        """Test with special characters in query"""
        query = "How do I fix error: 'Connection failed!' @#$%^&*()"
        result = rag_query(query)

        assert isinstance(result, dict)
        assert result["answer"] == "stub"
        assert result["sources"] == []

    def test_rag_query_unicode_characters(self):
        """Test with unicode characters in query"""
        query = "Comment puis-je réinitialiser mon mot de passe? 你好"
        result = rag_query(query)

        assert isinstance(result, dict)
        assert result["answer"] == "stub"
        assert result["sources"] == []

    # Error handling tests
    def test_rag_query_invalid_query_type(self):
        """Test error handling for invalid query type"""
        with pytest.raises(TypeError, match="query must be a string"):
            rag_query(123)

        with pytest.raises(TypeError, match="query must be a string"):
            rag_query(None)

        with pytest.raises(TypeError, match="query must be a string"):
            rag_query(["not", "a", "string"])

    def test_rag_query_empty_query(self):
        """Test error handling for empty query"""
        with pytest.raises(
            ValueError, match="query cannot be empty or only whitespace"
        ):
            rag_query("")

        with pytest.raises(
            ValueError, match="query cannot be empty or only whitespace"
        ):
            rag_query("   ")

        with pytest.raises(
            ValueError, match="query cannot be empty or only whitespace"
        ):
            rag_query("\t\n")

    def test_rag_query_invalid_context_type(self):
        """Test error handling for invalid context type"""
        query = "Valid query"

        with pytest.raises(TypeError, match="context must be a list or None"):
            rag_query(query, "not a list")

        with pytest.raises(TypeError, match="context must be a list or None"):
            rag_query(query, 123)

        with pytest.raises(TypeError, match="context must be a list or None"):
            rag_query(query, {"not": "a list"})

    def test_rag_query_invalid_context_items(self):
        """Test error handling for invalid context items"""
        query = "Valid query"

        with pytest.raises(TypeError, match="context\\[0\\] must be a string"):
            rag_query(query, [123])

        with pytest.raises(TypeError, match="context\\[1\\] must be a string"):
            rag_query(query, ["valid", 456])

        with pytest.raises(TypeError, match="context\\[2\\] must be a string"):
            rag_query(query, ["valid", "also valid", None])

    def test_rag_query_mixed_valid_context(self):
        """Test with various valid context strings"""
        query = "How do I troubleshoot network issues?"
        context = [
            "Network troubleshooting guide",
            "Common network problems",
            "Step-by-step solutions",
            "",  # Empty string should be valid
            "Final context item",
        ]
        result = rag_query(query, context)

        assert isinstance(result, dict)
        assert result["answer"] == "stub"
        assert result["sources"] == []

    def test_rag_query_return_type_consistency(self):
        """Test that return type is always consistent"""
        queries = [
            "Short query",
            "This is a much longer query with more details about the problem",
            "Query with numbers 123 and symbols !@#",
            "Query\nwith\nnewlines",
        ]

        for query in queries:
            result = rag_query(query)
            assert isinstance(result, dict)
            assert set(result.keys()) == {"answer", "sources"}
            assert isinstance(result["answer"], str)
            assert isinstance(result["sources"], list)
            assert result["answer"] == "stub"
            assert result["sources"] == []

    def test_rag_query_function_signature(self):
        """Test that function signature matches requirements"""
        import inspect
        from app.services.ai.rag import rag_query

        sig = inspect.signature(rag_query)
        params = list(sig.parameters.keys())

        # Check parameter names
        assert params == ["query", "context"]

        # Check parameter types and defaults
        query_param = sig.parameters["query"]
        context_param = sig.parameters["context"]

        assert query_param.default == inspect.Parameter.empty  # Required parameter
        assert context_param.default is None  # Optional with None default
