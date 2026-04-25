# app/core/security.py
#
# Security utilities for phone hashing and token validation.
# These are separate from config to keep security logic isolated.

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.models import User


def normalize_phone_e164(phone: str) -> str:
    """
    Normalize a phone number to E.164 format.
    
    Removes all non-digit characters and ensures a leading +.
    Examples:
        +1 (260) 555-1234 → +12605551234
        2605551234 → +12605551234
        +12605551234 → +12605551234
    """
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", phone)
    
    # Add leading + if not present
    if not digits.startswith("+"):
        # Assume US country code if missing
        if digits.startswith("1") and len(digits) == 11:
            digits = "+" + digits
        elif len(digits) == 10:
            digits = "+1" + digits
        else:
            digits = "+" + digits
    
    return digits


def compute_phone_hash(phone: str, lookup_key: str) -> str:
    """
    Compute HMAC-SHA256 hash of a phone number for efficient lookup.
    
    Args:
        phone: Phone number in any format (will be normalized)
        lookup_key: The PHONE_LOOKUP_KEY from config
        
    Returns:
        64-character hex string
        
    FIX: Uses separate HMAC key to prevent rainbow table attacks.
    This is different from the ENCRYPTION_KEY used for PII at rest.
    """
    normalized = normalize_phone_e164(phone)
    
    # HMAC-SHA256 with the lookup key
    h = hashlib.sha256()
    h.update(lookup_key.encode())
    h.update(normalized.encode())
    
    return h.hexdigest()


def update_user_phone_hash(user: "User", phone: str | None, lookup_key: str) -> None:
    """
    Update a user's phone_hash field based on their phone_number.
    
    Called when phone_number is set or changed.
    
    Args:
        user: User instance to update
        phone: The raw phone number (will be normalized)
        lookup_key: The PHONE_LOOKUP_KEY from config
    """
    if phone:
        user.phone_hash = compute_phone_hash(phone, lookup_key)
    else:
        user.phone_hash = None