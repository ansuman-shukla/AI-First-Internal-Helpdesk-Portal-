"""
AI Configuration Module

This module handles configuration for AI services including LLM and vector database settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class AIConfig:
    """Configuration class for AI services"""
    
    # Google Gemini Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
    GEMINI_MAX_TOKENS: int = int(os.getenv("GEMINI_MAX_TOKENS", "1000"))
    
    # Pinecone Configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "helpdesk-knowledge-base")

    # Google Serper Configuration (for web search)
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    WEB_SEARCH_ENABLED: bool = os.getenv("WEB_SEARCH_ENABLED", "true").lower() == "true"
    
    # HSA Configuration
    HSA_ENABLED: bool = os.getenv("HSA_ENABLED", "true").lower() == "true"
    HSA_CONFIDENCE_THRESHOLD: float = float(os.getenv("HSA_CONFIDENCE_THRESHOLD", "0.7"))
    
    # RAG Configuration
    RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() == "true"
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.8"))
    
    # Logging Configuration
    AI_LOG_LEVEL: str = os.getenv("AI_LOG_LEVEL", "DEBUG")
    
    @classmethod
    def validate_config(cls) -> dict:
        """
        Validate AI configuration and return status
        
        Returns:
            dict: Configuration validation status
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required API keys
        if not cls.GOOGLE_API_KEY:
            validation_result["errors"].append("GOOGLE_API_KEY is required for LLM operations")
            validation_result["valid"] = False
            
        if not cls.PINECONE_API_KEY and cls.RAG_ENABLED:
            validation_result["errors"].append("PINECONE_API_KEY is required when RAG is enabled")
            validation_result["valid"] = False
            
        if not cls.PINECONE_ENVIRONMENT and cls.RAG_ENABLED:
            validation_result["errors"].append("PINECONE_ENVIRONMENT is required when RAG is enabled")
            validation_result["valid"] = False

        if not cls.SERPER_API_KEY and cls.WEB_SEARCH_ENABLED:
            validation_result["warnings"].append("SERPER_API_KEY is recommended when web search is enabled")
        
        # Check configuration values
        if cls.GEMINI_TEMPERATURE < 0 or cls.GEMINI_TEMPERATURE > 2:
            validation_result["warnings"].append("GEMINI_TEMPERATURE should be between 0 and 2")
            
        if cls.HSA_CONFIDENCE_THRESHOLD < 0 or cls.HSA_CONFIDENCE_THRESHOLD > 1:
            validation_result["warnings"].append("HSA_CONFIDENCE_THRESHOLD should be between 0 and 1")
            
        if cls.RAG_SIMILARITY_THRESHOLD < 0 or cls.RAG_SIMILARITY_THRESHOLD > 1:
            validation_result["warnings"].append("RAG_SIMILARITY_THRESHOLD should be between 0 and 1")
        
        return validation_result
    
    @classmethod
    def get_safe_config(cls) -> dict:
        """
        Get configuration with sensitive data masked
        
        Returns:
            dict: Safe configuration for logging
        """
        return {
            "gemini_model": cls.GEMINI_MODEL,
            "gemini_temperature": cls.GEMINI_TEMPERATURE,
            "gemini_max_tokens": cls.GEMINI_MAX_TOKENS,
            "google_api_key_configured": bool(cls.GOOGLE_API_KEY),
            "pinecone_api_key_configured": bool(cls.PINECONE_API_KEY),
            "pinecone_environment": cls.PINECONE_ENVIRONMENT,
            "pinecone_index_name": cls.PINECONE_INDEX_NAME,
            "serper_api_key_configured": bool(cls.SERPER_API_KEY),
            "web_search_enabled": cls.WEB_SEARCH_ENABLED,
            "hsa_enabled": cls.HSA_ENABLED,
            "hsa_confidence_threshold": cls.HSA_CONFIDENCE_THRESHOLD,
            "rag_enabled": cls.RAG_ENABLED,
            "rag_top_k": cls.RAG_TOP_K,
            "rag_similarity_threshold": cls.RAG_SIMILARITY_THRESHOLD,
            "ai_log_level": cls.AI_LOG_LEVEL
        }


# Global configuration instance
ai_config = AIConfig()

# Validate configuration on import
config_validation = ai_config.validate_config()
if not config_validation["valid"]:
    logger.warning(f"AI Configuration validation failed: {config_validation['errors']}")
if config_validation["warnings"]:
    logger.warning(f"AI Configuration warnings: {config_validation['warnings']}")

logger.info(f"AI Configuration loaded: {ai_config.get_safe_config()}")
