"""Evaluation baseline runner for Answerly.

Runs the labeled evaluation question set defined in docs/evaluation.md
and computes quality and operational metrics according to the rubric.
"""

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.gateway import default_gateway, MockDeterministicGateway
from backend.app.prompts import (
    GENERATOR_SYSTEM_PROMPT,
    VERIFIER_SYSTEM_PROMPT,
    format_generator_prompt,
    format_verifier_prompt,
)
from backend.app.schemas import AnswerContent, VerificationReport

LABELED_EVALUATION_DATA = [
    {
        "unit": "Unit I",
        "question_number": "1",
        "question_text": "Define Artificial Intelligence and differentiate between Strong AI and Weak AI.",
        "marks": 5,
        "bloom_level": "L1",
        "course_outcome": "CO1",
        "expected_coverage": [
            "Definition of AI",
            "Strong AI (General Intelligence, consciousness)",
            "Weak AI (Narrow, specialized tasks)",
            "Concrete examples",
        ],
    },
    {
        "unit": "Unit II",
        "question_number": "2",
        "question_text": "Explain Breadth-First Search (BFS) and Depth-First Search (DFS) with a comparative example.",
        "marks": 10,
        "bloom_level": "L2",
        "course_outcome": "CO2",
        "expected_coverage": [
            "BFS mechanics (Queue, FIFO, level by level)",
            "DFS mechanics (Stack/Recursion, LIFO, branch by branch)",
            "Time and space complexity formulas",
            "Comparative example or graph traversal trace",
            "Completeness and optimality comparison",
        ],
    },
    {
        "unit": "Unit III",
        "question_number": "3",
        "question_text": "State and derive Bayes' Theorem. Explain its application in probabilistic reasoning.",
        "marks": 10,
        "bloom_level": "L3",
        "course_outcome": "CO3",
        "expected_coverage": [
            "Mathematical formulation: P(A|B) = P(B|A)P(A)/P(B)",
            "Derivation from joint probability and product rule",
            "Explanation of Prior, Likelihood, Posterior, and Marginal Evidence",
            "Application in diagnostic reasoning or classification",
        ],
    },
    {
        "unit": "Unit IV",
        "question_number": "4",
        "question_text": "Explain Decision Tree learning, Entropy, and Information Gain with mathematical formulas.",
        "marks": 10,
        "bloom_level": "L3",
        "course_outcome": "CO4",
        "expected_coverage": [
            "Decision Tree tree representation and splitting principle",
            "Entropy formula: H(S) = - sum(p_i * log2(p_i))",
            "Information Gain formula: IG(S, A) = H(S) - sum(|S_v|/|S| * H(S_v))",
            "ID3 / C4.5 attribute selection mechanism",
        ],
    },
    {
        "unit": "Unit V",
        "question_number": "5",
        "question_text": "Describe the architecture of an Expert System with reference to MYCIN rule-based reasoning.",
        "marks": 10,
        "bloom_level": "L2",
        "course_outcome": "CO5",
        "expected_coverage": [
            "Core components: Knowledge Base, Inference Engine, Working Memory, UI/Explanation",
            "Rule-based IF-THEN paradigm",
            "Certainty factors (CF) handling in MYCIN",
            "Backward chaining inference methodology",
        ],
    },
]


@dataclass
class ItemEvalResult:
    unit: str
    question_text: str
    marks: int
    schema_valid: bool
    verdict: str
    criteria_passed: int
    criteria_total: int
    latency_ms: int
    estimated_cost: float
    coverage_score: float


