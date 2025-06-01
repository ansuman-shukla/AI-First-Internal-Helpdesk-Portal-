from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
from app.schemas.user import (
    UserLoginSchema,
    TokenSchema,
    UserSchema,
    UserCreateSchema,
    UserRegistrationResponse,
)
from app.services.auth_service import (
    verify_password,
    create_access_token,
    get_token_data,
)
from app.services.user_service import user_service
from app.core.database import get_database
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current user from JWT token"""
    token_data = get_token_data(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data


@router.post("/register", response_model=UserRegistrationResponse)
async def register(user_data: UserCreateSchema):
    """Register a new user"""
    try:
        # Create user in database
        user_model = await user_service.create_user(user_data)

        logger.info(f"User registered successfully: {user_data.username}")

        return UserRegistrationResponse(
            message="User registered successfully",
            username=user_model.username,
            email=user_model.email,
            role=user_model.role,
            created_at=user_model.created_at,
        )

    except ValueError as e:
        # Handle duplicate username/email
        logger.warning(f"Registration failed for {user_data.username}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Handle other errors
        logger.error(f"Registration error for {user_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )


@router.post("/login", response_model=TokenSchema)
async def login(user_credentials: UserLoginSchema):
    """Authenticate user and return JWT token"""
    try:
        # Get user from database
        user = await user_service.get_user_by_username(user_credentials.username)

        if not user:
            logger.warning(
                f"Login attempt with non-existent username: {user_credentials.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not verify_password(user_credentials.password, user.password_hash):
            logger.warning(
                f"Login attempt with incorrect password for user: {user_credentials.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            logger.warning(
                f"Login attempt for inactive user: {user_credentials.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login
        await user_service.update_last_login(user.username)

        # Create token
        token_data = {
            "sub": user.username,
            "user_id": str(user._id),
            "role": user.role.value,
        }
        access_token = create_access_token(data=token_data)

        logger.info(f"User logged in successfully: {user_credentials.username}")
        return TokenSchema(access_token=access_token)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Login error for {user_credentials.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        )


@router.post("/logout")
async def logout(_: dict = Depends(get_current_user)):
    """Logout user (invalidate token)"""
    # In a simple JWT implementation, logout is handled client-side
    # For more security, you could maintain a blacklist of tokens
    return {"message": "Logout successful"}


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": current_user["username"],
        "user_id": current_user["user_id"],
        "role": current_user["role"],
    }
