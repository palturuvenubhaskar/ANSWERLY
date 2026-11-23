from dataclasses import dataclass
import json
import time
from typing import Protocol


@dataclass(frozen=True)
class GatewayResponse:
    content: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost: float
    provider: str
    model: str


class ModelGateway(Protocol):
    def generate(self, system_prompt: str, user_prompt: str, role: str) -> GatewayResponse:
        ...


class MockDeterministicGateway:
    """Deterministic gateway for offline testing and development verification."""

    def __init__(self, mode: str = "pass"):
        """mode can be 'pass', 'revise_then_pass', or 'always_fail'."""
        self.mode = mode
        self.call_count = 0

    def generate(self, system_prompt: str, user_prompt: str, role: str) -> GatewayResponse:
        self.call_count += 1
        start_time = time.time()

        if role in ("GENERATOR", "REFINER"):
            data = {
                "introduction": "This is a structured exam-oriented answer providing core principles.",
                "sections": [
                    {
                        "heading": "Core Analysis",
                        "content": "Detailed step-by-step breakdown of the concept and mechanisms.",
                        "bullets": ["Primary axiom", "Operational boundary", "Performance constraint"],
                        "formula": "O(V + E)",
                        "example": "Standard directed acyclic graph implementation.",
                    }
                ],
                "conclusion": "In summary, the method ensures optimal efficiency and determinism.",
                "diagram_source": None,
            }
            content = json.dumps(data)
        elif role == "VERIFIER":
            if self.mode == "pass" or (self.mode == "revise_then_pass" and self.call_count > 2):
                data = {
                    "verdict": "approved",
                    "criteria": [
                        {"name": "accuracy", "status": "pass", "notes": "Factual accuracy verified."},
                        {"name": "coverage", "status": "pass", "notes": "All question parts addressed."},
                        {"name": "marks_suitability", "status": "pass", "notes": "Depth matches marks."},
                        {"name": "clarity", "status": "pass", "notes": "Clear phrasing."},
                        {"name": "technical_details", "status": "pass", "notes": "Formulas intact."},
                        {"name": "source_consistency", "status": "pass", "notes": "Consistent with references."},
                        {"name": "citations", "status": "pass", "notes": "Proper reference labels."},
                    ],
                    "issues": [],
                    "evidence_notes": ["Criteria met"],
                    "confidence": 0.96,
                }
            else:
                data = {
                    "verdict": "needs_revision",
                    "criteria": [
                        {"name": "accuracy", "status": "fail", "notes": "Requires more precise time complexity."},
                        {"name": "coverage", "status": "pass", "notes": "Covered."},
                        {"name": "marks_suitability", "status": "pass", "notes": "Adequate."},
                        {"name": "clarity", "status": "pass", "notes": "Adequate."},
                        {"name": "technical_details", "status": "fail", "notes": "Missing boundary equation."},
                        {"name": "source_consistency", "status": "pass", "notes": "Consistent."},
                        {"name": "citations", "status": "pass", "notes": "Cited."},
                    ],
                    "issues": [
                        {
                            "severity": "major",
                            "category": "technical_details",
                            "description": "Specify exact boundary condition for cyclic inputs.",
                            "required_action": "Add explicit boundary note.",
                        }
                    ],
                    "evidence_notes": ["Revision needed for boundary cases."],
                    "confidence": 0.88,
                }
            content = json.dumps(data)
        else:
            raise ValueError(f"Unknown gateway role: {role}")

        latency = int((time.time() - start_time) * 1000) + 10
        return GatewayResponse(
            content=content,
            input_tokens=150,
            output_tokens=220,
            latency_ms=latency,
            cost=0.00045,
            provider="mock-ai",
            model="mock-v1",
        )


default_gateway = MockDeterministicGateway()