def run_evaluation(gateway=None) -> dict:
    gw = gateway or default_gateway
    print("=" * 70)
    print("  ANSWERLY QUALITY EVALUATION BASELINE RUNNER")
    print(f"  Gateway Provider: {getattr(gw, 'provider', type(gw).__name__)}")
    print(f"  Evaluation Set: {len(LABELED_EVALUATION_DATA)} accredited questions")
    print("=" * 70)

    results: list[ItemEvalResult] = []
    total_latency = 0
    total_cost = 0.0

    for idx, item in enumerate(LABELED_EVALUATION_DATA, 1):
        print(f"\n[{idx}/{len(LABELED_EVALUATION_DATA)}] Evaluating {item['unit']}: Q{item['question_number']}...")
        start_time = time.time()

        # Step 1: Generator
        gen_prompt = format_generator_prompt(item["question_text"], item["marks"], [])
        gen_resp = gw.generate(GENERATOR_SYSTEM_PROMPT, gen_prompt, role="GENERATOR")

        schema_valid = False
        parsed_answer = None
        try:
            parsed_answer = AnswerContent.model_validate_json(gen_resp.content)
            schema_valid = True
        except Exception as exc:
            print(f"   [!] Generator Schema Validation Error: {exc}")

        # Step 2: Verifier
        ver_prompt = format_verifier_prompt(
            item["question_text"],
            item["marks"],
            parsed_answer.model_dump(mode="json") if parsed_answer else {},
            [],
        )
        ver_resp = gw.generate(VERIFIER_SYSTEM_PROMPT, ver_prompt, role="VERIFIER")

        verdict = "unknown"
        passed_criteria = 0
        total_criteria = 7
        try:
            report = VerificationReport.model_validate_json(ver_resp.content)
            verdict = report.verdict
            passed_criteria = sum(1 for c in report.criteria if c.status == "pass")
            total_criteria = len(report.criteria)
        except Exception as exc:
            print(f"   [!] Verifier Report Validation Error: {exc}")

        # Basic coverage check against labeled coverage points
        answer_text = ""
        if parsed_answer:
            answer_text = (
                parsed_answer.introduction
                + " "
                + " ".join(s.content for s in parsed_answer.sections)
                + " "
                + parsed_answer.conclusion
            ).lower()

        matched_points = sum(
            1 for pt in item["expected_coverage"] if any(w in answer_text for w in pt.lower().split()[:2])
        )
        coverage_score = round(matched_points / len(item["expected_coverage"]), 2)

        item_latency = gen_resp.latency_ms + ver_resp.latency_ms
        item_cost = gen_resp.cost + ver_resp.cost
        total_latency += item_latency
        total_cost += item_cost

        result = ItemEvalResult(
            unit=item["unit"],
            question_text=item["question_text"][:60] + "...",
            marks=item["marks"],
            schema_valid=schema_valid,
            verdict=verdict,
            criteria_passed=passed_criteria,
            criteria_total=total_criteria,
            latency_ms=item_latency,
            estimated_cost=item_cost,
            coverage_score=coverage_score,
        )
        results.append(result)
        print(f"   -> Verdict: {verdict.upper()} ({passed_criteria}/{total_criteria} criteria) | Latency: {item_latency}ms | Cost: ${item_cost:.5f}")

    print("\n" + "=" * 70)
    print("  EVALUATION SUMMARY & RELEASE GATES")
    print("=" * 70)
    n = len(results)
    approved_count = sum(1 for r in results if r.verdict == "approved")
    schema_valid_count = sum(1 for r in results if r.schema_valid)
    avg_latency = round(total_latency / n, 1) if n else 0
    avg_cost = round(total_cost / n, 6) if n else 0

    print(f"  Total Items:              {n}")
    print(f"  Schema Validity Rate:     {schema_valid_count}/{n} ({(schema_valid_count/n)*100:.0f}%)")
    print(f"  Verifier Approval Rate:   {approved_count}/{n} ({(approved_count/n)*100:.0f}%)")
    print(f"  Mean Latency / Question:  {avg_latency} ms")
    print(f"  Mean Cost / Question:     ${avg_cost:.6f}")
    print("=" * 70)

    summary = {
        "total_items": n,
        "schema_valid_rate": schema_valid_count / n,
        "verifier_approval_rate": approved_count / n,
        "mean_latency_ms": avg_latency,
        "mean_cost_usd": avg_cost,
        "items": [asdict(r) for r in results],
    }

    # Save artifact
    output_path = Path("docs/evaluation_results.json")
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  Detailed evaluation results saved to: {output_path}")
    return summary


if __name__ == "__main__":
    run_evaluation()
