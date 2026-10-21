from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    token: str
    email: str


class UserOut(BaseModel):
    id: int
    email: str


class ThreadCreate(BaseModel):
    title: str | None = None


class ThreadOut(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    meta: str | None = None

    class Config:
        from_attributes = True


class StreamIn(BaseModel):
    message: str


class MemoryCreate(BaseModel):
    content: str
    kind: str = "fact"


class MemoryOut(BaseModel):
    id: int
    kind: str
    content: str

    class Config:
        from_attributes = True
