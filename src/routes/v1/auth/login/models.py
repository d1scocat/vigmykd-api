from pydantic import BaseModel


class LoginQuery(BaseModel):
    login: str
    password: str
