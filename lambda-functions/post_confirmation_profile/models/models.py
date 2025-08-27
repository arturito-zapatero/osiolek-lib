from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreateModel(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    surname: str
    auth_type: str  # "manual" or "cognito"
    address: Optional[str]
    phone: Optional[str]



class UserUpdateModel(BaseModel):
    user_id: str
    first_name: Optional[str]
    surname: Optional[str]
    address: Optional[str]
    phone: Optional[str]


class GetItemsQueryModel(BaseModel):
    query: str = Field(..., min_length=1)
    cutoff: int = Field(70, ge=0, le=100)
    limit: int = Field(25, ge=1, le=100)
