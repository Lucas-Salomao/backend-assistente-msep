from pydantic import BaseModel

class RequestBody(BaseModel):
    message: str
    userId: str
    threadId: str
    # latitude: str
    # longitude: str
    
class TTSRequestBody(BaseModel):
    message: str