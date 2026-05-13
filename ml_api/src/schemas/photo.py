from pydantic import BaseModel
from typing import Optional


class Photo(BaseModel):
    base64: str
    label: Optional[str] = None