from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class IssueLabel(BaseModel):
    """Represents a GitHub issue label"""
    name: str
    color: str
    description: Optional[str] = None


class SimilarIssue(BaseModel):
    """Represents a similar historical issue"""
    number: int
    title: str
    url: str
    state: str
    similarity_score: float
    resolution_summary: Optional[str] = None
    closed_at: Optional[datetime] = None


class RootCauseCommit(BaseModel):
    """Represents a potential root cause commit"""
    sha: str
    message: str
    author: str
    date: datetime
    url: str
    files_changed: List[str]
    confidence_score: float


class ComponentCategory(BaseModel):
    """ROCm component categorization"""
    component: str
    confidence: float
    reasoning: str


class IssueAnalysis(BaseModel):
    """AI-powered analysis of an issue"""
    issue_number: int
    title: str
    body: str
    created_at: datetime
    state: str
    url: str
    labels: List[IssueLabel]

    # AI Analysis Results
    component_categories: List[ComponentCategory]
    similar_issues: List[SimilarIssue]
    root_cause_commits: List[RootCauseCommit]
    suggested_labels: List[str]
    fix_suggestions: List[str]
    analysis_summary: str
    severity: str  # "critical", "high", "medium", "low"


class AnalysisRequest(BaseModel):
    """Request to analyze specific issues"""
    issue_numbers: Optional[List[int]] = None
    analyze_all_open: bool = False
    limit: int = 10


class AnalysisResponse(BaseModel):
    """Response containing analyzed issues"""
    analyses: List[IssueAnalysis]
    total_analyzed: int
    timestamp: datetime
