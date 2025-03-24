from pydantic import BaseModel

class UrlCreate(BaseModel):
    orig_url: str