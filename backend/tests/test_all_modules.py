"""
RegAI Test Suite — covers all four AI modules with unit tests.
Run: pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


# ---------------------------------------------------------------------------
# Anonymisation tests
# ---------------------------------------------------------------------------

class TestAnonymisationEngine:
    def setup_method(self):
        from app.modules.anonymisation.engine import AnonymisationEngine
        self.engine = AnonymisationEngine(salt="test_salt_for_unit_testing")

    def test_india_aadhaar_detected(self):
        text = "Patient Aadhaar: 2345 6789 0123"
        result = self.engine.anonymise_text(text)
        assert "2345 6789 0123" not in result.anonymised_text
        assert result.entities_found.get("IN_AADHAAR", 0) > 0

    def test_india_pan_detected(self):
        text = "PAN number: ABCDE1234F"
        result = self.engine.anonymise_text(text)
        assert "ABCDE1234F" not in result.anonymised_text

    def test_india_phone_detected(self):
        text = "Contact: +91 98765 43210"
        result = self.engine.anonymise_text(text)
        assert "98765 43210" not in result.anonymised_text

    def test_age_generalised(self):
        text = "The 45 year old patient was admitted"
        result = self.engine.anonymise_text(text)
        assert "45 year old" not in result.anonymised_text
        assert "[AGE:" in result.anonymised_text

    def test_date_generalised(self):
        text = "Adverse event onset: 15/03/2024"
        result = self.engine.anonymise_text(text)
        assert "15/03/2024" not in result.anonymised_text
        assert "[DATE:" in result.anonymised_text

    def test_pseudonymisation_deterministic(self):
        text = "Patient: John Doe, phone: 9876543210"
        result1 = self.engine.anonymise_text(text)
        result2 = self.engine.anonymise_text(text)
        assert result1.pseudonymised_text == result2.pseudonymised_text

    def test_empty_text_handled(self):
        result = self.engine.anonymise_text("")
        assert result.anonymised_text == ""

    def test_token_format(self):
        text = "Aadhaar: 2345 6789 0123"
        result = self.engine.anonymise_text(text)
        for token in result.tokens:
            assert token.token.startswith("[")
            assert token.token.endswith("]")
            assert "-" in token.token


class TestPrivacyMetrics:
    def test_k_anonymity_computed(self):
        import pandas as pd
        from app.modules.anonymisation.engine import compute_privacy_metrics
        df = pd.DataFrame({
            "age_group": ["adult", "adult", "senior", "senior", "adult"],
            "gender": ["M", "M", "F", "F", "F"],
            "diagnosis": ["hypertension", "diabetes", "hypertension", "diabetes", "diabetes"]
        })
        metrics = compute_privacy_metrics(df, ["age_group", "gender"])
        assert metrics["k_anonymity"] >= 1
        assert "compliant_k5" in metrics

    def test_k_anonymity_noncompliant(self):
        import pandas as pd
        from app.modules.anonymisation.engine import compute_privacy_metrics
        df = pd.DataFrame({"age": ["25", "30", "45"], "name": ["A", "B", "C"]})
        metrics = compute_privacy_metrics(df, ["age"])
        assert metrics["compliant_k5"] == False


# ---------------------------------------------------------------------------
# Summarisation tests
# ---------------------------------------------------------------------------

class TestSummarisationEngine:
    """Tests that do not require Gemini API (test rule-based extraction only)."""

    def setup_method(self):
        from app.modules.summarisation.engine import SummarisationEngine
        self.engine = SummarisationEngine(gemini_api_key="test_key_no_api_call")

    def test_sugam_field_extraction(self):
        text = """
        Applicant: PharmaCorp Ltd
        Drug Name: TestDrugX
        Generic Name: testgenericname
        Dosage Form: Tablet
        Strength: 100mg
        Route of Administration: Oral
        """
        fields = self.engine._extract_sugam_fields(text)
        assert fields.get("applicant_name") is not None
        assert fields.get("drug_name") is not None
        assert fields.get("dosage_form") is not None

    def test_sae_demographics_extracted(self):
        text = "A 52 year old male patient weighing 75 kg was admitted."
        demo = self.engine._extract_patient_demographics(text)
        assert demo.get("age") == "52"
        assert demo.get("sex") == "male"

    def test_seriousness_detection_death(self):
        text = "The patient died on day 3 post-infusion."
        criteria = self.engine._detect_seriousness_criteria(text)
        assert "death" in criteria

    def test_seriousness_detection_hospitalisation(self):
        text = "Patient was hospitalised for 5 days due to severe reaction."
        criteria = self.engine._detect_seriousness_criteria(text)
        assert "hospitalisation" in criteria

    def test_causality_detection(self):
        text = "Causality was assessed as probable relationship to study drug."
        causality = self.engine._extract_causality(text)
        assert causality == "probable"

    def test_missing_causality_returns_none(self):
        text = "The patient recovered after discontinuation."
        causality = self.engine._extract_causality(text)
        assert causality is None

    def test_sae_key_flags_no_causality(self):
        text = "A 30 year old female was hospitalised. Drug: DrugY. Dose: 100mg."
        result = self.engine.summarise_sae(text)
        assert any("CAUSALITY" in flag for flag in result.key_flags)


# ---------------------------------------------------------------------------
# Completeness tests
# ---------------------------------------------------------------------------

class TestCompletenessEngine:
    def setup_method(self):
        from app.modules.completeness.engine import CompletenessEngine
        self.engine = CompletenessEngine()

    def test_field_found(self):
        from app.modules.completeness.engine import FieldStatus
        text = "Applicant Name: PharmaX Ltd\nAddress: Mumbai, India"
        status, value, issue = self.engine._check_field(text, "applicant_name")
        assert status == FieldStatus.PRESENT
        assert value is not None

    def test_field_missing(self):
        from app.modules.completeness.engine import FieldStatus
        text = "Applicant Name: PharmaX Ltd"
        status, value, issue = self.engine._check_field(text, "drug_name")
        assert status == FieldStatus.MISSING

    def test_field_incomplete_na(self):
        from app.modules.completeness.engine import FieldStatus
        text = "Drug Name: N/A"
        status, value, issue = self.engine._check_field(text, "drug_name")
        assert status == FieldStatus.INCOMPLETE

    def test_completeness_score_range(self):
        text = "Applicant Name: TestCo\nDrug Name: DrugA\nApplication Type: NDA"
        report = self.engine.check_completeness(text, "new_drug_application")
        assert 0.0 <= report.overall_score <= 1.0

    def test_verdict_complete(self):
        text = " ".join([
            "Applicant Name: PharmaCorp", "Address: Delhi", "Drug Name: DrugX",
            "Generic Name: genericname", "Application Type: NDA",
            "Date of Submission: 01/01/2024", "Contact Person: Dr. Smith",
            "Email: test@pharma.com", "Phone: 9876543210",
        ])
        report = self.engine.check_completeness(text, "new_drug_application")
        assert isinstance(report.verdict, str)
        assert len(report.verdict) > 0


class TestDocumentComparisonEngine:
    def setup_method(self):
        from app.modules.completeness.engine import DocumentComparisonEngine
        self.engine = DocumentComparisonEngine()

    def test_identical_documents_no_changes(self):
        text = "This is a clinical trial submission. Primary endpoint: reduction in HbA1c. Sample size: 300 patients."
        report = self.engine.compare(text, text)
        assert report.total_changes == 0

    def test_deleted_paragraph_detected(self):
        text_a = "First paragraph about safety data.\n\nSecond paragraph about efficacy.\n\nThird paragraph about manufacturing."
        text_b = "First paragraph about safety data.\n\nThird paragraph about manufacturing."
        report = self.engine.compare(text_a, text_b)
        assert report.total_changes > 0

    def test_severity_classification_critical_term(self):
        from app.modules.completeness.engine import ChangeSeverity
        original = "No deaths were observed in the study."
        revised = "Two deaths were reported in the treatment arm."
        severity = self.engine._classify_change_severity(original, revised, 0.3)
        assert severity == ChangeSeverity.CRITICAL

    def test_section_inference(self):
        clinical_text = "A total of 450 patients were enrolled in the phase 3 clinical trial."
        section = self.engine._infer_section(clinical_text)
        assert section == "clinical"


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

class TestClassificationEngine:
    def setup_method(self):
        from app.modules.classification.engine import ClassificationEngine, SeverityLevel
        self.engine = ClassificationEngine()
        self.SeverityLevel = SeverityLevel

    def test_death_classified(self):
        text = "Patient died on day 7 after receiving the study drug. Fatal outcome confirmed."
        result = self.engine.classify_severity(text, "test_case_death")
        assert result.predicted_severity == self.SeverityLevel.DEATH

    def test_hospitalisation_classified(self):
        text = "Patient was hospitalised for 3 days due to severe adverse reaction. Recovered fully."
        result = self.engine.classify_severity(text, "test_case_hosp")
        assert result.predicted_severity in [self.SeverityLevel.HOSPITALISATION, self.SeverityLevel.DEATH]

    def test_others_classified_mild(self):
        text = "Patient reported mild headache. No serious outcome. Resolved without treatment."
        result = self.engine.classify_severity(text, "test_case_mild")
        assert result.predicted_severity == self.SeverityLevel.OTHERS

    def test_confidence_in_range(self):
        text = "Patient died. Fatal."
        result = self.engine.classify_severity(text, "test_conf")
        assert 0.0 <= result.confidence <= 1.0

    def test_no_duplicate_empty_registry(self):
        result = self.engine.check_duplicate("Some case text", "new_case_001")
        assert result.is_duplicate == False

    def test_priority_queue_sorted(self):
        cases = [
            {"case_id": "C1", "severity": "others", "completeness_score": 1.0, "submission_age_days": 1},
            {"case_id": "C2", "severity": "death", "completeness_score": 0.9, "submission_age_days": 2},
            {"case_id": "C3", "severity": "hospitalisation", "completeness_score": 0.7, "submission_age_days": 5},
        ]
        queue = self.engine.build_priority_queue(cases)
        assert queue[0].case_id == "C2"  # death should be first
        assert all(queue[i].priority_score >= queue[i+1].priority_score for i in range(len(queue)-1))

    def test_death_flag_in_queue(self):
        cases = [{"case_id": "D1", "severity": "death", "completeness_score": 0.95, "submission_age_days": 1}]
        queue = self.engine.build_priority_queue(cases)
        assert any("DEATH" in f for f in queue[0].flags)

    def test_incomplete_flag_in_queue(self):
        cases = [{"case_id": "I1", "severity": "others", "completeness_score": 0.4, "submission_age_days": 3}]
        queue = self.engine.build_priority_queue(cases)
        assert any("INCOMPLETE" in f for f in queue[0].flags)

    def test_overdue_flag_in_queue(self):
        cases = [{"case_id": "O1", "severity": "others", "completeness_score": 0.9, "submission_age_days": 20}]
        queue = self.engine.build_priority_queue(cases)
        assert any("OVERDUE" in f for f in queue[0].flags)
