from pydantic import BaseModel, Field, ConfigDict


class ChangePasswordQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    old: str
    new: str
    invalidate_sessions: bool = Field(alias="invalidate-sessions")
