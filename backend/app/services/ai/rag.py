"""
RAG (Retrieval-Augmented Generation) Module

This module provides RAG functionality for the helpdesk system using Pinecone vector store and Google Gemini LLM.
Combines document retrieval with LLM generation for accurate, context-aware responses.
"""

import logging
from typing import Optional, List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from app.core.ai_config import ai_config
from app.services.ai.vector_store import get_vector_store_manager

logger = logging.getLogger(__name__)


def rag_query(query: str, context: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Process a user query using RAG (Retrieval-Augmented Generation) approach with Pinecone and Google Gemini.

    Args:
        query (str): The user's question or query
        context (Optional[List[str]]): Optional list of context strings for enhanced responses

    Returns:
        Dict[str, Any]: Dictionary containing:
            - answer (str): Generated response to the query
            - sources (List[str]): List of source references from knowledge base

    Raises:
        TypeError: If query is not a string or context is not a list of strings
        ValueError: If query is empty or only whitespace
    """
    # Type validation for query
    if not isinstance(query, str):
        raise TypeError(f"query must be a string, got {type(query).__name__}")

    # Content validation for query
    if not query.strip():
        raise ValueError("query cannot be empty or only whitespace")

    # Type validation for context
    if context is not None:
        if not isinstance(context, list):
            raise TypeError(
                f"context must be a list or None, got {type(context).__name__}"
            )

        # Validate each context item is a string
        for i, item in enumerate(context):
            if not isinstance(item, str):
                raise TypeError(
                    f"context[{i}] must be a string, got {type(item).__name__}"
                )

    logger.info(
        f"RAG query requested - Query length: {len(query)}, Context items: {len(context) if context else 0}"
    )
    logger.debug(f"RAG query content: '{query[:100]}...' (truncated)")

    if context:
        logger.debug(f"RAG context provided: {len(context)} items")

    # Check if RAG is enabled and configured
    if not ai_config.RAG_ENABLED:
        logger.info("RAG is disabled, returning fallback response")
        return _fallback_response(query)

    if not ai_config.GOOGLE_API_KEY:
        logger.warning("Google API key not configured, returning fallback response")
        return _fallback_response(query)

    try:
        # Use real RAG implementation
        result = _analyze_with_llm(query, context)
        logger.info(f"RAG analysis complete - Query: '{query[:50]}...', Answer length: {len(result['answer'])}")
        return result

    except Exception as e:
        logger.error(f"RAG analysis failed: {str(e)}, returning fallback response")
        return _fallback_response(query)


def _analyze_with_llm(
    query: str, context: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyze query using RAG with Pinecone vector store and Google Gemini LLM.

    Args:
        query (str): The user's question or query
        context (Optional[List[str]]): Optional context for enhanced responses

    Returns:
        Dict[str, Any]: Dictionary with answer and sources
    """
    logger.debug("Initializing RAG with Pinecone and Gemini LLM")

    # Get vector store manager
    vector_store = get_vector_store_manager()

    if not vector_store._initialized:
        logger.error("Vector store not initialized")
        raise RuntimeError("Vector store not initialized")

    # Retrieve relevant documents from knowledge base
    logger.debug("Retrieving relevant documents from knowledge base")
    relevant_docs = vector_store.similarity_search(
        query,
        k=ai_config.RAG_TOP_K,
        score_threshold=ai_config.RAG_SIMILARITY_THRESHOLD
    )

    if not relevant_docs:
        logger.warning("No relevant documents found in knowledge base")
        return {
            "answer": "I couldn't find relevant information in the knowledge base to answer your question. Please contact support for assistance.",
            "sources": []
        }

    # Extract content and sources from retrieved documents
    retrieved_content = []
    sources = []

    for doc in relevant_docs:
        retrieved_content.append(doc.page_content)
        if hasattr(doc, 'metadata') and doc.metadata:
            source_info = doc.metadata.get('source', 'Unknown')
            category = doc.metadata.get('category', '')
            if category:
                source_info += f" ({category})"
            sources.append(source_info)

    logger.debug(f"Retrieved {len(relevant_docs)} relevant documents")

    # Initialize ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=ai_config.GEMINI_MODEL,
        temperature=ai_config.GEMINI_TEMPERATURE,
        max_tokens=ai_config.GEMINI_MAX_TOKENS,
        google_api_key=ai_config.GOOGLE_API_KEY,
        max_retries=2,
        timeout=30
    )

    # Create RAG prompt template
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful AI assistant for an internal company helpdesk system. Your job is to answer employee questions using the provided knowledge base information.

Instructions:
1. Use ONLY the information provided in the knowledge base context below
2. If the knowledge base doesn't contain relevant information, say so clearly
3. Provide step-by-step instructions when applicable
4. Be concise but thorough in your responses
5. If you need to reference specific policies or procedures, mention the source
6. For technical issues, provide troubleshooting steps when available

Knowledge Base Context:
{context}

Additional Context (if provided):
{additional_context}"""),
        ("human", "{question}")
    ])

    # Prepare context and additional context
    knowledge_context = "\n\n".join([f"Source: {sources[i] if i < len(sources) else 'Unknown'}\nContent: {content}"
                                    for i, content in enumerate(retrieved_content)])

    additional_context_str = ""
    if context:
        additional_context_str = "\n".join(context)

    # Create RAG chain
    rag_chain = rag_prompt | llm | StrOutputParser()

    # Generate response
    logger.debug("Generating RAG response with LLM")

    try:
        response = rag_chain.invoke({
            "context": knowledge_context,
            "additional_context": additional_context_str,
            "question": query
        })

        logger.debug(f"RAG response generated - Length: {len(response)}")

        return {
            "answer": response,
            "sources": list(set(sources))  # Remove duplicates
        }

    except Exception as e:
        logger.error(f"Error generating RAG response: {str(e)}")
        raise


def _fallback_response(query: str) -> Dict[str, Any]:
    """
    Generate fallback response when RAG is unavailable.

    Args:
        query: User query

    Returns:
        Dictionary with fallback answer and empty sources
    """
    logger.debug("Generating fallback response")

    # Simple keyword-based responses
    query_lower = query.lower()

    if any(word in query_lower for word in ["password", "reset", "login"]):
        answer = "For password reset issues, please contact IT support at ext. 1234 or visit the company login page and click 'Forgot Password'."
    elif any(word in query_lower for word in ["email", "outlook", "mail"]):
        answer = "For email issues, please contact IT support at ext. 1234. They can help with email setup, configuration, and troubleshooting."
    elif any(word in query_lower for word in ["vacation", "leave", "time off"]):
        answer = "For vacation and leave requests, please log into the HR portal at hr.company.com or contact HR directly."
    elif any(word in query_lower for word in ["benefits", "insurance", "401k"]):
        answer = "For benefits questions, please contact HR or visit the HR portal for detailed information about your benefits package."
    else:
        answer = "I'm currently unable to access the knowledge base. Please contact the appropriate support team (IT: ext. 1234, HR: ext. 5678) for assistance with your question."

    return {
        "answer": answer,
        "sources": []
    }
