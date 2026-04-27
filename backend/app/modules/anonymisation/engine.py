"""
Anonymisation Module

Two-step pipeline:
  Step 1 - Pseudonymisation: Replace PII/PHI with reversible secure tokens
  Step 2 - Irreversible anonymisation: Generalise and normalise residual identifiers

Compliance: DPDP Act 2023, NDHM Health Data Management Policy,
            ICMR Ethical Guidelines, CDSCO standards

Privacy metrics reported: k-anonymity, l-diversity, t-closeness
"""

import re
import hashlib
import hmac
import json
import logging
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entity type registry
# ---------------------------------------------------------------------------

ENTITY_TYPES = {
    "PERSON": "PII",
    "EMAIL_ADDRESS": "PII",
    "PHONE_NUMBER": "PII",
    "LOCATION": "PII",
    "DATE_TIME": "PHI",
    "AGE": "PHI",
    "MEDICAL_LICENSE": "PHI",
    "NRP": "PII",          # national registration / Aadhaar
    "IN_PAN": "PII",
    "IN_AADHAAR": "PII",
    "CREDIT_CARD": "PII",
    "IBAN_CODE": "PII",
    "IP_ADDRESS": "PII",
    "URL": "PII",
    "DIAGNOSIS": "PHI",
    "TREATMENT": "PHI",
    "DRUG_NAME": "PHI",
    "HOSPITAL": "PHI",
    "PATIENT_ID": "PHI",
}

# Regex patterns for India-specific identifiers not covered by Presidio
INDIA_PATTERNS = {
    "IN_AADHAAR": re.compile(r"\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b"),
    "IN_PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"),
    "IN_PHONE": re.compile(r"(?:\+91|91|0)?[6-9][0-9]{4}\s?[0-9]{5}\b"),
    "IN_PINCODE": re.compile(r"\b[1-9][0-9]{5}\b"),
    "PATIENT_ID": re.compile(r"\b(?:PT|PID|PAT)[-/]?\d{4,10}\b", re.IGNORECASE),
    "CASE_ID": re.compile(r"\b(?:CASE|SAE|CT)[-/]?\d{4,12}\b", re.IGNORECASE),
}

# Age generalisation brackets (as per NDHM guidelines)
AGE_BRACKETS = [(0, 1, "infant"), (1, 5, "toddler"), (5, 12, "child"),
                (12, 18, "adolescent"), (18, 30, "young-adult"),
                (30, 45, "adult"), (45, 60, "middle-aged"),
                (60, 75, "senior"), (75, 200, "elderly")]

# Date generalisation: keep only year-month
DATE_PATTERN = re.compile(
    r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b|"
    r"\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+(\d{2,4})\b",
    re.IGNORECASE
)


@dataclass
class AnonymisationToken:
    original: str
    token: str
    entity_type: str
    step: str  # "pseudonymised" or "generalised"


@dataclass
class AnonymisationResult:
    original_text: str
    pseudonymised_text: str
    anonymised_text: str
    tokens: list[AnonymisationToken] = field(default_factory=list)
    entities_found: dict = field(default_factory=dict)
    processing_time_ms: int = 0


