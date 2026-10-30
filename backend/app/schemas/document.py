from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DocumentSourceInfo(BaseModel):
    filename: str
    file_type: str
    file_size: int
    page_count: int

class ValidationIssue(BaseModel):
    issue_type: str
    message: str
    field: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None

class ValidationResult(BaseModel):
    status: str = "completed"  # valid, review_needed, calculation_mismatch, completed, failed
    issues: List[ValidationIssue] = Field(default_factory=list)
    confidence_score: Optional[float] = 1.0

class ExtractionMetadata(BaseModel):
    pdf_method: Optional[str] = None
    ocr_engine: Optional[str] = None
    model: Optional[str] = None
    llm_provider: Optional[str] = None
    extraction_mode: Optional[str] = None
    cross_verification_status: Optional[str] = None
    audit_summary: Optional[str] = None

class TableData(BaseModel):
    title: Optional[str] = None
    headers: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)

class KeyValuePair(BaseModel):
    key: str
    value: Any

class DocumentContent(BaseModel):
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    tables: List[TableData] = Field(default_factory=list)
    key_value_pairs: List[KeyValuePair] = Field(default_factory=list)

class DocumentDetailResponse(BaseModel):
    id: str
    document_id: str
    filename: str
    file_type: str
    document_type: str
    status: str
    source: DocumentSourceInfo
    metadata: Dict[str, Any] = Field(default_factory=dict)
    content: DocumentContent
    raw_text: str
    normalized_json: Dict[str, Any] = Field(default_factory=dict)
    validation: ValidationResult
    extraction_metadata: ExtractionMetadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DocumentStatusResponse(BaseModel):
    id: str
    document_id: str
    status: str
    document_type: str
    message: Optional[str] = None

class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total: int
    page: int
    limit: int

class RAGQueryRequest(BaseModel):
    query: str

class RAGCitation(BaseModel):
    page: int
    content: str

class RAGQueryResponse(BaseModel):
    answer: str
    citations: List[RAGCitation] = Field(default_factory=list)

