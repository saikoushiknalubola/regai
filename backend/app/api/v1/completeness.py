from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional
import logging

from app.modules.completeness.engine import CompletenessEngine, DocumentComparisonEngine
from app.utils.document_parser import extract_text_from_upload

logger = logging.getLogger(__name__)
router = APIRouter()

_completeness_engine: Optional[CompletenessEngine] = None
_comparison_engine: Optional[DocumentComparisonEngine] = None


def get_completeness() -> CompletenessEngine:
    global _completeness_engine
    if _completeness_engine is None:
        _completeness_engine = CompletenessEngine()
    return _completeness_engine


def get_comparison() -> DocumentComparisonEngine:
    global _comparison_engine
    if _comparison_engine is None:
        _comparison_engine = DocumentComparisonEngine()
    return _comparison_engine


class TextCompletenessRequest(BaseModel):
    text: str
    document_type: str
    document_id: Optional[str] = "doc_001"


class TextComparisonRequest(BaseModel):
    text_a: str
    text_b: str
    doc_a_id: Optional[str] = "version_A"
    doc_b_id: Optional[str] = "version_B"


@router.post("/check")
async def check_completeness(request: TextCompletenessRequest):
    """Check completeness of a document against CDSCO checklist schema."""
    engine = get_completeness()
    report = engine.check_completeness(
        request.text, request.document_type, request.document_id
    )
    return {
        "document_id": report.document_id,
        "document_type": report.document_type,
        "overall_score": report.overall_score,
        "overall_percent": round(report.overall_score * 100, 1),
        "verdict": report.verdict,
        "section_scores": report.section_scores,
        "missing_mandatory": report.missing_mandatory,
        "missing_recommended": report.missing_recommended,
        "inconsistencies": report.inconsistencies,
        "field_details": [
            {
                "field": r.field_name,
                "section": r.section,
                "status": r.status,
                "value": r.found_value,
                "issue": r.issue,
                "severity": r.severity,
            }
            for r in report.field_results
        ],
        "processing_time_ms": report.processing_time_ms,
    }


@router.post("/check/document")
async def check_completeness_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
):
    """Check completeness of an uploaded document."""
    content = await file.read()
    ext = file.filename.split(".")[-1].lower() if file.filename else "txt"
    text = await extract_text_from_upload(content, ext)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from document")

    engine = get_completeness()
    report = engine.check_completeness(text, document_type, file.filename)

    return {
        "filename": file.filename,
        "overall_score": report.overall_score,
        "verdict": report.verdict,
        "missing_mandatory": report.missing_mandatory,
        "inconsistencies": report.inconsistencies,
        "processing_time_ms": report.processing_time_ms,
    }


@router.post("/compare")
async def compare_documents(request: TextComparisonRequest):
    """Compare two document versions using semantic diff."""
    if not request.text_a.strip() or not request.text_b.strip():
        raise HTTPException(status_code=400, detail="Both document texts must be provided")

    engine = get_comparison()
    report = engine.compare(
        request.text_a, request.text_b,
        request.doc_a_id, request.doc_b_id
    )

    return {
        "document_a_id": report.document_a_id,
        "document_b_id": report.document_b_id,
        "total_changes": report.total_changes,
        "critical_changes": report.critical_changes,
        "major_changes": report.major_changes,
        "minor_changes": report.minor_changes,
        "cosmetic_changes": report.cosmetic_changes,
        "overall_similarity": report.overall_similarity,
        "summary": report.summary,
        "diff_report": [
            {
                "chunk_id": c.chunk_id,
                "section": c.section,
                "change_type": c.change_type,
                "severity": c.severity,
                "original": c.original_text[:500],
                "revised": c.revised_text[:500],
                "semantic_distance": c.semantic_distance,
                "explanation": c.explanation,
            }
            for c in report.diff_chunks
        ],
        "processing_time_ms": report.processing_time_ms,
    }


@router.post("/compare/documents")
async def compare_uploaded_documents(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    """Compare two uploaded document files."""
    content_a = await file_a.read()
    content_b = await file_b.read()

    ext_a = file_a.filename.split(".")[-1].lower() if file_a.filename else "txt"
    ext_b = file_b.filename.split(".")[-1].lower() if file_b.filename else "txt"

    text_a = await extract_text_from_upload(content_a, ext_a)
    text_b = await extract_text_from_upload(content_b, ext_b)

    if not text_a.strip() or not text_b.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from one or both files")

    engine = get_comparison()
    report = engine.compare(text_a, text_b, file_a.filename, file_b.filename)

    return {
        "file_a": file_a.filename,
        "file_b": file_b.filename,
        "total_changes": report.total_changes,
        "critical_changes": report.critical_changes,
        "major_changes": report.major_changes,
        "summary": report.summary,
        "processing_time_ms": report.processing_time_ms,
    }
