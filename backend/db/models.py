from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID

class PipelineRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID] = None
    mode: str
    status: str = "running"
    current_stage: Optional[str] = None
    stage_progress: Dict[str, Any] = Field(default_factory=dict)
    review_counts: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class RawReview(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID] = None
    run_id: UUID
    source: str
    raw_text: str
    cleaned_text: Optional[str] = None
    rating: Optional[int] = None
    review_date: Optional[date] = None
    source_url: Optional[str] = None
    content_hash: Optional[str] = None
    word_count: Optional[int] = None
    language: str = "en"
    signal_score: Optional[float] = None
    signal_rationale: Optional[str] = None
    status: str = "pending"
    created_at: Optional[datetime] = None

class ReviewChunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID] = None
    review_id: UUID
    run_id: UUID
    chunk_text: str
    chunk_index: int
    word_count: Optional[int] = None

class ChunkAnnotation(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID] = None
    chunk_id: UUID
    run_id: UUID
    decision_evidence_type: Optional[str] = None
    decision_driver: Optional[str] = None
    purchase_context: Optional[str] = None
    categories_mentioned: Optional[List[str]] = None
    evidence_quote: Optional[str] = None
    other_signal: Optional[str] = None
    inferred_segment: Optional[str] = None
    confidence: Optional[str] = None
    annotation_model: Optional[str] = None
    annotation_failed: bool = False

class SynthesizedInsight(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID] = None
    run_id: UUID
    insight_type: str
    cluster_key: str
    title: str
    description: str
    hypothesis: str
    evidence_chunk_ids: Optional[List[UUID]] = None
    evidence_quotes: Optional[List[Dict[str, Any]]] = None
    evidence_count: int
    confidence: str
    confidence_rationale: str
    opportunity_score: Optional[int] = None
    com_b_interpretation: Optional[str] = None
    intervention_hint: Optional[str] = None
    has_contradiction: bool = False
    contradiction_description: Optional[str] = None
    display_order: Optional[int] = None

class Opportunity(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID] = None
    run_id: UUID
    title: str
    problem_statement: str
    evidence_summary: str
    product_direction: str
    com_b_lever: Optional[str] = None
    parent_insight_ids: Optional[List[UUID]] = None
    supporting_evidence_count: Optional[int] = None
    priority_rank: Optional[int] = None
