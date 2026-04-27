from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/types")
async def get_document_types():
    """Returns supported document types and their checklist schemas."""
    return {
        "document_types": [
            {
                "id": "new_drug_application",
                "label": "New Drug Application",
                "module": "completeness",
                "sugam_checklist": True
            },
            {
                "id": "clinical_trial",
                "label": "Clinical Trial Application",
                "module": "completeness",
                "sugam_checklist": True
            },
            {
                "id": "sae_report",
                "label": "Serious Adverse Event Report",
                "module": "completeness+classification",
                "sugam_checklist": False
            },
            {
                "id": "medical_device",
                "label": "Medical Device Application",
                "module": "completeness",
                "sugam_checklist": True
            },
        ]
    }
