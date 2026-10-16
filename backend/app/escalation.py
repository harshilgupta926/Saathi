from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

EscalationReason = Literal[
    "low_confidence",
    "explicit_human_request",
    "provider_failure",
    "safety_boundary",
]


@dataclass(frozen=True)
class EscalationDecision:
    escalate: bool
    reason: EscalationReason | None = None
    confidence: float = 1.0


class EscalationPolicy:
    def __init__(self, minimum_confidence: float = 0.65) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        self.minimum_confidence = minimum_confidence

    def evaluate(
        self,
        *,
        confidence: float,
        explicit_human_request: bool = False,
        provider_failed: bool = False,
        safety_boundary: bool = False,
    ) -> EscalationDecision:
        # Invalid provider/model confidence must not accidentally appear safe.
        if not isfinite(confidence):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        if explicit_human_request:
            return EscalationDecision(True, "explicit_human_request", confidence)
        if safety_boundary:
            return EscalationDecision(True, "safety_boundary", confidence)
        if provider_failed:
            return EscalationDecision(True, "provider_failure", confidence)
        if confidence < self.minimum_confidence:
            return EscalationDecision(True, "low_confidence", confidence)
        return EscalationDecision(False, None, confidence)
