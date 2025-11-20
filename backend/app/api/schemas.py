from typing import Optional

from pydantic import BaseModel, Field


# User schemas
class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=1)


class UserResponse(UserBase):
    id: int
    
    class Config:
        from_attributes = True


# Authentication schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str


# News schemas
class NewsArticleResponse(BaseModel):
    id: int
    url: str
    title: str
    time: str
    content: str
    summary: str
    reason: str
    upvotes: int = 0
    is_upvoted: bool = False
    
    class Config:
        from_attributes = True


# Request schemas
class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


class NewsSummaryRequest(BaseModel):
    content: str = Field(..., min_length=1)


class NewsSummaryResponse(BaseModel):
    summary: str
    reason: str


class UpvoteResponse(BaseModel):
    message: str
