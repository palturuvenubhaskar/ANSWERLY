from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AnswerSection(StrictModel):
    heading: str = Field(max_length=300)
    content: str = Field(max_length=20000)
    bullets: list[str] = Field(default_factory=list, max_length=100)
    formula: str | None = Field(default=None, max_length=5000)
    example: str | None = Field(default=None, max_length=10000)


class AnswerContent(StrictModel):
    introduction: str = Field(max_length=10000)
    sections: list[AnswerSection] = Field(max_length=100)
    conclusion: str = Field(max_length=10000)
    diagram_source: str | None = Field(default=None, max_length=20000)


class Criterion(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    status: Literal["pass", "fail", "uncertain"]
    notes: str = Field(default="", max_length=4000)


class VerificationIssue(StrictModel):
    severity: Literal["critical", "major", "minor", "suggestion"]
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=4000)
    required_action: str = Field(default="", max_length=4000)


class VerificationReport(StrictModel):
    verdict: Literal["approved", "needs_revision"]
    criteria: list[Criterion] = Field(min_length=1, max_length=30)
    issues: list[VerificationIssue] = Field(default_factory=list, max_length=100)
    evidence_notes: list[str] = Field(default_factory=list, max_length=100)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def approved_report_must_be_consistent(self):
        required = {
            "accuracy",
            "coverage",
            "marks_suitability",
            "clarity",
            "technical_details",
            "source_consistency",
            "citations",
        }
        names = [item.name for item in self.criteria]
        if len(names) != len(set(names)) or not required.issubset(names):
            raise ValueError("reports must include each required criterion exactly once")
        if self.verdict == "approved":
            if any(item.status != "pass" for item in self.criteria):
                raise ValueError("approved reports require every criterion to pass")
            if any(item.severity in {"critical", "major"} for item in self.issues):
                raise ValueError("approved reports cannot contain critical or major issues")
        return self


class RegisterRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class ProjectCreate(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class ProjectUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class DocumentResponse(StrictModel):
    id: str
    project_id: str
    title: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    sha256: str
    status: str
    extraction_warnings: list[str] = Field(default_factory=list)


class QuestionItemResponse(StrictModel):
    id: str
    position: int
    question_number: str | None = None
    section: str | None = None
    question_text: str
    original_text: str | None = None
    marks: int | None = None
    bl: str | None = None
    co: str | None = None
    source_page_start: int | None = None
    source_page_end: int | None = None
    extraction_confidence: float | None = None
    status: str


class DeleteProjectRequest(StrictModel):
    confirm: bool


class QuestionCreate(StrictModel):
    question_text: str = Field(min_length=1, max_length=20000)
    marks: int | None = Field(default=None, ge=1, le=1000)


class ReferenceExcerptCreate(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=50000)
    source_label: str = Field(min_length=1, max_length=500)
    page: int | None = Field(default=None, ge=1)


class AnswerCreate(StrictModel):
    answer: AnswerContent


class HumanApprovalCreate(StrictModel):
    answer_version_id: str = Field(min_length=36, max_length=36)
    decision: Literal["APPROVED", "REJECTED"]


class ProcessingRunCreate(StrictModel):
    question_ids: list[str] = Field(default_factory=list, max_length=500)
    reference_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def ids_must_be_unique(self):
        if len(self.question_ids) != len(set(self.question_ids)):
            raise ValueError("question_ids must not contain duplicates")
        if len(self.reference_ids) != len(set(self.reference_ids)):
            raise ValueError("reference_ids must not contain duplicates")
        return self
