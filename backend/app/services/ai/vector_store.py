"""
Pinecone Vector Store Module

This module handles Pinecone vector database operations for RAG functionality.
Provides initialization, document embedding, storage, and retrieval capabilities.
"""

import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from app.core.ai_config import ai_config

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages Pinecone vector store operations for RAG"""
    
    def __init__(self):
        self.pc = None
        self.index = None
        self.embeddings = None
        self.vector_store = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize Pinecone vector store and embeddings.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing Pinecone vector store")
            
            # Validate configuration
            if not ai_config.PINECONE_API_KEY:
                logger.error("PINECONE_API_KEY not configured")
                return False
                
            if not ai_config.GOOGLE_API_KEY:
                logger.error("GOOGLE_API_KEY not configured for embeddings")
                return False
            
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=ai_config.PINECONE_API_KEY)
            logger.debug("Pinecone client initialized")
            
            # Initialize embeddings
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=ai_config.GOOGLE_API_KEY,
                task_type="RETRIEVAL_DOCUMENT"
            )
            logger.debug("Google embeddings initialized")
            
            # Create or connect to index
            if not self._setup_index():
                return False
            
            # Initialize vector store
            self.vector_store = PineconeVectorStore(
                index=self.index,
                embedding=self.embeddings
            )
            logger.debug("PineconeVectorStore initialized")
            
            self._initialized = True
            logger.info("Pinecone vector store initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone vector store: {str(e)}")
            return False
    
    def _setup_index(self) -> bool:
        """
        Setup Pinecone index, creating if it doesn't exist.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            index_name = ai_config.PINECONE_INDEX_NAME
            
            # Check if index exists
            if not self.pc.has_index(index_name):
                logger.info(f"Creating new Pinecone index: {index_name}")
                
                # Create index with appropriate dimensions for text-embedding-004
                self.pc.create_index(
                    name=index_name,
                    dimension=768,  # text-embedding-004 dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info(f"Pinecone index '{index_name}' created successfully")
            else:
                logger.info(f"Using existing Pinecone index: {index_name}")
            
            # Connect to index
            self.index = self.pc.Index(index_name)
            logger.debug(f"Connected to Pinecone index: {index_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Pinecone index: {str(e)}")
            return False
    
    def add_documents(self, documents: List[Document]) -> bool:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of LangChain Document objects to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Vector store not initialized")
            return False
        
        try:
            logger.info(f"Adding {len(documents)} documents to vector store")
            
            # Generate unique IDs for documents
            ids = [f"doc_{i}" for i in range(len(documents))]
            
            # Add documents to vector store
            self.vector_store.add_documents(documents=documents, ids=ids)
            
            logger.info(f"Successfully added {len(documents)} documents to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {str(e)}")
            return False
    
    def similarity_search(self, query: str, k: int = 8, score_threshold: float = 0.8) -> List[Document]:
        """
        Perform similarity search in the vector store.
        
        Args:
            query: Search query string
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of relevant Document objects
        """
        if not self._initialized:
            logger.error("Vector store not initialized")
            return []
        
        try:
            logger.debug(f"Performing similarity search for query: '{query[:50]}...'")
            
            # Perform similarity search with score threshold
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k
            )
            
            # Filter by score threshold
            filtered_results = [
                doc for doc, score in results 
                if score >= score_threshold
            ]
            
            logger.debug(f"Found {len(filtered_results)} relevant documents (threshold: {score_threshold})")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {str(e)}")
            return []
    
    def get_retriever(self, k: int = 5, score_threshold: float = 0.8):
        """
        Get a retriever object for use in RAG chains.
        
        Args:
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            Retriever object or None if not initialized
        """
        if not self._initialized:
            logger.error("Vector store not initialized")
            return None
        
        try:
            retriever = self.vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "k": k,
                    "score_threshold": score_threshold
                }
            )
            
            logger.debug(f"Created retriever with k={k}, threshold={score_threshold}")
            return retriever
            
        except Exception as e:
            logger.error(f"Failed to create retriever: {str(e)}")
            return None
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index.
        
        Returns:
            Dictionary with index statistics
        """
        if not self._initialized or not self.index:
            return {"error": "Vector store not initialized"}
        
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            return {"error": str(e)}


# Global vector store manager instance
vector_store_manager = VectorStoreManager()


def initialize_vector_store() -> bool:
    """
    Initialize the global vector store manager.
    
    Returns:
        bool: True if initialization successful
    """
    return vector_store_manager.initialize()


def get_vector_store_manager() -> VectorStoreManager:
    """
    Get the global vector store manager instance.
    
    Returns:
        VectorStoreManager instance
    """
    return vector_store_manager
