from pydantic import BaseModel, Field


class Account(BaseModel):
    id: int = Field(..., description="ID аккаунта")
    login: str = Field(..., description="Логин")
    is_blocked: bool = Field(..., description="Заблокирован")


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
