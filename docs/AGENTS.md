# Runtime AI Agents

This document defines the LLM roles used at runtime. The deterministic orchestrator owns state transitions; LLMs do not control workflow state.

## 1. Answer Generator
**Input:** exact question, marks, unit/course context, answer settings, and optional trusted reference excerpts with provenance.

**Responsibilities**
- Answer every requested part.
- Match detail to marks without padding.
- Use simple, student-friendly language.
- Include examples, equations, calculations, algorithms, or diagrams only when relevant.
- Ground claims in supplied references when the user asks for source-based answers.
- Return only the canonical `AnswerContent` structure in `schemas.md`.

**Guidance:** 2 marks = concise definition/key points; 5 marks = moderate explanation and useful example; 10 marks = introduction, organized sections, relevant examples/formulas/diagrams, and conclusion. Marks are guidance, not a rigid word-count rule.

## 2. Independent Verifier
Use a different model/provider from the generator when practical. If not possible, record that the same provider was used.

Check:
1. Factual and technical accuracy.
2. Coverage of every instruction and sub-question.
3. Suitability for marks and expected academic level.
4. Clarity and simple wording.
5. Correctness of formulas, calculations, examples, and diagram descriptions.
6. Consistency with supplied references.
7. Unsupported claims or fabricated citations.

Return `VerificationReport` from `schemas.md`, including a verdict, criterion results, actionable issues, and evidence notes. Do not approve an answer just because it is fluent. Distinguish must-fix errors from optional improvements.

## 3. Answer Refiner
**Input:** exact question, current answer version, verifier report, and the same reference excerpts.

- Fix all required factual and coverage issues.
- Preserve correct content.
- Do not introduce unsupported claims.
- Keep the answer mark-appropriate and readable.
- Return the complete revised `AnswerContent`, not a patch.

## 4. Deterministic Orchestrator
Application code, not an LLM. It validates schemas, stores immutable versions, enforces revision limits, handles retries/timeouts/cancellation, and chooses terminal states.

## Quality caveat
Automated verification reduces obvious errors but cannot guarantee correctness. The UI must expose verification status and allow user review/editing. After two unsuccessful revisions, route the question to `MANUAL_REVIEW`.
