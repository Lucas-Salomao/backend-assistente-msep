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
    estrategia: str
    tematica: Optional[str] = ""

class PlanGenerationResponse(BaseModel):
    userId: str
    threadId: str
    plan_markdown: str
    
# Novos modelos para os endpoints
class GetThreadsRequest(BaseModel):
    userId: str = Field(..., alias="userId")

class GetThreadsResponse(BaseModel):
    userId: str
    all_threads: List[str]

class ChatHistoryRequest(BaseModel):
    threadId: str = Field(..., alias="threadId")

class MessageInfo(BaseModel):
    type: str
    content: str
    additional_info: dict

class ChatHistoryResponse(BaseModel):
    threadId: str
    messages: List[MessageInfo]
    title: Optional[str] = None  # Adiciona o campo title como opcional
    
class ThreadInfo(BaseModel):
    thread_id: str
    title: str | None

class GetThreadsWithTitlesRequest(BaseModel):
    userId: str

class GetThreadsWithTitlesResponse(BaseModel):
    userId: str
    threads: List[ThreadInfo]
    
class ModelConfigRequest(BaseModel):
    temperature: float = Field(..., ge=0.0, le=2.0)  # Entre 0.0 e 1.0
    top_p: float = Field(..., ge=0.0, le=1.0)       # Entre 0.0 e 1.0
    user_id: str
    
class UCCapabilities(BaseModel):
    CapacidadesTecnicas_list: List[str] = Field(default_factory=list)
    CapacidadesSocioemocionais_list: List[str] = Field(default_factory=list)

class UCEntry(BaseModel):
    nomeUC: str
    capacidades: UCCapabilities

class FullPlanDetailsResponse(BaseModel):
    stored_markdown_id: str
    user_id: str
    thread_id: str # O thread_id da conversa original
    original_pdf_filename: Optional[str] = None
    nomeCurso: Optional[str] = None
    unidadesCurriculares: List[UCEntry] = Field(default_factory=list)

class HorarioAula(BaseModel): # Novo modelo para representar os horários
    dia: str
    horaInicio: str
    horaFim: str
    
# Corpo da requisição para gerar o plano de ensino, usando o ID do markdown armazenado
class PlanGenerationBodyWithStoredId(BaseModel):
    stored_markdown_id: str
    user_id: str
    thread_id: str
    docente: str
    escola: str
    curso: str
    turma: str
    uc: str
    capacidadesTecnicas: Optional[List[str]] = Field(default_factory=list)
    capacidadesSocioemocionais: Optional[List[str]] = Field(default_factory=list)
    estrategia: str
    tematica: Optional[str] = ""
    horarios: List[HorarioAula] = Field(default_factory=list)