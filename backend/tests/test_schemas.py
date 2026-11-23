import pytest
from pydantic import ValidationError

from app.schemas import (
    AnswerContent,
    AnswerSection,
    Criterion,
    HumanApprovalCreate,
    ProcessingRunCreate,
    VerificationIssue,
    VerificationReport,
)

REQUIRED_CRITERIA_NAMES = [
    "accuracy",
    "coverage",
    "marks_suitability",
    "clarity",
    "technical_details",
    "source_consistency",
    "citations",
]


def make_valid_criteria(all_pass=True):
    return [
        Criterion(name=name, status="pass" if all_pass else "fail", notes=f"{name} note")
        for name in REQUIRED_CRITERIA_NAMES
    ]


def test_verification_report_approved_success():
    report = VerificationReport(
        verdict="approved",
        criteria=make_valid_criteria(all_pass=True),
        issues=[],
        evidence_notes=["All verified."],
        confidence=0.95,
    )
    assert report.verdict == "approved"
    assert len(report.criteria) == 7


def test_verification_report_approved_fails_if_criterion_fails():
    criteria = make_valid_criteria(all_pass=True)
    criteria[0] = Criterion(name=criteria[0].name, status="fail", notes="incorrect formula")
    with pytest.raises(ValidationError, match="approved reports require every criterion to pass"):
        VerificationReport(
            verdict="approved",
            criteria=criteria,
            issues=[],
        )


def test_verification_report_approved_fails_if_major_issue():
    criteria = make_valid_criteria(all_pass=True)
    with pytest.raises(ValidationError, match="cannot contain critical or major issues"):
        VerificationReport(
            verdict="approved",
            criteria=criteria,
            issues=[
                VerificationIssue(
                    severity="major",
                    category="coverage",
                    description="Omitted part B",
                )
            ],
        )


def test_verification_report_needs_revision_with_failures():
    criteria = make_valid_criteria(all_pass=False)
    report = VerificationReport(
        verdict="needs_revision",
        criteria=criteria,
        issues=[
            VerificationIssue(
                severity="critical",
                category="accuracy",
                description="Hallucinated law",
                required_action="Provide exact statement",
            )
        ],
    )
    assert report.verdict == "needs_revision"
    assert len(report.issues) == 1


def test_verification_report_missing_criterion_raises():
    incomplete_criteria = [
        Criterion(name="accuracy", status="pass"),
        Criterion(name="coverage", status="pass"),
    ]
    with pytest.raises(ValidationError, match="include each required criterion exactly once"):
        VerificationReport(
            verdict="approved",
            criteria=incomplete_criteria,
        )


def test_answer_content_structure():
    content = AnswerContent(
        introduction="Intro text",
        sections=[
            AnswerSection(
                heading="Section 1",
                content="Body of section 1",
                bullets=["Point 1", "Point 2"],
                formula="E = mc^2",
                example="Relativity demo",
            )
        ],
        conclusion="Summary text",
    )
    assert content.introduction == "Intro text"
    assert len(content.sections) == 1
    assert content.sections[0].formula == "E = mc^2"


def test_processing_run_unique_ids_validator():
    with pytest.raises(ValidationError, match="question_ids must not contain duplicates"):
        ProcessingRunCreate(
            question_ids=["q1", "q1"],
            reference_ids=["r1"],
        )
