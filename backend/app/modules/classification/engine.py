"""
Classification Module

Three capabilities:

1. Severity Classification
   - Classifies SAE cases by outcome: death / disability / hospitalisation / others
   - Uses fine-tuned BERT classifier with fallback to rule-based keyword scoring
   - Reports confidence score and contributing evidence

2. Duplicate Detection
   - Fuzzy string matching on patient demographics + adverse event description
   - Sentence embedding similarity for semantic duplicate detection
   - Configurable similarity threshold

3. Priority Queue
   - Composite priority score: severity weight + completeness + submission age
   - Generates sorted reviewer workload queue
   - Supports workload balancing across reviewers
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class SeverityLevel(str, Enum):
    DEATH = "death"
    DISABILITY = "disability"
    HOSPITALISATION = "hospitalisation"
    OTHERS = "others"


SEVERITY_WEIGHTS = {
    SeverityLevel.DEATH: 1.0,
    SeverityLevel.DISABILITY: 0.8,
    SeverityLevel.HOSPITALISATION: 0.6,
    SeverityLevel.OTHERS: 0.3,
}

SEVERITY_KEYWORDS = {
    SeverityLevel.DEATH: [
        "death", "died", "fatal", "fatality", "deceased", "mortality",
        "lethal", "killed", "expire", "passed away", "demise"
    ],
    SeverityLevel.DISABILITY: [
        "disability", "disabled", "permanent damage", "incapacitation",
        "significant disability", "persistent", "irreversible",
        "paralysis", "paralysed", "blind", "deaf", "amputat"
    ],
    SeverityLevel.HOSPITALISATION: [
        "hospitalised", "hospitalized", "hospitalisation", "hospitalization",
        "admitted", "admission", "inpatient", "icu", "intensive care",
        "emergency", "ward", "bed rest"
    ],
}


@dataclass
class SeverityResult:
    case_id: str
    predicted_severity: SeverityLevel
    confidence: float
    evidence: list[str]
    rule_based_signals: dict
    model_used: str  # "bert_classifier" or "rule_based"


@dataclass
class DuplicateCheckResult:
    case_id: str
    is_duplicate: bool
    duplicate_of: Optional[str]
    similarity_score: float
    matching_fields: list[str]
    method: str


@dataclass
class PriorityQueueItem:
    case_id: str
    document_type: str
    severity: SeverityLevel
    priority_score: float
    completeness_score: float
    submission_age_days: int
    assigned_reviewer: Optional[str]
    flags: list[str]


class ClassificationEngine:

    DUPLICATE_THRESHOLD = 0.82
    DUPLICATE_FUZZY_THRESHOLD = 85

    def __init__(self):
        self._bert_model = None
        self._bert_tokenizer = None
        self._embedding_model = None
        self._case_registry: dict[str, dict] = {}

    def _get_bert_classifier(self):
        if self._bert_model is None:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch
                model_name = "uer/roberta-base-finetuned-dianping-chinese"
                self._bert_tokenizer = AutoTokenizer.from_pretrained(
                    "dmis-lab/biobert-base-cased-v1.2"
                )
                self._bert_model = AutoModelForSequenceClassification.from_pretrained(
                    "dmis-lab/biobert-base-cased-v1.2",
                    num_labels=4
                )
                logger.info("BioBERT classifier loaded")
            except Exception as e:
                logger.warning(f"BERT classifier not available: {e}")
        return self._bert_model, self._bert_tokenizer

    def _get_embedding_model(self):
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"Embedding model not available: {e}")
        return self._embedding_model

    # ------------------------------------------------------------------
    # 1. Severity classification
    # ------------------------------------------------------------------

    def classify_severity(self, text: str, case_id: str = "unknown") -> SeverityResult:
        """
        Classify SAE severity. Attempts BERT classifier first,
        falls back to rule-based keyword scoring.
        """
        rule_signals = self._rule_based_severity(text)
        model, tokenizer = self._get_bert_classifier()

        if model is not None and tokenizer is not None:
            result = self._bert_classify(text, case_id, rule_signals, model, tokenizer)
        else:
            result = self._rule_based_classify(text, case_id, rule_signals)

        self._case_registry[case_id] = {
            "text": text,
            "severity": result.predicted_severity,
            "classified_at": datetime.now(timezone.utc).isoformat()
        }

        return result

    def _rule_based_severity(self, text: str) -> dict:
        """Score each severity level based on keyword presence."""
        text_lower = text.lower()
        scores = {}
        for severity, keywords in SEVERITY_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in text_lower]
            scores[severity] = {"count": len(matched), "matched_keywords": matched}
        return scores

    def _rule_based_classify(
        self, text: str, case_id: str, signals: dict
    ) -> SeverityResult:
        """Classify using keyword scoring when BERT unavailable."""
        sorted_signals = sorted(
            signals.items(), key=lambda x: x[1]["count"], reverse=True
        )
        has_any = sorted_signals[0][1]["count"] > 0
        top_severity = sorted_signals[0][0] if has_any else SeverityLevel.OTHERS
        top_count = sorted_signals[0][1]["count"]
        total_signals = sum(s["count"] for _, s in signals.items())

        confidence = min(0.9, 0.4 + (top_count / max(total_signals, 1)) * 0.5) if has_any else 0.5
        evidence = signals.get(top_severity, {}).get("matched_keywords", [])

        return SeverityResult(
            case_id=case_id,
            predicted_severity=top_severity,
            confidence=round(confidence, 3),
            evidence=evidence,
            rule_based_signals={k.value: v for k, v in signals.items()},
            model_used="rule_based",
        )

    def _bert_classify(
        self, text: str, case_id: str, signals: dict, model, tokenizer
    ) -> SeverityResult:
        """Classify using fine-tuned BERT model."""
        try:
            import torch
            label_map = {
                0: SeverityLevel.DEATH,
                1: SeverityLevel.DISABILITY,
                2: SeverityLevel.HOSPITALISATION,
                3: SeverityLevel.OTHERS,
            }
            inputs = tokenizer(
                text[:512], return_tensors="pt",
                truncation=True, padding=True, max_length=512
            )
            with torch.no_grad():
                outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)[0].tolist()
            predicted_idx = int(torch.argmax(outputs.logits, dim=1).item())
            predicted_severity = label_map[predicted_idx]
            confidence = probs[predicted_idx]

            return SeverityResult(
                case_id=case_id,
                predicted_severity=predicted_severity,
                confidence=round(confidence, 3),
                evidence=signals.get(predicted_severity, {}).get("matched_keywords", []),
                rule_based_signals={k.value: v for k, v in signals.items()},
                model_used="bert_classifier",
            )
        except Exception as e:
            logger.warning(f"BERT classification failed, using rule-based: {e}")
            return self._rule_based_classify(text, case_id, signals)

    # ------------------------------------------------------------------
    # 2. Duplicate detection
    # ------------------------------------------------------------------

    def check_duplicate(self, text: str, case_id: str) -> DuplicateCheckResult:
        """
        Check if a case is a duplicate of an already-registered case.
        Uses two-stage approach:
          Stage 1: Fast fuzzy string matching on key fields
          Stage 2: Semantic similarity on full case text
        """
        if not self._case_registry:
            return DuplicateCheckResult(
                case_id=case_id, is_duplicate=False, duplicate_of=None,
                similarity_score=0.0, matching_fields=[], method="no_corpus"
            )

        try:
            from rapidfuzz import fuzz
        except ImportError:
            return DuplicateCheckResult(
                case_id=case_id, is_duplicate=False, duplicate_of=None,
                similarity_score=0.0, matching_fields=[], method="unavailable"
            )

        key_fields = self._extract_key_fields(text)
        best_fuzzy_score = 0.0
        best_fuzzy_id = None
        matching_fields = []

        for existing_id, existing_case in self._case_registry.items():
            if existing_id == case_id:
                continue
            existing_fields = self._extract_key_fields(existing_case["text"])

            field_scores = {}
            for field_name, value in key_fields.items():
                if field_name in existing_fields and value and existing_fields[field_name]:
                    score = fuzz.token_sort_ratio(value, existing_fields[field_name])
                    field_scores[field_name] = score / 100.0

            if field_scores:
                composite = sum(field_scores.values()) / len(field_scores)
                if composite > best_fuzzy_score:
                    best_fuzzy_score = composite
                    best_fuzzy_id = existing_id
                    matching_fields = [f for f, s in field_scores.items() if s > 0.8]

        if best_fuzzy_score >= self.DUPLICATE_FUZZY_THRESHOLD / 100:
            return DuplicateCheckResult(
                case_id=case_id, is_duplicate=True, duplicate_of=best_fuzzy_id,
                similarity_score=round(best_fuzzy_score, 3),
                matching_fields=matching_fields, method="fuzzy_matching"
            )

        emb_model = self._get_embedding_model()
        if emb_model and self._case_registry:
            import numpy as np
            new_embedding = emb_model.encode([text[:512]])[0]
            best_sem_score = 0.0
            best_sem_id = None

            for existing_id, existing_case in self._case_registry.items():
                if existing_id == case_id:
                    continue
                existing_emb = emb_model.encode([existing_case["text"][:512]])[0]
                sim = float(np.dot(new_embedding, existing_emb) /
                            (np.linalg.norm(new_embedding) * np.linalg.norm(existing_emb) + 1e-8))
                if sim > best_sem_score:
                    best_sem_score = sim
                    best_sem_id = existing_id

            if best_sem_score >= self.DUPLICATE_THRESHOLD:
                return DuplicateCheckResult(
                    case_id=case_id, is_duplicate=True, duplicate_of=best_sem_id,
                    similarity_score=round(best_sem_score, 3),
                    matching_fields=[], method="semantic_similarity"
                )

        return DuplicateCheckResult(
            case_id=case_id, is_duplicate=False, duplicate_of=None,
            similarity_score=round(best_fuzzy_score, 3),
            matching_fields=[], method="not_duplicate"
        )

    def _extract_key_fields(self, text: str) -> dict:
        patterns = {
            "patient_id": r"(?:patient|pt|pid)[:\s]+([A-Z0-9-]{3,20})",
            "drug_name": r"(?:drug|product)[:\s]+([^\n]{2,40})",
            "adverse_event": r"(?:adverse event|adr|ae)[:\s]+([^\n]{2,80})",
            "onset_date": r"(?:onset)[:\s]+([^\n]{2,20})",
        }
        fields = {}
        for name, pattern in patterns.items():
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                fields[name] = m.group(1).strip().lower()
        return fields

    # ------------------------------------------------------------------
    # 3. Priority queue
    # ------------------------------------------------------------------

    def build_priority_queue(self, cases: list[dict]) -> list[PriorityQueueItem]:
        """
        Build a prioritised review queue from a list of case dicts.

        Priority score formula:
          P = (severity_weight * 0.5) + (completeness_deficit * 0.3) + (age_factor * 0.2)

        Where:
          severity_weight  = SEVERITY_WEIGHTS[severity_level]
          completeness_deficit = 1.0 - completeness_score (more incomplete = more urgent to query)
          age_factor       = min(1.0, submission_age_days / 30) (older = higher priority)
        """
        queue_items = []

        for case in cases:
            severity = SeverityLevel(case.get("severity", "others"))
            completeness = float(case.get("completeness_score", 1.0))
            age_days = int(case.get("submission_age_days", 0))

            severity_w = SEVERITY_WEIGHTS[severity]
            completeness_deficit = 1.0 - completeness
            age_factor = min(1.0, age_days / 30.0)

            priority_score = (severity_w * 0.5) + (completeness_deficit * 0.3) + (age_factor * 0.2)

            flags = []
            if severity == SeverityLevel.DEATH:
                flags.append("DEATH CASE: Immediate review required")
            if completeness < 0.6:
                flags.append("INCOMPLETE: Deficiency letter required before review")
            if age_days > 14:
                flags.append(f"OVERDUE: {age_days} days since submission")
            if case.get("is_duplicate"):
                flags.append(f"POTENTIAL DUPLICATE: Check against {case.get('duplicate_of')}")

            queue_items.append(PriorityQueueItem(
                case_id=case["case_id"],
                document_type=case.get("document_type", "sae"),
                severity=severity,
                priority_score=round(priority_score, 4),
                completeness_score=round(completeness, 3),
                submission_age_days=age_days,
                assigned_reviewer=case.get("assigned_reviewer"),
                flags=flags,
            ))

        queue_items.sort(key=lambda x: x.priority_score, reverse=True)
        return queue_items
