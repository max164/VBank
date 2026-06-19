from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    username: str = Field(min_length=3, max_length=64)
    phone_number: str = Field(min_length=5, max_length=32)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=16, max_length=512)
