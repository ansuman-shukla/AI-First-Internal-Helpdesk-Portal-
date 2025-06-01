"""
Document schemas for file upload and processing

This module defines Pydantic schemas for document upload,
processing, and knowledge base management.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types for upload"""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"


class DocumentCategory(str, Enum):
    """Document categories for knowledge base organization"""
    POLICY = "policy"
    PROCEDURE = "procedure"
    FAQ = "faq"
    TROUBLESHOOTING = "troubleshooting"
    GENERAL = "general"


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload"""
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    document_type: DocumentType = Field(..., description="Type of document")
    category: DocumentCategory = Field(..., description="Document category")
    pages_processed: Optional[int] = Field(None, description="Number of pages processed")
    chunks_created: int = Field(..., description="Number of text chunks created")
    vectors_stored: int = Field(..., description="Number of vectors stored in database")
    processing_time: float = Field(..., description="Processing time in seconds")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    uploaded_by: str = Field(..., description="Admin user who uploaded the document")
    status: str = Field(default="processed", description="Processing status")


class DocumentMetadata(BaseModel):
    """Metadata for stored documents"""
    document_id: str
    filename: str
    original_filename: str
    file_size: int
    document_type: DocumentType
    category: DocumentCategory
    uploaded_by: str
    uploaded_at: datetime
    pages_processed: Optional[int] = None
    chunks_created: int = 0
    vectors_stored: int = 0
    processing_time: float = 0.0
    checksum: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response schema for listing documents"""
    documents: List[DocumentMetadata] = Field(..., description="List of document metadata")
    total_count: int = Field(..., description="Total number of documents")
    page: int = Field(default=1, description="Current page number")
    limit: int = Field(default=20, description="Items per page")


class DocumentDeleteResponse(BaseModel):
    """Response schema for document deletion"""
    document_id: str = Field(..., description="ID of deleted document")
    filename: str = Field(..., description="Name of deleted document")
    vectors_removed: int = Field(..., description="Number of vectors removed from database")
    deleted_at: datetime = Field(..., description="Deletion timestamp")
    deleted_by: str = Field(..., description="Admin user who deleted the document")


class DocumentProcessingStatus(BaseModel):
    """Status of document processing"""
    document_id: str
    status: str  # "processing", "completed", "failed"
    progress: float  # 0.0 to 1.0
    message: Optional[str] = None
    error: Optional[str] = None


class KnowledgeBaseStats(BaseModel):
    """Statistics about the knowledge base"""
    total_documents: int = Field(..., description="Total number of documents")
    total_vectors: int = Field(..., description="Total number of vectors stored")
    documents_by_category: Dict[str, int] = Field(..., description="Document count by category")
    documents_by_type: Dict[str, int] = Field(..., description="Document count by type")
    total_size_mb: float = Field(..., description="Total size of all documents in MB")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class DocumentSearchRequest(BaseModel):
    """Request schema for searching documents"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    category: Optional[DocumentCategory] = Field(None, description="Filter by category")
    limit: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class DocumentSearchResult(BaseModel):
    """Individual search result"""
    content: str = Field(..., description="Relevant text content")
    score: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    document_id: str = Field(..., description="Source document ID")
    filename: str = Field(..., description="Source filename")
    category: str = Field(..., description="Document category")


class DocumentSearchResponse(BaseModel):
    """Response schema for document search"""
    query: str = Field(..., description="Original search query")
    results: List[DocumentSearchResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total number of results found")
    search_time: float = Field(..., description="Search time in seconds")