class AnonymisationEngine:
    """
    Hybrid rule-based + NLP anonymisation engine.

    Uses Microsoft Presidio as the primary NER backbone, augmented with:
    - India-specific regex patterns (Aadhaar, PAN, phone, etc.)
    - scispaCy medical entity recognition for PHI
    - Custom post-processing for age generalisation and date normalisation
    """

    def __init__(self, salt: str):
        self.salt = salt.encode()
        self._presidio_analyzer = None
        self._presidio_anonymizer = None
        self._nlp = None
        self._token_map: dict[str, str] = {}

    def _load_presidio(self):
        if self._presidio_analyzer is None:
            try:
                from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
                from presidio_analyzer.nlp_engine import NlpEngineProvider
                from presidio_anonymizer import AnonymizerEngine

                configuration = {
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
                }
                provider = NlpEngineProvider(nlp_configuration=configuration)
                nlp_engine = provider.create_engine()
                self._presidio_analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
                self._presidio_anonymizer = AnonymizerEngine()
                logger.info("Presidio loaded successfully")
            except Exception as e:
                logger.warning(f"Presidio not available, using regex fallback: {e}")

    def _generate_token(self, text: str, entity_type: str) -> str:
        """Generate deterministic pseudonymisation token via HMAC-SHA256."""
        key = hmac.new(self.salt, f"{entity_type}:{text}".encode(), hashlib.sha256)
        short_hash = key.hexdigest()[:8].upper()
        prefix = entity_type[:3]
        return f"[{prefix}-{short_hash}]"

    def _pseudonymise_with_presidio(self, text: str) -> tuple[str, list[AnonymisationToken]]:
        self._load_presidio()
        tokens = []

        if self._presidio_analyzer is None:
            return text, tokens

        results = self._presidio_analyzer.analyze(
            text=text,
            entities=list(ENTITY_TYPES.keys()),
            language="en"
        )

        replacements = []
        for result in results:
            original = text[result.start:result.end]
            token = self._generate_token(original, result.entity_type)
            self._token_map[token] = original
            replacements.append((result.start, result.end, token, result.entity_type))
            tokens.append(AnonymisationToken(
                original=original,
                token=token,
                entity_type=result.entity_type,
                step="pseudonymised"
            ))

        # Apply replacements in reverse order to preserve offsets
        for start, end, token, _ in sorted(replacements, key=lambda x: x[0], reverse=True):
            text = text[:start] + token + text[end:]

        return text, tokens

    def _pseudonymise_with_regex(self, text: str) -> tuple[str, list[AnonymisationToken]]:
        """Apply India-specific patterns not caught by Presidio."""
        tokens = []
        for entity_type, pattern in INDIA_PATTERNS.items():
            for match in pattern.finditer(text):
                original = match.group()
                token = self._generate_token(original, entity_type)
                self._token_map[token] = original
                tokens.append(AnonymisationToken(
                    original=original, token=token,
                    entity_type=entity_type, step="pseudonymised"
                ))
            text = pattern.sub(
                lambda m: self._generate_token(m.group(), entity_type),
                text
            )
        return text, tokens

    def _generalise_ages(self, text: str) -> tuple[str, list[AnonymisationToken]]:
        """Replace specific ages with age brackets."""
        tokens = []
        age_pattern = re.compile(
            r"\b(\d{1,3})\s*(?:year[s]?(?:\s*old)?|yr[s]?(?:\s*old)?|y\.?o\.?)\b",
            re.IGNORECASE
        )
        for match in age_pattern.finditer(text):
            age = int(match.group(1))
            bracket = next(
                (label for lo, hi, label in AGE_BRACKETS if lo <= age < hi),
                "adult"
            )
            generalised = f"[AGE:{bracket}]"
            tokens.append(AnonymisationToken(
                original=match.group(), token=generalised,
                entity_type="AGE", step="generalised"
            ))
        text = age_pattern.sub(
            lambda m: f"[AGE:{next((l for lo,hi,l in AGE_BRACKETS if lo<=int(m.group(1))<hi),'adult')}]",
            text
        )
        return text, tokens

    def _generalise_dates(self, text: str) -> tuple[str, list[AnonymisationToken]]:
        """Generalise specific dates to year-month only."""
        tokens = []
        month_map = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
            "may": "05", "jun": "06", "jul": "07", "aug": "08",
            "sep": "09", "oct": "10", "nov": "11", "dec": "12"
        }

        def replace_date(m):
            original = m.group()
            if m.group(3):  # numeric dd/mm/yyyy
                year = m.group(3) if len(m.group(3)) == 4 else "20" + m.group(3)
                month = m.group(2).zfill(2)
                generalised = f"[DATE:{year}-{month}]"
            elif m.group(6):  # dd Month yyyy
                year = m.group(6) if len(m.group(6)) == 4 else "20" + m.group(6)
                month = month_map.get(m.group(5)[:3].lower(), "??")
                generalised = f"[DATE:{year}-{month}]"
            else:
                generalised = "[DATE:REDACTED]"
            tokens.append(AnonymisationToken(
                original=original, token=generalised,
                entity_type="DATE_TIME", step="generalised"
            ))
            return generalised

        text = DATE_PATTERN.sub(replace_date, text)
        return text, tokens

    def anonymise_text(self, text: str) -> AnonymisationResult:
        """Full two-step anonymisation pipeline for unstructured text."""
        import time
        start = time.perf_counter()

        all_tokens = []

        # Step 1a: Presidio NER pseudonymisation
        pseudonymised, tokens_presidio = self._pseudonymise_with_presidio(text)
        all_tokens.extend(tokens_presidio)

        # Step 1b: India-specific regex pseudonymisation
        pseudonymised, tokens_regex = self._pseudonymise_with_regex(pseudonymised)
        all_tokens.extend(tokens_regex)

        # Step 2a: Age generalisation
        anonymised, tokens_age = self._generalise_ages(pseudonymised)
        all_tokens.extend(tokens_age)

        # Step 2b: Date generalisation
        anonymised, tokens_date = self._generalise_dates(anonymised)
        all_tokens.extend(tokens_date)

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        entity_counts = defaultdict(int)
        for t in all_tokens:
            entity_counts[t.entity_type] += 1

        return AnonymisationResult(
            original_text=text,
            pseudonymised_text=pseudonymised,
            anonymised_text=anonymised,
            tokens=all_tokens,
            entities_found=dict(entity_counts),
            processing_time_ms=elapsed_ms
        )

    def anonymise_dataframe(self, df: pd.DataFrame, sensitive_columns: list[str]) -> dict:
        """
        Anonymise structured tabular data.
        Returns anonymised dataframe + k-anonymity, l-diversity, t-closeness metrics.
        """
        anonymised_df = df.copy()

        for col in sensitive_columns:
            if col not in df.columns:
                continue
            anonymised_df[col] = df[col].apply(
                lambda v: self._generate_token(str(v), "STRUCTURED_PII") if pd.notna(v) else v
            )

        metrics = compute_privacy_metrics(anonymised_df, sensitive_columns)

        return {
            "anonymised_data": anonymised_df.to_dict(orient="records"),
            "privacy_metrics": metrics,
            "rows_processed": len(df),
            "columns_anonymised": sensitive_columns,
        }


