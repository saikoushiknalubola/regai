from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional
import tempfile
import os
import logging

from app.core.config import settings
from app.modules.summarisation.engine import SummarisationEngine, DocumentType
from app.utils.document_parser import extract_text_from_upload

logger = logging.getLogger(__name__)
router = APIRouter()

_engine: Optional[SummarisationEngine] = None


def get_engine() -> SummarisationEngine:
    global _engine
    if _engine is None:
        _engine = SummarisationEngine(
            gemini_api_key=settings.GEMINI_API_KEY,
            gemini_model=settings.GEMINI_MODEL,
        )
    return _engine


class TextSummariseRequest(BaseModel):
    text: str
    document_type: DocumentType
    application_type: Optional[str] = "default"


@router.post("/text")
async def summarise_text(request: TextSummariseRequest):
    """Summarise text by document type (sugam / sae / meeting)."""
    engine = get_engine()

    if request.document_type == DocumentType.SUGAM:
        result = engine.summarise_sugam(request.text, request.application_type or "default")
        return {
            "document_type": "sugam",
            "application_number": result.application_number,
            "applicant_name": result.applicant_name,
            "drug_name": result.drug_name,
            "application_type": result.application_type,
            "completeness_score": result.completeness_score,
            "missing_mandatory_fields": result.missing_mandatory_fields,
            "reviewer_notes": result.reviewer_notes,
            "summary": result.raw_summary,
            "present_fields": result.present_fields,
        }

    elif request.document_type == DocumentType.SAE:
        result = engine.summarise_sae(request.text)
        return {
            "document_type": "sae",
            "case_id": result.case_id,
            "patient_demographics": result.patient_demographics,
            "suspect_drug": result.suspect_drug,
            "dose_route": result.dose_route,
            "adverse_event": result.adverse_event,
            "event_onset_date": result.event_onset_date,
            "outcome": result.outcome,
            "causality_assessment": result.causality_assessment,
            "seriousness_criteria": result.seriousness_criteria,
            "reporter_type": result.reporter_type,
            "action_taken": result.action_taken,
            "rechallenge": result.rechallenge,
            "structured_narrative": result.structured_narrative,
            "key_flags": result.key_flags,
        }

    elif request.document_type == DocumentType.MEETING:
        result = engine.summarise_meeting(request.text)
        return {
            "document_type": "meeting",
            "meeting_date": result.meeting_date,
            "participants": result.participants,
            "agenda_items": result.agenda_items,
            "key_decisions": result.key_decisions,
            "action_items": result.action_items,
            "next_steps": result.next_steps,
            "summary": result.full_summary,
            "transcript_length_words": result.transcript_length_words,
        }

    raise HTTPException(status_code=400, detail=f"Unknown document type: {request.document_type}")


@router.post("/document")
async def summarise_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    application_type: str = Form("default"),
):
    """Summarise an uploaded document file."""
    content = await file.read()
    ext = file.filename.split(".")[-1].lower() if file.filename else "txt"
    text = await extract_text_from_upload(content, ext)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from document")

    engine = get_engine()
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid document_type: {document_type}")

    if doc_type == DocumentType.SUGAM:
        result = engine.summarise_sugam(text, application_type)
        return {"document_type": "sugam", "summary": result.raw_summary,
                "completeness_score": result.completeness_score,
                "missing_mandatory_fields": result.missing_mandatory_fields,
                "reviewer_notes": result.reviewer_notes}

    elif doc_type == DocumentType.SAE:
        result = engine.summarise_sae(text)
        return {"document_type": "sae", "structured_narrative": result.structured_narrative,
                "seriousness_criteria": result.seriousness_criteria,
                "causality_assessment": result.causality_assessment,
                "key_flags": result.key_flags}

    elif doc_type == DocumentType.MEETING:
        result = engine.summarise_meeting(text)
        return {"document_type": "meeting", "summary": result.full_summary,
                "key_decisions": result.key_decisions,
                "action_items": result.action_items}

    raise HTTPException(status_code=400, detail=f"Unknown document_type: {document_type}")


@router.post("/audio")
async def summarise_audio(file: UploadFile = File(...)):
    """Transcribe audio meeting recording and summarise it."""
    audio_extensions = {"mp3", "mp4", "wav", "m4a", "ogg", "flac"}
    ext = file.filename.split(".")[-1].lower() if file.filename else ""
    if ext not in audio_extensions:
        raise HTTPException(status_code=415, detail=f"Unsupported audio format: .{ext}")

    content = await file.read()
    engine = get_engine()

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = engine.summarise_meeting(text="", audio_path=tmp_path)
        return {
            "document_type": "meeting",
            "source": "audio_transcription",
            "transcript_length_words": result.transcript_length_words,
            "meeting_date": result.meeting_date,
            "participants": result.participants,
            "key_decisions": result.key_decisions,
            "action_items": result.action_items,
            "next_steps": result.next_steps,
            "summary": result.full_summary,
        }
    finally:
        os.unlink(tmp_path)
