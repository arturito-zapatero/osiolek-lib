from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreateModel(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    surname: str
    auth_type: str  # "manual" or "cognito"
    address: Optional[str] = None   # <- default makes it optional
    phone: Optional[str] = None     # <- default makes it optional



class UserUpdateModel(BaseModel):
    user_id: str
    first_name: Optional[str] = None
    surname: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


class GetItemsQueryModel(BaseModel):
    query: str = Field(..., min_length=1)
    cutoff: int = Field(70, ge=0, le=100)
    limit: int = Field(25, ge=1, le=100)
