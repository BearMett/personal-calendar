from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """JWT token payload schema."""
    username: Optional[str] = None


class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    

class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8)
    

class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    

class UserInDB(UserBase):
    """User schema as stored in database."""
    id: int
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class User(UserInDB):
    """Schema for user response."""
    pass


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str