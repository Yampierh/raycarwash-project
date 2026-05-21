from __future__ import annotations

import enum


class OnboardingStep(str, enum.Enum):
    PENDING_REGISTRATION = "pending_registration"
    PROFILE_CREATION = "profile_creation"
    ROLE_ASSIGNMENT = "role_assignment"
    KYC_PENDING = "kyc_pending"
    KYC_SUBMITTED = "kyc_submitted"
    KYC_REJECTED = "kyc_rejected"
    COMPLETED = "completed"


VALID_TRANSITIONS: dict[OnboardingStep, list[OnboardingStep]] = {
    OnboardingStep.PENDING_REGISTRATION: [OnboardingStep.PROFILE_CREATION],
    OnboardingStep.PROFILE_CREATION: [OnboardingStep.ROLE_ASSIGNMENT, OnboardingStep.COMPLETED, OnboardingStep.KYC_PENDING],
    OnboardingStep.ROLE_ASSIGNMENT: [OnboardingStep.COMPLETED, OnboardingStep.KYC_PENDING],
    OnboardingStep.KYC_PENDING: [OnboardingStep.KYC_SUBMITTED],
    OnboardingStep.KYC_SUBMITTED: [OnboardingStep.COMPLETED, OnboardingStep.KYC_REJECTED],
    OnboardingStep.KYC_REJECTED: [OnboardingStep.KYC_SUBMITTED],
    OnboardingStep.COMPLETED: [],
}

INITIAL_STEP: OnboardingStep = OnboardingStep.PENDING_REGISTRATION
