from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    IT_AGENT = "it_agent"
    HR_AGENT = "hr_agent"
    ADMIN = "admin"


class UserLoginSchema(BaseModel):
    username: str
    password: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER


class UserSchema(BaseModel):
    id: Optional[str] = None
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDB(UserSchema):
    password_hash: str


class UserRegistrationResponse(BaseModel):
    message: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
