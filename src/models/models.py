from typing import List, Optional
from pydantic import BaseModel, Field

class RequestBody(BaseModel):
    message: str
    userId: str
    threadId: str
    
class PlanGenerationBody(BaseModel):
    userId: str
    threadId: str
    docente: str
    escola: str
    planoCurso: str
    curso: str
    uc: str
    capacidadesTecnicas: Optional[List[str]] = Field(default_factory=list)
    capacidadesSocioemocionais: Optional[List[str]] = Field(default_factory=list)
    estraategia: str
    tematica: Optional[str] = ""

class PlanGenerationResponse(BaseModel):
    userId: str
    threadId: str
    plan_markdown: str