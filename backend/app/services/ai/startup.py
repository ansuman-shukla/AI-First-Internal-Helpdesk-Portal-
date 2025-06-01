"""
AI Services Startup Module

This module handles initialization of AI services including vector store and knowledge base.
Should be called during application startup to ensure all AI components are ready.
"""

import logging
from typing import Dict, Any
from app.core.ai_config import ai_config
from app.services.ai.vector_store import initialize_vector_store, get_vector_store_manager
from app.services.ai.knowledge_base import initialize_knowledge_base

logger = logging.getLogger(__name__)


def initialize_ai_services() -> Dict[str, Any]:
    """
    Initialize all AI services including vector store and knowledge base.
    
    Returns:
        Dict with initialization status and details
    """
    logger.info("Starting AI services initialization")
    
    initialization_result = {
        "success": False,
        "vector_store_initialized": False,
        "knowledge_base_initialized": False,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Validate AI configuration first
        config_validation = ai_config.validate_config()
        
        if not config_validation["valid"]:
            initialization_result["errors"].extend(config_validation["errors"])
            logger.error(f"AI configuration validation failed: {config_validation['errors']}")
            return initialization_result
        
        if config_validation["warnings"]:
            initialization_result["warnings"].extend(config_validation["warnings"])
            logger.warning(f"AI configuration warnings: {config_validation['warnings']}")
        
        # Initialize vector store if RAG is enabled
        if ai_config.RAG_ENABLED:
            logger.info("Initializing Pinecone vector store")
            
            if initialize_vector_store():
                initialization_result["vector_store_initialized"] = True
                logger.info("Vector store initialization successful")
                
                # Initialize knowledge base
                logger.info("Initializing knowledge base")
                
                if initialize_knowledge_base():
                    initialization_result["knowledge_base_initialized"] = True
                    logger.info("Knowledge base initialization successful")
                else:
                    initialization_result["errors"].append("Knowledge base initialization failed")
                    logger.error("Knowledge base initialization failed")
            else:
                initialization_result["errors"].append("Vector store initialization failed")
                logger.error("Vector store initialization failed")
        else:
            logger.info("RAG is disabled, skipping vector store initialization")
            initialization_result["warnings"].append("RAG is disabled")
        
        # Check overall success
        if ai_config.RAG_ENABLED:
            initialization_result["success"] = (
                initialization_result["vector_store_initialized"] and 
                initialization_result["knowledge_base_initialized"]
            )
        else:
            initialization_result["success"] = True  # Success if RAG is disabled
        
        if initialization_result["success"]:
            logger.info("AI services initialization completed successfully")
        else:
            logger.error("AI services initialization failed")
        
        return initialization_result
        
    except Exception as e:
        error_msg = f"Unexpected error during AI services initialization: {str(e)}"
        initialization_result["errors"].append(error_msg)
        logger.error(error_msg)
        return initialization_result


def get_ai_services_status() -> Dict[str, Any]:
    """
    Get current status of AI services.
    
    Returns:
        Dict with current status information
    """
    try:
        status = {
            "ai_config_valid": True,
            "vector_store_initialized": False,
            "vector_store_stats": {},
            "services_available": {
                "hsa": False,
                "routing": False,
                "rag": False
            }
        }
        
        # Check AI configuration
        config_validation = ai_config.validate_config()
        status["ai_config_valid"] = config_validation["valid"]
        
        if not config_validation["valid"]:
            status["config_errors"] = config_validation["errors"]
        
        # Check vector store status
        vector_store = get_vector_store_manager()
        status["vector_store_initialized"] = vector_store._initialized
        
        if vector_store._initialized:
            status["vector_store_stats"] = vector_store.get_index_stats()
        
        # Check service availability
        status["services_available"]["hsa"] = bool(ai_config.GOOGLE_API_KEY and ai_config.HSA_ENABLED)
        status["services_available"]["routing"] = bool(ai_config.GOOGLE_API_KEY)
        status["services_available"]["rag"] = bool(
            ai_config.GOOGLE_API_KEY and 
            ai_config.RAG_ENABLED and 
            vector_store._initialized
        )
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting AI services status: {str(e)}")
        return {
            "error": str(e),
            "ai_config_valid": False,
            "vector_store_initialized": False,
            "services_available": {
                "hsa": False,
                "routing": False,
                "rag": False
            }
        }


def health_check() -> Dict[str, Any]:
    """
    Perform health check on AI services.
    
    Returns:
        Dict with health check results
    """
    logger.debug("Performing AI services health check")
    
    health_status = {
        "healthy": True,
        "checks": {
            "config": {"status": "unknown", "details": ""},
            "vector_store": {"status": "unknown", "details": ""},
            "llm_connectivity": {"status": "unknown", "details": ""}
        }
    }
    
    try:
        # Check configuration
        config_validation = ai_config.validate_config()
        if config_validation["valid"]:
            health_status["checks"]["config"]["status"] = "healthy"
            health_status["checks"]["config"]["details"] = "Configuration valid"
        else:
            health_status["checks"]["config"]["status"] = "unhealthy"
            health_status["checks"]["config"]["details"] = f"Config errors: {config_validation['errors']}"
            health_status["healthy"] = False
        
        # Check vector store
        if ai_config.RAG_ENABLED:
            vector_store = get_vector_store_manager()
            if vector_store._initialized:
                try:
                    stats = vector_store.get_index_stats()
                    if "error" not in stats:
                        health_status["checks"]["vector_store"]["status"] = "healthy"
                        health_status["checks"]["vector_store"]["details"] = f"Vector count: {stats.get('total_vector_count', 0)}"
                    else:
                        health_status["checks"]["vector_store"]["status"] = "unhealthy"
                        health_status["checks"]["vector_store"]["details"] = stats["error"]
                        health_status["healthy"] = False
                except Exception as e:
                    health_status["checks"]["vector_store"]["status"] = "unhealthy"
                    health_status["checks"]["vector_store"]["details"] = str(e)
                    health_status["healthy"] = False
            else:
                health_status["checks"]["vector_store"]["status"] = "unhealthy"
                health_status["checks"]["vector_store"]["details"] = "Vector store not initialized"
                health_status["healthy"] = False
        else:
            health_status["checks"]["vector_store"]["status"] = "disabled"
            health_status["checks"]["vector_store"]["details"] = "RAG disabled"
        
        # Check LLM connectivity (basic check)
        if ai_config.GOOGLE_API_KEY:
            health_status["checks"]["llm_connectivity"]["status"] = "healthy"
            health_status["checks"]["llm_connectivity"]["details"] = "API key configured"
        else:
            health_status["checks"]["llm_connectivity"]["status"] = "unhealthy"
            health_status["checks"]["llm_connectivity"]["details"] = "No API key configured"
            health_status["healthy"] = False
        
        logger.debug(f"Health check completed - Overall status: {'healthy' if health_status['healthy'] else 'unhealthy'}")
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "healthy": False,
            "error": str(e),
            "checks": {
                "config": {"status": "error", "details": str(e)},
                "vector_store": {"status": "error", "details": str(e)},
                "llm_connectivity": {"status": "error", "details": str(e)}
            }
        }


def reinitialize_services() -> Dict[str, Any]:
    """
    Reinitialize AI services (useful for recovery or configuration changes).
    
    Returns:
        Dict with reinitialization results
    """
    logger.info("Reinitializing AI services")
    
    try:
        # Reset vector store manager
        vector_store = get_vector_store_manager()
        vector_store._initialized = False
        vector_store.pc = None
        vector_store.index = None
        vector_store.embeddings = None
        vector_store.vector_store = None
        
        # Reinitialize
        return initialize_ai_services()
        
    except Exception as e:
        logger.error(f"Failed to reinitialize AI services: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
