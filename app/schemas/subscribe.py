from pydantic import BaseModel
from typing import List


class SubscribeRequest(BaseModel):
    keywords: List[str]
