from pydantic import BaseModel
from typing import Union

class UrlCreate(BaseModel):
    orig_url: str
    alias: Union[str, None] = None

class UrlChange(BaseModel):
    short_code: str
    alias: Union[str, None] = None