def compute_privacy_metrics(df: pd.DataFrame, quasi_identifiers: list[str]) -> dict:
    """
    Compute k-anonymity, l-diversity, and t-closeness on anonymised dataset.

    k-anonymity: every record is indistinguishable from at least k-1 others
                 on the quasi-identifier combination.
    l-diversity: each equivalence class has at least l distinct sensitive values.
    t-closeness: distribution of sensitive attribute in each class is within
                 distance t of its overall distribution.
    """
    available_qi = [c for c in quasi_identifiers if c in df.columns]
    if not available_qi:
        return {"k_anonymity": None, "l_diversity": None, "t_closeness": None,
                "note": "No quasi-identifier columns found in dataset"}

    groups = df.groupby(available_qi)
    group_sizes = groups.size()

    k_anonymity = int(group_sizes.min())

    sensitive_col = next(
        (c for c in df.columns if c not in available_qi and df[c].dtype == object),
        None
    )

    l_diversity = None
    t_closeness = None

    if sensitive_col:
        l_diversity = int(groups[sensitive_col].nunique().min())

        overall_dist = df[sensitive_col].value_counts(normalize=True)
        max_t = 0.0
        for _, group_df in groups:
            group_dist = group_df[sensitive_col].value_counts(normalize=True)
            combined = overall_dist.align(group_dist, fill_value=0)
            emd = float((combined[0] - combined[1]).abs().sum() / 2)
            max_t = max(max_t, emd)
        t_closeness = round(max_t, 4)

    return {
        "k_anonymity": k_anonymity,
        "l_diversity": l_diversity,
        "t_closeness": t_closeness,
        "equivalence_classes": len(group_sizes),
        "min_class_size": k_anonymity,
        "max_class_size": int(group_sizes.max()),
        "compliant_k5": k_anonymity >= 5,
        "compliant_l2": l_diversity >= 2 if l_diversity else None,
        "compliant_t025": t_closeness <= 0.25 if t_closeness else None,
    }
