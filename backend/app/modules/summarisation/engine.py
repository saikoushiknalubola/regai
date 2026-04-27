"""
Summarisation Module

Three separate pipelines for three document types:

1. SUGAM Checklist Applications
   - Structured field extraction from CDSCO application forms
   - Gap analysis against mandatory field schema
   - Output: reviewer summary card with completeness score

2. SAE (Serious Adverse Event) Case Narrations
   - Clinical entity extraction: drug names, diagnoses, outcomes, causality
   - Structured SAE summary following CDSCO/ICH E2A format
   - Severity pre-classification

3. Meeting Transcripts / Audio Files
   - Audio: Whisper STT transcription
   - Abstractive summarisation: key decisions, action items, next steps
   - Participant-attributed action item extraction
"""

import json
import logging
import re
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    SUGAM = "sugam"
    SAE = "sae"
    MEETING = "meeting"


@dataclass
class SugamSummary:
    application_number: Optional[str]
    applicant_name: Optional[str]
    drug_name: Optional[str]
    application_type: Optional[str]
    completeness_score: float
    missing_mandatory_fields: list[str]
    present_fields: dict
    reviewer_notes: str
    raw_summary: str


@dataclass
class SAESummary:
    case_id: Optional[str]
    patient_demographics: dict
    suspect_drug: Optional[str]
    dose_route: Optional[str]
    adverse_event: Optional[str]
    event_onset_date: Optional[str]
    outcome: Optional[str]
    causality_assessment: Optional[str]
    seriousness_criteria: list[str]
    reporter_type: Optional[str]
    action_taken: Optional[str]
    rechallenge: Optional[str]
    structured_narrative: str
    key_flags: list[str]


@dataclass
class MeetingSummary:
    meeting_date: Optional[str]
    participants: list[str]
    agenda_items: list[str]
    key_decisions: list[str]
    action_items: list[dict]
    next_steps: list[str]
    full_summary: str
    transcript_length_words: int


# SUGAM mandatory fields by application type
SUGAM_MANDATORY_FIELDS = {
    "new_drug": [
        "applicant_name", "drug_name", "generic_name", "dosage_form",
        "strength", "route_of_administration", "therapeutic_indication",
        "proposed_dosage", "manufacturing_site", "regulatory_status_other_countries",
        "clinical_trial_data_summary", "pharmacokinetic_data", "safety_data",
        "quality_data", "proposed_labelling"
    ],
    "clinical_trial": [
        "protocol_number", "title", "phase", "sponsor_name", "principal_investigator",
        "investigational_product", "indication", "study_design", "sample_size",
        "inclusion_criteria", "exclusion_criteria", "primary_endpoint",
        "secondary_endpoints", "safety_monitoring_plan", "irb_approval",
        "informed_consent_form"
    ],
    "medical_device": [
        "device_name", "device_class", "intended_use", "manufacturer_name",
        "manufacturing_site", "technical_specifications", "test_reports",
        "clinical_evidence", "risk_analysis", "labelling_draft"
    ],
    "default": [
        "applicant_name", "application_type", "product_name",
        "date_of_submission", "contact_details"
    ]
}

# Seriousness criteria keywords (ICH E2A)
SERIOUSNESS_KEYWORDS = {
    "death": ["death", "fatal", "died", "deceased", "mortality"],
    "life_threatening": ["life-threatening", "life threatening", "near fatal"],
    "hospitalisation": ["hospitalised", "hospitalized", "hospitalisation", "hospitalization",
                        "admitted", "admission", "inpatient"],
    "disability": ["disability", "disabled", "permanent damage", "incapacitation",
                   "incapacitated", "significant disability"],
    "congenital_anomaly": ["congenital anomaly", "birth defect", "teratogenic", "foetal"],
    "medically_important": ["medically important", "medically significant", "required intervention"]
}

# Causality terms
CAUSALITY_TERMS = {
    "certain": ["certain", "definite", "definitive"],
    "probable": ["probable", "likely"],
    "possible": ["possible", "may be related"],
    "unlikely": ["unlikely", "doubtful", "unrelated"],
    "unclassified": ["unclassified", "unknown", "not assessable"]
}


