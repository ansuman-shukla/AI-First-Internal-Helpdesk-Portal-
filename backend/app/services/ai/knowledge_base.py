"""
Knowledge Base Module

This module handles initialization and management of the helpdesk knowledge base.
Provides sample documents and utilities for populating the vector store.
"""

import logging
from typing import List, Dict, Any
from langchain_core.documents import Document
from app.services.ai.vector_store import get_vector_store_manager

logger = logging.getLogger(__name__)


def get_sample_knowledge_base() -> List[Document]:
    """
    Get sample helpdesk knowledge base documents.
    
    Returns:
        List of Document objects with helpdesk knowledge
    """
    documents = [
        # IT Knowledge Base Documents
        Document(
            page_content="""
            Password Reset Procedure:
            1. Go to the company login page
            2. Click 'Forgot Password' link
            3. Enter your email address
            4. Check your email for reset instructions
            5. Follow the link in the email to create a new password
            6. Password must be at least 8 characters with uppercase, lowercase, and numbers
            
            If you don't receive the email within 10 minutes, check your spam folder.
            For urgent password resets, contact IT support at ext. 1234.
            """,
            metadata={
                "source": "IT_Manual",
                "category": "Authentication",
                "department": "IT",
                "keywords": ["password", "reset", "login", "authentication"]
            }
        ),
        
        Document(
            page_content="""
            Email Setup on Mobile Devices:
            
            For iPhone/iPad:
            1. Go to Settings > Mail > Accounts
            2. Tap 'Add Account' > 'Other'
            3. Enter your company email and password
            4. Server settings: mail.company.com (IMAP: 993, SMTP: 587)
            5. Enable SSL for both incoming and outgoing mail
            
            For Android:
            1. Open Email app > Settings > Add Account
            2. Choose 'Other' or 'IMAP'
            3. Enter email and password
            4. Use same server settings as above
            
            Contact IT if you need help with server configurations.
            """,
            metadata={
                "source": "IT_Manual",
                "category": "Email",
                "department": "IT",
                "keywords": ["email", "mobile", "setup", "iphone", "android", "imap"]
            }
        ),
        
        Document(
            page_content="""
            VPN Connection Issues:
            
            Common solutions:
            1. Check internet connection first
            2. Restart VPN client application
            3. Try different VPN server location
            4. Disable firewall temporarily to test
            5. Clear DNS cache: ipconfig /flushdns (Windows) or sudo dscacheutil -flushcache (Mac)
            
            If still having issues:
            - Check if VPN credentials are correct
            - Ensure VPN client is updated to latest version
            - Contact IT for server status updates
            
            Emergency access: Use web portal at portal.company.com
            """,
            metadata={
                "source": "IT_Manual",
                "category": "Network",
                "department": "IT",
                "keywords": ["vpn", "connection", "network", "remote", "access"]
            }
        ),
        
        Document(
            page_content="""
            Software Installation Requests:
            
            Process:
            1. Submit request through IT portal
            2. Include business justification
            3. Specify exact software name and version
            4. IT will review for security compliance
            5. Approval typically takes 2-3 business days
            6. Installation will be scheduled with user
            
            Pre-approved software list available on company intranet.
            For urgent requests, contact IT manager directly.
            
            Note: Personal software installation is not permitted on company devices.
            """,
            metadata={
                "source": "IT_Manual",
                "category": "Software",
                "department": "IT",
                "keywords": ["software", "installation", "request", "approval", "security"]
            }
        ),
        
        # HR Knowledge Base Documents
        Document(
            page_content="""
            Vacation Request Process:
            
            Steps:
            1. Log into HR portal at hr.company.com
            2. Navigate to 'Time Off' section
            3. Select vacation dates (minimum 2 weeks advance notice)
            4. Submit request to direct manager
            5. Manager has 5 business days to approve/deny
            6. HR will send confirmation email once approved
            
            Vacation Policy:
            - Minimum 2 weeks advance notice required
            - Maximum 2 consecutive weeks without special approval
            - Blackout dates: December 15-31, end of fiscal quarters
            - Unused vacation expires at year end (no carryover)
            """,
            metadata={
                "source": "HR_Manual",
                "category": "Time_Off",
                "department": "HR",
                "keywords": ["vacation", "time off", "leave", "request", "approval"]
            }
        ),
        
        Document(
            page_content="""
            Benefits Enrollment:
            
            Open Enrollment Period: November 1-30 annually
            
            Available Benefits:
            - Health Insurance (3 plan options)
            - Dental Insurance
            - Vision Insurance
            - 401(k) with company match up to 6%
            - Life Insurance (1x salary, option to purchase additional)
            - Flexible Spending Account (FSA)
            
            New Employee Enrollment:
            - Must enroll within 30 days of start date
            - Contact HR within first week for benefits orientation
            - Default enrollment in basic health plan if no selection made
            
            Changes allowed only during open enrollment or qualifying life events.
            """,
            metadata={
                "source": "HR_Manual",
                "category": "Benefits",
                "department": "HR",
                "keywords": ["benefits", "enrollment", "health", "insurance", "401k"]
            }
        ),
        
        Document(
            page_content="""
            Performance Review Process:
            
            Annual Review Cycle:
            - Self-assessment due: January 15
            - Manager review due: February 15
            - HR review and calibration: March 1-15
            - Final reviews delivered: March 30
            
            Review Components:
            1. Goal achievement (40%)
            2. Core competencies (30%)
            3. Leadership/collaboration (20%)
            4. Professional development (10%)
            
            Rating Scale: Exceeds (5), Meets+ (4), Meets (3), Below (2), Unsatisfactory (1)
            
            Career development discussions included in all reviews.
            """,
            metadata={
                "source": "HR_Manual",
                "category": "Performance",
                "department": "HR",
                "keywords": ["performance", "review", "evaluation", "goals", "development"]
            }
        ),
        
        Document(
            page_content="""
            Remote Work Policy:
            
            Eligibility:
            - Employees with 6+ months tenure
            - Role suitable for remote work
            - Demonstrated performance standards
            - Manager approval required
            
            Requirements:
            - Dedicated workspace at home
            - Reliable internet connection (minimum 25 Mbps)
            - Available during core hours (9 AM - 3 PM local time)
            - Participate in weekly team meetings
            
            Equipment:
            - Company laptop provided
            - Monitor and accessories available upon request
            - IT support for home office setup
            
            Review remote work arrangements quarterly.
            """,
            metadata={
                "source": "HR_Manual",
                "category": "Work_Policy",
                "department": "HR",
                "keywords": ["remote work", "work from home", "policy", "equipment"]
            }
        ),
        
        # General Company Policies
        Document(
            page_content="""
            IT Security Guidelines:
            
            Password Requirements:
            - Minimum 8 characters
            - Include uppercase, lowercase, numbers, and symbols
            - Change every 90 days
            - No reusing last 12 passwords
            
            Data Protection:
            - Never share login credentials
            - Lock computer when away from desk
            - Use encrypted USB drives for sensitive data
            - Report suspicious emails to security@company.com
            
            Incident Reporting:
            - Report security incidents immediately
            - Contact IT security team: ext. 1111
            - Document what happened and when
            """,
            metadata={
                "source": "Security_Manual",
                "category": "Security",
                "department": "IT",
                "keywords": ["security", "password", "data protection", "incident"]
            }
        ),
        
        Document(
            page_content="""
            Expense Reimbursement Process:
            
            Eligible Expenses:
            - Business travel (flights, hotels, meals)
            - Client entertainment (with business purpose)
            - Professional development (conferences, training)
            - Office supplies for remote workers
            
            Process:
            1. Submit expense report within 30 days
            2. Include original receipts (digital copies accepted)
            3. Provide business justification for each expense
            4. Manager approval required for amounts over $100
            5. Finance processes reimbursements bi-weekly
            
            Reimbursement typically takes 7-10 business days after approval.
            """,
            metadata={
                "source": "Finance_Manual",
                "category": "Expenses",
                "department": "HR",
                "keywords": ["expense", "reimbursement", "travel", "receipts"]
            }
        )
    ]
    
    logger.info(f"Generated {len(documents)} sample knowledge base documents")
    return documents


