from pydantic import BaseModel


class ConfirmQuery(BaseModel):
    code: str
