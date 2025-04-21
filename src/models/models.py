from pydantic import BaseModel

class RequestBody(BaseModel):
    message: str
    userId: str
    threadId: str