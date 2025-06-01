from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from app.schemas.user import UserRole


class UserModel:
    """User model for MongoDB operations"""

    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
        rate_limit_reset: Optional[datetime] = None,
        _id: Optional[ObjectId] = None,
    ):
        self._id = _id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.last_login = last_login
        self.rate_limit_reset = rate_limit_reset

    def to_dict(self) -> dict:
        """Convert model to dictionary for MongoDB"""
        data = {
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "rate_limit_reset": self.rate_limit_reset,
        }

        # Only include _id if it's not None (for updates)
        if self._id is not None:
            data["_id"] = self._id

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "UserModel":
        """Create model from MongoDB document"""
        return cls(
            _id=data.get("_id"),
            username=data["username"],
            email=data["email"],
            password_hash=data["password_hash"],
            role=UserRole(data["role"]),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_login=data.get("last_login"),
            rate_limit_reset=data.get("rate_limit_reset"),
        )
