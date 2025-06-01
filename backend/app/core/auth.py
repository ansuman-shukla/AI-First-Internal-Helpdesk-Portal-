"""
Authentication utilities for the helpdesk system.

This module provides centralized authentication and authorization functions
that can be used across different routers.
"""

import logging
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import get_token_data
from app.models.user import UserModel

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Get current user from JWT token
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        dict: User data from token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    logger.debug("Extracting user from JWT token")
    
    token_data = get_token_data(credentials.credentials)
    if token_data is None:
        logger.warning("Invalid authentication credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"Successfully authenticated user: {token_data['username']}")
    return token_data


async def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Verify that the current user has admin role
    
    Args:
        current_user: Current authenticated user from get_current_user
        
    Returns:
        dict: User information if authorized
        
    Raises:
        HTTPException: If user is not an admin
    """
    logger.debug(f"Checking admin role for user: {current_user['username']}")
    
    if current_user["role"] != "admin":
        logger.warning(f"Non-admin user {current_user['username']} attempted to access admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    logger.debug(f"Admin access granted for user: {current_user['username']}")
    return current_user


async def require_agent(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Verify that the current user has agent role (IT or HR agent)
    
    Args:
        current_user: Current authenticated user from get_current_user
        
    Returns:
        dict: User information if authorized
        
    Raises:
        HTTPException: If user is not an agent
    """
    logger.debug(f"Checking agent role for user: {current_user['username']}")
    
    if current_user["role"] not in ["it_agent", "hr_agent"]:
        logger.warning(f"Non-agent user {current_user['username']} attempted to access agent endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Agent role required."
        )
    
    logger.debug(f"Agent access granted for user: {current_user['username']} ({current_user['role']})")
    return current_user
