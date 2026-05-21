from __future__ import annotations

from domains.onboarding.state import OnboardingStep, VALID_TRANSITIONS


def can_transition(from_step: OnboardingStep, to_step: OnboardingStep) -> bool:
    return to_step in VALID_TRANSITIONS.get(from_step, [])


def transition(from_step: OnboardingStep, to_step: OnboardingStep) -> OnboardingStep:
    if not can_transition(from_step, to_step):
        raise ValueError(
            f"Cannot transition from {from_step.value} to {to_step.value}. "
            f"Allowed: {[s.value for s in VALID_TRANSITIONS.get(from_step, [])]}"
        )
    return to_step
