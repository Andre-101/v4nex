from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str = "USER"
    bridge_limit: int = 1
    is_active: bool = True


class CurrentUserResponse(UserResponse):
    bridges_used: int


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
