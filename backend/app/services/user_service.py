from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from app.core.database import get_database
from app.models.user import UserModel
from app.schemas.user import UserCreateSchema
from app.services.auth_service import hash_password
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service for user database operations"""

    def __init__(self):
        self.collection_name = "users"

    async def create_user(self, user_data: UserCreateSchema) -> UserModel:
        """
        Create a new user in the database

        Args:
            user_data: User creation data

        Returns:
            UserModel: Created user

        Raises:
            ValueError: If username or email already exists
            Exception: For other database errors
        """
        db = get_database()
        if db is None:
            raise Exception("Database connection not available")

        collection = db[self.collection_name]

        # Check if username already exists
        existing_user = await collection.find_one({"username": user_data.username})
        if existing_user:
            logger.warning(
                f"Attempt to create user with existing username: {user_data.username}"
            )
            raise ValueError("Username already exists")

        # Check if email already exists
        existing_email = await collection.find_one({"email": user_data.email})
        if existing_email:
            logger.warning(
                f"Attempt to create user with existing email: {user_data.email}"
            )
            raise ValueError("Email already exists")

        # Create user model
        user_model = UserModel(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role=user_data.role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        try:
            # Insert user into database
            user_dict = user_model.to_dict()
            result = await collection.insert_one(user_dict)
            user_model._id = result.inserted_id

            logger.info(
                f"Successfully created user: {user_data.username} with role: {user_data.role}"
            )
            return user_model

        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error creating user {user_data.username}: {e}")
            raise ValueError("Username or email already exists")
        except Exception as e:
            logger.error(f"Error creating user {user_data.username}: {e}")
            raise Exception(f"Failed to create user: {str(e)}")

    async def get_user_by_username(self, username: str) -> Optional[UserModel]:
        """
        Get user by username

        Args:
            username: Username to search for

        Returns:
            UserModel or None if not found
        """
        db = get_database()
        if db is None:
            return None

        collection = db[self.collection_name]
        user_doc = await collection.find_one({"username": username})

        if user_doc:
            return UserModel.from_dict(user_doc)
        return None

    async def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """
        Get user by email

        Args:
            email: Email to search for

        Returns:
            UserModel or None if not found
        """
        db = get_database()
        if db is None:
            return None

        collection = db[self.collection_name]
        user_doc = await collection.find_one({"email": email})

        if user_doc:
            return UserModel.from_dict(user_doc)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        """
        Get user by ID

        Args:
            user_id: User ID to search for

        Returns:
            UserModel or None if not found
        """
        db = get_database()
        if db is None:
            return None

        collection = db[self.collection_name]
        try:
            user_doc = await collection.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                return UserModel.from_dict(user_doc)
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")

        return None

    async def update_last_login(self, username: str) -> bool:
        """
        Update user's last login timestamp

        Args:
            username: Username to update

        Returns:
            bool: True if updated successfully
        """
        db = get_database()
        if db is None:
            return False

        collection = db[self.collection_name]
        try:
            result = await collection.update_one(
                {"username": username},
                {"$set": {"last_login": datetime.now(timezone.utc)}},
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating last login for {username}: {e}")
            return False

    async def get_users_by_role(self, role: str) -> list[UserModel]:
        """
        Get all users with a specific role

        Args:
            role: User role to search for (e.g., 'hr_agent', 'it_agent', 'admin')

        Returns:
            List of UserModel objects with the specified role
        """
        db = get_database()
        if db is None:
            return []

        collection = db[self.collection_name]
        try:
            cursor = collection.find({
                "role": role,
                "is_active": True
            })

            users = []
            async for user_doc in cursor:
                users.append(UserModel.from_dict(user_doc))

            logger.debug(f"Found {len(users)} active users with role {role}")
            return users

        except Exception as e:
            logger.error(f"Error getting users by role {role}: {e}")
            return []

    async def get_users_by_roles(self, roles: list[str]) -> list[UserModel]:
        """
        Get all users with any of the specified roles

        Args:
            roles: List of user roles to search for

        Returns:
            List of UserModel objects with any of the specified roles
        """
        db = get_database()
        if db is None:
            return []

        collection = db[self.collection_name]
        try:
            cursor = collection.find({
                "role": {"$in": roles},
                "is_active": True
            })

            users = []
            async for user_doc in cursor:
                users.append(UserModel.from_dict(user_doc))

            logger.debug(f"Found {len(users)} active users with roles {roles}")
            return users

        except Exception as e:
            logger.error(f"Error getting users by roles {roles}: {e}")
            return []


# Global user service instance
user_service = UserService()
