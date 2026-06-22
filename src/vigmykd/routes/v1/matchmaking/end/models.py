from pydantic import BaseModel


class GameOverQuery(BaseModel):
    payload: str
