from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
