from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import io
import logging

from app.core.config import settings
from app.modules.anonymisation.engine import AnonymisationEngine
from app.utils.document_parser import extract_text_from_upload

logger = logging.getLogger(__name__)
router = APIRouter()

_engine: Optional[AnonymisationEngine] = None


def get_engine() -> AnonymisationEngine:
    global _engine
    if _engine is None:
        _engine = AnonymisationEngine(salt=settings.PSEUDONYMISATION_SALT)
    return _engine


class TextAnonymisationRequest(BaseModel):
    text: str
    document_id: Optional[str] = None


@router.post("/text")
async def anonymise_text(request: TextAnonymisationRequest):
    """Anonymise plain text. Returns pseudonymised and fully anonymised versions."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    engine = get_engine()
    result = engine.anonymise_text(request.text)

    return {
        "document_id": request.document_id,
        "pseudonymised_text": result.pseudonymised_text,
        "anonymised_text": result.anonymised_text,
        "entities_detected": result.entities_found,
        "total_entities": sum(result.entities_found.values()),
        "processing_time_ms": result.processing_time_ms,
        "token_manifest": [
            {
                "token": t.token,
                "entity_type": t.entity_type,
                "step": t.step
            }
            for t in result.tokens
        ]
    }


@router.post("/document")
async def anonymise_document(
    file: UploadFile = File(...),
    return_tokens: bool = Form(False)
):
    """
    Anonymise a document (PDF, DOCX, TXT).
    Extracts text, applies two-step anonymisation, returns anonymised text.
    """
    if file.content_type and file.size and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds maximum upload size")

    ext = file.filename.split(".")[-1].lower() if file.filename else ""
    if ext not in settings.allowed_extensions_set:
        raise HTTPException(status_code=415, detail=f"File type .{ext} not supported")

    content = await file.read()
    text = await extract_text_from_upload(content, ext)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from document")

    engine = get_engine()
    result = engine.anonymise_text(text)

    response = {
        "filename": file.filename,
        "original_length": len(text),
        "anonymised_length": len(result.anonymised_text),
        "pseudonymised_text": result.pseudonymised_text,
        "anonymised_text": result.anonymised_text,
        "entities_detected": result.entities_found,
        "total_entities": sum(result.entities_found.values()),
        "processing_time_ms": result.processing_time_ms,
    }

    if return_tokens:
        response["token_manifest"] = [
            {"token": t.token, "entity_type": t.entity_type, "step": t.step}
            for t in result.tokens
        ]

    return response


@router.post("/structured")
async def anonymise_structured(
    file: UploadFile = File(...),
    sensitive_columns: str = Form(...)
):
    """
    Anonymise structured data (CSV).
    Returns anonymised records with k-anonymity, l-diversity, t-closeness metrics.
    """
    import pandas as pd

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}")

    columns = [c.strip() for c in sensitive_columns.split(",")]
    engine = get_engine()
    result = engine.anonymise_dataframe(df, columns)

    return {
        "filename": file.filename,
        "rows_processed": result["rows_processed"],
        "columns_anonymised": result["columns_anonymised"],
        "anonymised_data": result["anonymised_data"],
        "privacy_metrics": result["privacy_metrics"],
        "compliance": {
            "dpdp_act_2023": result["privacy_metrics"].get("compliant_k5", False),
            "ndhm_policy": result["privacy_metrics"].get("compliant_l2", False),
            "icmr_guidelines": result["privacy_metrics"].get("compliant_t025", False),
        }
    }
