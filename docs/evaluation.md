# Quality Evaluation Plan

## Purpose
Measure extraction quality and answer usefulness with human-reviewed examples. LLM self-evaluation alone is not a sufficient quality measure.

## 1. Labeled evaluation set
Start with representative questions from the user's question-bank corpus, covering:
- short definition questions;
- multi-part 10-mark explanations;
- formulas and calculations;
- algorithms with examples;
- questions with diagrams;
- OCR/scanned source pages;
- questions with missing marks or ambiguous boundaries.

For every item, record the source document/page, expected question text, expected metadata, required answer coverage points, and reviewer notes. Do not publish private source documents in a public test set.

## 2. Extraction metrics
- Question recall: expected questions extracted / expected questions in the labeled set.
- Exact-text preservation: proportion whose normalized text matches reviewer-approved text.
- Metadata accuracy: marks/unit/number/BL/CO accuracy where present.
- Provenance accuracy: correct page/range assignment.
- Ambiguity detection: proportion of uncertain cases correctly flagged.

Report results by source type (digital PDF, scanned PDF, DOCX). Never hide missed questions inside an aggregate score.

## 3. Answer rubric
Human reviewers score each dimension from 1 to 5:
- Accuracy: facts, definitions, formulas, calculations.
- Completeness: every requested subpart is addressed.
- Marks suitability: depth appropriate for assigned marks.
- Simplicity: understandable student-friendly language.
- Organization: headings, sequence, examples, conclusion.
- Source fidelity: consistency with supplied references and no fabricated citations.

Track severe factual errors separately; a high average score must not mask them.

## 4. Verification performance
Measure verifier precision/recall on known seeded errors:
- omitted sub-question;
- wrong formula;
- incorrect calculation;
- unsupported claim;
- excessive/irrelevant content.
Track false approvals and unnecessary revision requests. Human adjudication is the reference label.

## 5. Operational metrics
Record median and p95 processing time per question, provider failure/retry rate, tokens per role, estimated cost per question, queue wait time, and manual-review rate. Compare models using the same evaluation set and prompt version.

## 6. Initial sample
Use a small balanced sample from the supplied AI question bank, for example:
- Unit I: definition of Artificial Intelligence.
- Unit II: BFS and DFS.
- Unit III: Bayes' theorem.
- Unit IV: Decision Tree Learning, Entropy, and Information Gain.
- Unit V: Expert System and MYCIN.
Confirm the exact source wording and pages when building the fixture set.

## 7. Release gates
Set numeric thresholds only after a baseline run and human review. At minimum:
- No silent question loss in the labeled extraction set.
- No critical seeded error is repeatedly false-approved without being documented.
- All export formats pass structural validation.
- No cross-user data access.
- No unbounded retry/revision/concurrency behavior.
- Human reviewers judge output acceptable for study support and understand that AI can make mistakes.
