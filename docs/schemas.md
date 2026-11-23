# Canonical Data Schemas

This document is the single source of truth for model outputs and serialized answer data. Implement these contracts in Pydantic and validate every model response before persistence.

## 1. AnswerContent
All generator/refiner outputs must match this structure.

```json
{
  "introduction": "A short opening paragraph.",
  "sections": [
    {
      "heading": "Main concept",
      "content": "Explanation in simple language.",
      "bullets": ["First point", "Second point"],
      "formula": null,
      "example": null
    }
  ],
  "conclusion": "A brief concluding statement.",
  "diagram_source": null
}
```

### Field rules
- `introduction`: required string; may be empty for very short answers.
- `sections`: required array; each section has required `heading`, `content`, `bullets`, `formula`, and `example`.
- `bullets`: array of strings; use an empty array when not needed.
- `formula`: nullable string containing plain text or LaTeX source; do not place executable code here.
- `example`: nullable string.
- `conclusion`: required string; may be empty for concise answers.
- `diagram_source`: nullable Mermaid source. Only include when a diagram materially helps. Render as text/diagram after sanitization; never execute arbitrary code.
- No unrecognized fields. Enforce reasonable maximum lengths and output token limits.

## 2. VerificationReport
```json
{
  "verdict": "needs_revision",
  "criteria": [
    {"name": "accuracy", "status": "pass", "notes": "No factual issue found."},
    {"name": "coverage", "status": "fail", "notes": "The second part is missing."},
    {"name": "marks_suitability", "status": "pass", "notes": "Appropriate detail."},
    {"name": "clarity", "status": "pass", "notes": "Clear wording."},
    {"name": "technical_details", "status": "pass", "notes": "No incorrect formula or example."},
    {"name": "source_consistency", "status": "pass", "notes": "No supplied source conflicts."},
    {"name": "citations", "status": "pass", "notes": "No unsupported citations."}
  ],
  "issues": [
    {
      "severity": "major",
      "category": "coverage",
      "description": "The second part of the question is missing.",
      "required_action": "Add a section explaining the second part."
    }
  ],
  "evidence_notes": ["Compared with supplied reference excerpt on page 4."],
  "confidence": 0.82
}
```

`verdict` is `approved` or `needs_revision`. Criterion status is `pass`, `fail`, or `uncertain`. Severity is `critical`, `major`, `minor`, or `suggestion`. Confidence is nullable numeric 0–1 and is not a correctness guarantee. Every report must include exactly one result for `accuracy`, `coverage`, `marks_suitability`, `clarity`, `technical_details`, `source_consistency`, and `citations`; use a passing result with an explicit not-applicable note when a criterion does not apply. An `approved` report is valid only when every criterion is `pass` and there is no critical or major issue. The orchestrator must enforce these rules after schema validation as well as in Pydantic; it must never infer approval from confidence. A suggestion alone does not force revision.

## 3. Question record
Required normalized fields: `question_text`, `position`, and `document_id`; optional metadata: `unit_id`, `question_number`, `section`, `marks`, `bl`, `co`, `source_page_start`, `source_page_end`, `extraction_confidence`. Preserve original extracted text separately from user-corrected text.

## 4. Job states
Question processing states:
`PENDING`, `QUEUED`, `GENERATING`, `VERIFYING`, `REVISING`, `RETRY_WAIT`, `VERIFIER_APPROVED`, `MANUAL_REVIEW`, `FAILED`, `CANCELLED`.

`VERIFIER_APPROVED` means the verifier approved the current answer version. It does not mean a person approved it. Human approval is a separate append-only `HumanApproval` record tied to an exact answer version, reviewer, and timestamp. Editing an answer creates a new version and does not carry approval forward.

`RETRY_WAIT` is operational, not an answer-quality verdict. Revision count is an integer from 0 through 2. Initial generation does not increment it.

## 5. Validation policy
- Use strict JSON parsing; reject markdown fences and trailing commentary if raw JSON is required.
- Validate all required fields and enum values.
- Do not silently coerce invalid types.
- On schema failure, allow a bounded format-repair attempt; record it as a model call, not an answer revision.
- Persist the raw response only in protected diagnostic storage with redaction and retention controls.
