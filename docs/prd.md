# Product Requirements Document — Answerly

## 1. Product summary
Answerly converts question-bank documents into organized, exam-oriented answers. A user uploads a question bank, reviews extracted questions, generates answers in parallel, checks them through an independent verification pass, revises weak answers automatically, and exports the result.

## 2. Target user and problem
Primary users are students who need clear answers organized by unit, question, and marks. Manually splitting a PDF, writing each answer, checking completeness, and formatting a final document is repetitive and time-consuming.

## 3. Core user journey
1. User creates or opens a project.
2. User uploads a PDF or DOCX question bank.
3. System extracts units, sections, questions, marks, BL/CO metadata when present.
4. User reviews and corrects extraction.
5. User selects questions and starts processing.
6. Each question is independently generated, verified, and revised if needed.
7. User reviews approved and manual-review answers.
8. User exports selected answers to PDF, DOCX, Markdown, or JSON.

## 4. MVP functional requirements
- Project create/list/open/rename/delete.
- Upload PDF and DOCX; scanned PDF pages use OCR fallback.
- Validate file type, content, and configurable maximum size (initial default: 30 MB).
- Preserve original question wording, order, unit, page provenance, and marks when available.
- Extraction preview with manual correction.
- Let users attach plain-text reference excerpts with source labels and page numbers to a project; they can select excerpts for a processing run.
- Process questions independently with bounded parallelism.
- Generate answers suited to marks and simple student-friendly language.
- Independent verification for accuracy, coverage, clarity, marks suitability, and source consistency.
- Up to two automatic answer revisions after initial generation.
- Manual review after unsuccessful revisions.
- Live progress, retry, cancel, edit, approve, and regenerate controls.
- Export PDF, DOCX, Markdown, and JSON.
- Maintain answer history and model/token/cost metadata.

## 5. Non-functional requirements
- Secure project-level authorization on every API operation.
- Private file storage; no public upload URLs by default.
- Idempotent job creation and safe worker redelivery.
- Bounded concurrency, rate limits, timeouts, and retries.
- Observable job states and actionable failures.
- Responsive UI and accessible status communication.
- Retention defaults: source files 30 days after upload at most; exports 7 days after creation; operational metadata logs 30 days; rolling backups at most 30 days. Project content remains until the user deletes it. Raw prompts and provider responses are not retained by default.
- Send question/reference content only to configured model providers that do not use it for training and whose disclosed retention is no more than 30 days. Disclose the provider before processing; disable providers that cannot meet this policy.

## 6. Out of scope for MVP
- Native mobile applications.
- Real-time collaborative editing.
- Guaranteed factual correctness or official grading.
- Automatic textbook citation discovery.
- Fine-tuning custom models.
- Multi-tenant institution administration and payment/billing.

## 7. Success measures
Track extraction completeness on labeled documents, human-rated answer correctness/completeness/simplicity, percentage of answers approved without manual intervention, processing latency, provider failure rate, and estimated cost per question. Targets must be set after collecting a baseline on the evaluation set; do not invent performance claims before measurement.

## 8. Product principles
Preserve source wording; make uncertainty visible; optimize for clear exam-ready explanations rather than verbosity; allow users to inspect and edit every answer; never imply that AI verification guarantees correctness.
