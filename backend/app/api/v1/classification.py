from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.modules.classification.engine import ClassificationEngine, SeverityLevel

logger = logging.getLogger(__name__)
router = APIRouter()

_engine: Optional[ClassificationEngine] = None


def get_engine() -> ClassificationEngine:
    global _engine
    if _engine is None:
        _engine = ClassificationEngine()
    return _engine


class ClassifyRequest(BaseModel):
    text: str
    case_id: Optional[str] = "unknown"


class DuplicateCheckRequest(BaseModel):
    text: str
    case_id: str
    register_case: bool = True


class PriorityQueueRequest(BaseModel):
    cases: list[dict]


@router.post("/severity")
async def classify_severity(request: ClassifyRequest):
    """Classify SAE severity: death / disability / hospitalisation / others."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    engine = get_engine()
    result = engine.classify_severity(request.text, request.case_id)

    return {
        "case_id": result.case_id,
        "severity": result.predicted_severity,
        "confidence": result.confidence,
        "evidence": result.evidence,
        "rule_signals": result.rule_based_signals,
        "model_used": result.model_used,
    }


@router.post("/duplicate")
async def check_duplicate(request: DuplicateCheckRequest):
    """Check if a case is a duplicate of a previously registered case."""
    engine = get_engine()

    if request.register_case:
        engine._case_registry[request.case_id] = {
            "text": request.text,
            "severity": "others",
            "classified_at": "now"
        }

    result = engine.check_duplicate(request.text, request.case_id)

    return {
        "case_id": result.case_id,
        "is_duplicate": result.is_duplicate,
        "duplicate_of": result.duplicate_of,
        "similarity_score": result.similarity_score,
        "matching_fields": result.matching_fields,
        "method": result.method,
        "action": (
            f"Merge with case {result.duplicate_of} or verify with reporter"
            if result.is_duplicate else "Proceed as new case"
        ),
    }


@router.post("/queue")
async def build_priority_queue(request: PriorityQueueRequest):
    """
    Build prioritised review queue from list of cases.

    Each case dict should include:
      case_id, severity, completeness_score, submission_age_days,
      document_type (optional), assigned_reviewer (optional),
      is_duplicate (optional), duplicate_of (optional)
    """
    if not request.cases:
        raise HTTPException(status_code=400, detail="Cases list cannot be empty")

    engine = get_engine()
    queue = engine.build_priority_queue(request.cases)

    return {
        "total_cases": len(queue),
        "death_cases": sum(1 for q in queue if q.severity == SeverityLevel.DEATH),
        "disability_cases": sum(1 for q in queue if q.severity == SeverityLevel.DISABILITY),
        "hospitalisation_cases": sum(1 for q in queue if q.severity == SeverityLevel.HOSPITALISATION),
        "other_cases": sum(1 for q in queue if q.severity == SeverityLevel.OTHERS),
        "queue": [
            {
                "rank": i + 1,
                "case_id": item.case_id,
                "document_type": item.document_type,
                "severity": item.severity,
                "priority_score": item.priority_score,
                "completeness_score": item.completeness_score,
                "submission_age_days": item.submission_age_days,
                "assigned_reviewer": item.assigned_reviewer,
                "flags": item.flags,
            }
            for i, item in enumerate(queue)
        ]
    }