class SummarisationEngine:

    def __init__(self, gemini_api_key: str, gemini_model: str = "gemini-1.5-flash"):
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self._gemini_client = None
        self._whisper_model = None

    def _get_gemini(self):
        if self._gemini_client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_client = genai.GenerativeModel(self.gemini_model)
        return self._gemini_client

    def _get_whisper(self):
        if self._whisper_model is None:
            import whisper
            self._whisper_model = whisper.load_model("base")
        return self._whisper_model

    def _call_gemini(self, prompt: str, max_tokens: int = 1024) -> str:
        try:
            model = self._get_gemini()
            response = model.generate_content(
                prompt,
                generation_config={"max_output_tokens": max_tokens, "temperature": 0.1}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return ""

    # ------------------------------------------------------------------
    # Pipeline 1: SUGAM checklist summarisation
    # ------------------------------------------------------------------

    def summarise_sugam(self, text: str, application_type: str = "default") -> SugamSummary:
        """
        Extract structured fields from SUGAM checklist application.
        Identifies present fields, missing mandatory fields, and
        produces a standardised reviewer summary card.
        """
        fields = self._extract_sugam_fields(text)
        mandatory = SUGAM_MANDATORY_FIELDS.get(application_type, SUGAM_MANDATORY_FIELDS["default"])
        present_mandatory = [f for f in mandatory if f in fields]
        missing_mandatory = [f for f in mandatory if f not in fields]
        completeness_score = len(present_mandatory) / len(mandatory) if mandatory else 1.0

        prompt = f"""You are a CDSCO regulatory reviewer. Below is the extracted text from a drug/device application.

Application type: {application_type}
Present fields: {json.dumps(fields, indent=2)}
Missing mandatory fields: {missing_mandatory}

Write a concise reviewer summary card (150-200 words) covering:
1. What this application is for
2. Key clinical/technical highlights
3. Critical gaps that require the applicant's attention
4. Overall assessment for expedited review

Be factual and direct. Use regulatory terminology. Do not fabricate data not present in the text.

APPLICATION TEXT:
{text[:4000]}
"""

        raw_summary = self._call_gemini(prompt)

        reviewer_notes = ""
        if missing_mandatory:
            reviewer_notes = (
                f"INCOMPLETE: {len(missing_mandatory)} mandatory field(s) missing — "
                f"{', '.join(missing_mandatory[:5])}{'...' if len(missing_mandatory) > 5 else ''}. "
                "Application cannot proceed to technical review until resolved."
            )
        else:
            reviewer_notes = "COMPLETE: All mandatory fields present. Ready for technical review."

        return SugamSummary(
            application_number=fields.get("application_number"),
            applicant_name=fields.get("applicant_name"),
            drug_name=fields.get("drug_name") or fields.get("product_name"),
            application_type=application_type,
            completeness_score=round(completeness_score, 3),
            missing_mandatory_fields=missing_mandatory,
            present_fields=fields,
            reviewer_notes=reviewer_notes,
            raw_summary=raw_summary,
        )

    def _extract_sugam_fields(self, text: str) -> dict:
        """Rule-based field extraction from SUGAM forms."""
        fields = {}
        patterns = {
            "application_number": r"(?:application\s+(?:no|number|#))[:\s]+([A-Z0-9/-]+)",
            "applicant_name": r"(?:applicant|company|firm|sponsor)[:\s]+([^\n]{3,80})",
            "drug_name": r"(?:drug\s+name|product\s+name|brand\s+name)[:\s]+([^\n]{2,60})",
            "generic_name": r"(?:generic\s+name|inn|non-proprietary)[:\s]+([^\n]{2,60})",
            "dosage_form": r"(?:dosage\s+form|pharmaceutical\s+form)[:\s]+([^\n]{2,50})",
            "strength": r"(?:strength|concentration|dose)[:\s]+([\d.]+\s*(?:mg|mcg|ml|g|%|iu)[^\n]{0,30})",
            "route_of_administration": r"(?:route|administration)[:\s]+([^\n]{2,50})",
            "therapeutic_indication": r"(?:indication|therapeutic use|intended use)[:\s]+([^\n]{5,200})",
            "manufacturing_site": r"(?:manufacturing\s+(?:site|facility|plant))[:\s]+([^\n]{5,100})",
            "phase": r"(?:phase)[:\s]+(I{1,3}V?\/?\w*)",
            "protocol_number": r"(?:protocol\s+(?:no|number|#))[:\s]+([A-Z0-9/-]+)",
        }
        for field_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields[field_name] = match.group(1).strip()
        return fields

    # ------------------------------------------------------------------
    # Pipeline 2: SAE case narration summarisation
    # ------------------------------------------------------------------

    def summarise_sae(self, text: str) -> SAESummary:
        """
        Extract structured SAE information following ICH E2A format.
        Identifies seriousness criteria, causality, and produces
        a standardised case summary for CDSCO reviewer.
        """
        demographics = self._extract_patient_demographics(text)
        seriousness = self._detect_seriousness_criteria(text)
        causality = self._extract_causality(text)

        drug_match = re.search(
            r"(?:suspect(?:ed)?\s+drug|investigational\s+product|study\s+drug)[:\s]+([^\n]{2,60})",
            text, re.IGNORECASE
        )
        outcome_match = re.search(
            r"(?:outcome|patient\s+outcome|resolution)[:\s]+([^\n]{2,80})",
            text, re.IGNORECASE
        )
        action_match = re.search(
            r"(?:action\s+taken|drug\s+action)[:\s]+([^\n]{2,80})",
            text, re.IGNORECASE
        )

        prompt = f"""You are a CDSCO pharmacovigilance reviewer. Analyse this SAE case narration.

Write a structured case summary (150-200 words) in this format:
- Case ID and reporter
- Patient demographics (anonymised)
- Suspect drug and therapy details
- Adverse event description and onset
- Seriousness criteria met: {seriousness}
- Causality assessment: {causality}
- Outcome and action taken
- Key flags for reviewer attention

Be precise. Use ICH E2A terminology. Flag any data gaps.

SAE TEXT:
{text[:4000]}
"""

        narrative = self._call_gemini(prompt)

        key_flags = []
        if not seriousness:
            key_flags.append("SERIOUSNESS CRITERIA NOT EXPLICITLY STATED")
        if not causality:
            key_flags.append("CAUSALITY NOT ASSESSED")
        if "rechallenge" not in text.lower():
            key_flags.append("RECHALLENGE DATA ABSENT")
        if not demographics.get("age") and not demographics.get("sex"):
            key_flags.append("PATIENT DEMOGRAPHICS INCOMPLETE")

        return SAESummary(
            case_id=self._extract_case_id(text),
            patient_demographics=demographics,
            suspect_drug=drug_match.group(1).strip() if drug_match else None,
            dose_route=self._extract_dose_route(text),
            adverse_event=self._extract_adverse_event(text),
            event_onset_date=self._extract_onset_date(text),
            outcome=outcome_match.group(1).strip() if outcome_match else None,
            causality_assessment=causality,
            seriousness_criteria=seriousness,
            reporter_type=self._extract_reporter_type(text),
            action_taken=action_match.group(1).strip() if action_match else None,
            rechallenge=self._extract_rechallenge(text),
            structured_narrative=narrative,
            key_flags=key_flags,
        )

    def _extract_patient_demographics(self, text: str) -> dict:
        demo = {}
        age_m = re.search(r"\b(\d{1,3})\s*(?:year|yr|y\.?o\.?)", text, re.IGNORECASE)
        if age_m:
            demo["age"] = age_m.group(1)
        sex_m = re.search(r"\b(male|female|man|woman|boy|girl)\b", text, re.IGNORECASE)
        if sex_m:
            demo["sex"] = sex_m.group(1).lower()
        weight_m = re.search(r"\b(\d{2,3})\s*(?:kg|kilogram)", text, re.IGNORECASE)
        if weight_m:
            demo["weight_kg"] = weight_m.group(1)
        return demo

    def _detect_seriousness_criteria(self, text: str) -> list[str]:
        text_lower = text.lower()
        criteria = []
        for criterion, keywords in SERIOUSNESS_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                criteria.append(criterion)
        return criteria

    def _extract_causality(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for level, terms in CAUSALITY_TERMS.items():
            if any(term in text_lower for term in terms):
                return level
        return None

    def _extract_case_id(self, text: str) -> Optional[str]:
        m = re.search(r"(?:case\s+(?:id|no|number|#)|report\s+id)[:\s]+([A-Z0-9/-]+)", text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _extract_dose_route(self, text: str) -> Optional[str]:
        m = re.search(r"(?:dose|dosage)[:\s]+([\d.]+\s*(?:mg|mcg|g|ml|iu)[^\n]{0,40})", text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _extract_adverse_event(self, text: str) -> Optional[str]:
        m = re.search(r"(?:adverse\s+(?:event|reaction|effect)|adr|ae)[:\s]+([^\n]{3,100})", text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _extract_onset_date(self, text: str) -> Optional[str]:
        m = re.search(r"(?:onset\s+date|date\s+of\s+onset)[:\s]+([^\n]{3,30})", text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _extract_reporter_type(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for rt in ["physician", "pharmacist", "nurse", "patient", "consumer", "lawyer", "other healthcare"]:
            if rt in text_lower:
                return rt
        return None

    def _extract_rechallenge(self, text: str) -> Optional[str]:
        m = re.search(r"(?:rechallenge|re-challenge)[:\s]+([^\n]{2,60})", text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    # ------------------------------------------------------------------
    # Pipeline 3: Meeting transcript / audio summarisation
    # ------------------------------------------------------------------

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio file using OpenAI Whisper."""
        try:
            model = self._get_whisper()
            result = model.transcribe(audio_path, language="en", verbose=False)
            return result["text"]
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise

    def summarise_meeting(self, text: str, audio_path: Optional[str] = None) -> MeetingSummary:
        """
        Summarise meeting transcript. If audio_path provided, transcribes first.
        Extracts: participants, agenda, decisions, action items, next steps.
        """
        if audio_path:
            text = self.transcribe_audio(audio_path)

        word_count = len(text.split())

        prompt = f"""You are a regulatory affairs secretary. Summarise this CDSCO meeting transcript.

Return your response as a JSON object with exactly these keys:
{{
  "participants": ["list of participant names/roles mentioned"],
  "agenda_items": ["list of agenda items discussed"],
  "key_decisions": ["list of concrete decisions made"],
  "action_items": [
    {{"owner": "person/team", "action": "what to do", "deadline": "when if mentioned"}}
  ],
  "next_steps": ["list of next steps"],
  "full_summary": "150-200 word factual summary of the meeting"
}}

Return only the JSON. No preamble. No explanation.

TRANSCRIPT:
{text[:6000]}
"""

        raw = self._call_gemini(prompt, max_tokens=1500)

        parsed = {}
        try:
            clean = re.sub(r"```(?:json)?", "", raw).strip()
            parsed = json.loads(clean)
        except Exception:
            logger.warning("Gemini did not return valid JSON for meeting summary, using fallback")
            parsed = self._fallback_meeting_parse(text)

        return MeetingSummary(
            meeting_date=self._extract_meeting_date(text),
            participants=parsed.get("participants", []),
            agenda_items=parsed.get("agenda_items", []),
            key_decisions=parsed.get("key_decisions", []),
            action_items=parsed.get("action_items", []),
            next_steps=parsed.get("next_steps", []),
            full_summary=parsed.get("full_summary", ""),
            transcript_length_words=word_count,
        )

    def _extract_meeting_date(self, text: str) -> Optional[str]:
        m = re.search(
            r"(?:meeting\s+date|date\s+of\s+meeting|held\s+on)[:\s]+([^\n]{3,30})",
            text, re.IGNORECASE
        )
        return m.group(1).strip() if m else None

    def _fallback_meeting_parse(self, text: str) -> dict:
        """Rule-based fallback when Gemini JSON parsing fails."""
        lines = text.split("\n")
        action_pattern = re.compile(
            r"(?:action|to\s+do|follow\s+up|will|shall|must)[:\-]?\s+(.+)", re.IGNORECASE
        )
        decision_pattern = re.compile(
            r"(?:decided|resolved|agreed|approved|rejected)[:\-]?\s+(.+)", re.IGNORECASE
        )

        actions = [{"owner": "TBD", "action": m.group(1).strip(), "deadline": "TBD"}
                   for line in lines for m in [action_pattern.search(line)] if m]
        decisions = [m.group(1).strip() for line in lines
                     for m in [decision_pattern.search(line)] if m]

        return {
            "participants": [],
            "agenda_items": [],
            "key_decisions": decisions[:10],
            "action_items": actions[:10],
            "next_steps": [],
            "full_summary": text[:500] + "..." if len(text) > 500 else text,
        }
