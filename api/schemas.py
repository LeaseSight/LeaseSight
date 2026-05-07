from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class EntityStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DISCARDED = "DISCARDED"

class MigrationEntity(BaseModel):
    id: Optional[int] = None
    file_name: str
    category: str
    value: str
    confidence: float
    status: EntityStatus = EntityStatus.PENDING

class MigrationTask(BaseModel):
    task_id: str
    status: str
    total_files: int
    processed_files: int
    findings: List[MigrationEntity] = []

class ResearchAuditRequest(BaseModel):
    file_name: str

class Coordinate(BaseModel):
    page: int
    x: float
    y: float
    width: float
    height: float

class Finding(BaseModel):
    label: str
    value: str
    explanation: str
    coordinates: Optional[Coordinate] = None

class ResearchScorecard(BaseModel):
    originality: Finding
    technical_rigor: Finding
    citation_validity: Finding
    narrative_clarity: Finding
    overall_score: int
    missing_citations: List[str]

class AuthKeys(BaseModel):
    openai_key: Optional[str] = None
    pinecone_key: Optional[str] = None
    azure_key: Optional[str] = None
    azure_endpoint: Optional[str] = None
