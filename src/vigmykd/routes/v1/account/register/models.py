from pydantic import BaseModel, Field, ConfigDict


class RegisterQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nickname: str
    email: str
    password: str
    agree_with_policies: bool = Field(alias="agree-with-policies")


class ConfirmQuery(BaseModel):
    code: str
