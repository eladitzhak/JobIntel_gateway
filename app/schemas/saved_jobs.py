from pydantic import BaseModel


class SaveJobResponse(BaseModel):
    message: str
