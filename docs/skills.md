# Reusable Workflows and Agent Skills

This file is the project-level workflow specification. It is **not by itself** an executable OpenCode skill. If OpenCode skills are required, create separate files under `.opencode/skills/<skill-name>/SKILL.md` and follow the installed OpenCode skill format.

## Parse Question Bank
**Input:** document ID, source file, extraction settings.
1. Extract text page-by-page or paragraph/table-by-paragraph.
2. Preserve page/paragraph provenance.
3. Detect units, sections, question boundaries, question number, marks, BL, and CO.
4. Join wrapped lines without changing source wording.
5. Flag ambiguous boundaries and low-confidence OCR.
6. Validate each record against the Question schema.
**Output:** questions plus warnings and provenance.

## Classify Question
1. Prefer explicit source labels.
2. Preserve marks as supplied; do not invent missing marks.
3. Identify every subtask (define, compare, explain, calculate, discuss, etc.).
4. Build a coverage checklist and answer outline.
5. Record uncertainty when metadata conflicts or is missing.

## Generate Exam Answer
1. Read the exact question and its metadata.
2. Use only authorized reference excerpts, retaining provenance.
3. Build a coverage checklist.
4. Generate canonical `AnswerContent`.
5. Validate the output schema and return it with model-call metadata.

## Verify Answer
1. Compare every question requirement with the answer.
2. Check facts, formulas, calculations, examples, and diagrams.
3. Assess marks suitability and clarity.
4. Check supplied references and source citations.
5. Return a structured `VerificationReport` with actionable corrections.

## Refine Answer
1. Preserve accurate content.
2. Address all required verifier issues.
3. Avoid unsupported expansion.
4. Return the complete canonical `AnswerContent`.
5. Validate before saving a new immutable version.

## Export Question Bank
1. Load selected questions in original unit/question order.
2. Use canonical answer JSON.
3. Render PDF, DOCX, Markdown, or JSON.
4. Escape special characters and render equations safely.
5. Include status labels for unapproved/manual-review answers when selected.
6. Verify every selected question appears exactly once.
