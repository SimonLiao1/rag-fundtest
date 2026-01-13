from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import uuid

# --- Phase 1: Knowledge Extraction Models ---

class KnowledgePoint(BaseModel):
    """Structured knowledge extracted from a parent chunk"""
    summary: str = Field(..., description="Concise summary of the knowledge point")
    category: str = Field(..., description="Category: Definition, Rule, Process, Prohibition, Classification")
    key_facts: List[str] = Field(..., description="List of atomic facts derived from the text")
    distractor_ideas: List[str] = Field(..., description="Ideas for generating plausible distractors")
    source_chunk_id: str = Field(..., description="ID of the source parent chunk")

# --- Phase 2: Question Generation Models ---

class QuestionOptions(BaseModel):
    """The four options for a multiple choice question"""
    A: str
    B: str
    C: str
    D: str

class QuestionCandidate(BaseModel):
    """A generated question before verification"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str
    options: QuestionOptions
    correct_answer: str = Field(..., pattern="^[A-D]$")
    explanation: Optional[str] = None
    question_type: str = Field(..., description="Fact, Negative, or Scenario")
    knowledge_point: KnowledgePoint

# --- Phase 3: Final Verified Question Model ---

class GeneratedQuestion(BaseModel):
    """Final verified question ready for storage"""
    id: str
    question: str
    options: Dict[str, str]
    answer: str
    explanation: str
    source_chunk_id: str
    source_metadata: Dict
    question_type: str
    verification_score: float = Field(..., ge=0.0, le=1.0)
    status: str = "Verified"
    created_at: str

