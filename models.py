"""
Pydantic Data Schemas and Validation Models for PotionLabs Recruitment Engine
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ApplicantCreate(BaseModel):
    full_name: str = Field(..., min_length=2, description="Candidate full name")
    email: str = Field(..., min_length=5, description="Candidate email address")
    phone: Optional[str] = Field(None, description="Phone number")
    city: Optional[str] = Field("Kolkata", description="Candidate location/city")
    linkedin_portfolio: Optional[str] = Field(None, description="LinkedIn / GitHub URL")
    source_attribution: Optional[str] = Field("PotionLabs Careers Page", description="Referral or discovery source")
    read_first_note: Optional[str] = Field(None, max_length=500, description="Anything you want us to read first (0/500)")
    resume_text: str = Field(..., min_length=50, description="Extracted resume text or technical submission details")

class EvaluationResult(BaseModel):
    overall_score: int
    tool_calling_score: int
    backend_python_score: int
    sql_score: int
    worker_patterns_score: int
    project_depth_score: int
    passed_hard_constraints: bool
    disqualification_reason: Optional[str] = None
    reasoning_summary: str
    raw_signals: Dict[str, Any]

class ReviewActionRequest(BaseModel):
    action: str = Field(..., pattern="^(accept|reject|double_check_promote|restore)$")
    reviewer_name: str = Field("PotionLabs Recruiter", description="Name of the reviewing engineer")
    notes: Optional[str] = None

class CandidateSummary(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str]
    city: Optional[str]
    linkedin_portfolio: Optional[str]
    read_first_note: Optional[str]
    status: str
    created_at: str
    evaluation: Optional[EvaluationResult] = None