def initialize_knowledge_base() -> bool:
    """
    Initialize the knowledge base by adding sample documents to the vector store.
    
    Returns:
        bool: True if initialization successful
    """
    try:
        logger.info("Initializing knowledge base")
        
        # Get vector store manager
        vector_store = get_vector_store_manager()
        
        if not vector_store._initialized:
            logger.error("Vector store not initialized")
            return False
        
        # Get sample documents
        documents = get_sample_knowledge_base()
        
        # Add documents to vector store
        success = vector_store.add_documents(documents)
        
        if success:
            logger.info("Knowledge base initialization completed successfully")
            
            # Log index statistics
            stats = vector_store.get_index_stats()
            logger.info(f"Vector store stats: {stats}")
            
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize knowledge base: {str(e)}")
        return False


def search_knowledge_base(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Search the knowledge base for relevant documents.
    
    Args:
        query: Search query
        k: Number of results to return
        
    Returns:
        List of dictionaries with document content and metadata
    """
    try:
        vector_store = get_vector_store_manager()
        
        if not vector_store._initialized:
            logger.error("Vector store not initialized")
            return []
        
        # Perform similarity search
        documents = vector_store.similarity_search(query, k=k)
        
        # Convert to dictionary format
        results = []
        for doc in documents:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        logger.debug(f"Knowledge base search returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Knowledge base search failed: {str(e)}")
        return []
