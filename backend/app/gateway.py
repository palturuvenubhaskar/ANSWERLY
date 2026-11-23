"""Provider-neutral model gateway with OpenRouter and mock implementations."""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Protocol

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("answerly.gateway")


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


# ---------------------------------------------------------------------------
# OpenRouter gateway (real AI provider)
# ---------------------------------------------------------------------------

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Pricing per million tokens (input, output) for common models — used for cost estimation
_PRICING: dict[str, tuple[float, float]] = {
    "google/gemini-2.5-flash": (0.15, 0.60),
    "google/gemini-2.5-pro": (1.25, 10.00),
    "anthropic/claude-sonnet-4": (3.00, 15.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (2.50, 10.00),
}


class OpenRouterGateway:
    """Production gateway using the OpenRouter Chat Completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        generator_model: str | None = None,
        verifier_model: str | None = None,
        refiner_model: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.models = {
            "GENERATOR": generator_model or os.getenv("GENERATOR_MODEL", "google/gemini-2.5-flash"),
            "VERIFIER": verifier_model or os.getenv("VERIFIER_MODEL", "google/gemini-2.5-flash"),
            "REFINER": refiner_model or os.getenv("REFINER_MODEL", "google/gemini-2.5-flash"),
        }
        self.timeout = timeout or int(os.getenv("MODEL_TIMEOUT_SECONDS", "120"))
        self._client = httpx.Client(timeout=self.timeout)

    def generate(self, system_prompt: str, user_prompt: str, role: str) -> GatewayResponse:
        model = self.models.get(role, self.models["GENERATOR"])

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://answerly.app",
            "X-Title": "Answerly",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        start_ms = time.time()
        try:
            response = self._client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"OpenRouter API error: {exc.response.status_code} — {exc.response.text[:300]}"
            )
            raise RuntimeError(f"Model provider returned HTTP {exc.response.status_code}") from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError("Model provider request timed out") from exc

        latency_ms = int((time.time() - start_ms) * 1000)
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Estimate cost
        price_in, price_out = _PRICING.get(model, (0.50, 1.50))
        estimated_cost = round(
            (input_tokens * price_in + output_tokens * price_out) / 1_000_000, 6
        )

        return GatewayResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost=estimated_cost,
            provider="openrouter",
            model=model,
        )


# ---------------------------------------------------------------------------
# Mock gateway for offline testing and development
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Default gateway selection
# ---------------------------------------------------------------------------


def _create_default_gateway() -> ModelGateway:
    """Select gateway based on environment configuration."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if api_key:
        logger.info("Using OpenRouter gateway with real AI models")
        return OpenRouterGateway(api_key=api_key)
    else:
        logger.warning("No OPENROUTER_API_KEY set — using mock gateway (no real AI calls)")
        return MockDeterministicGateway()


default_gateway: ModelGateway = _create_default_gateway()
