from __future__ import annotations

import re
from typing import Any


def scope_check_request(user_request: str) -> dict[str, Any]:
    original = user_request.strip()
    text = original.lower()

    if not original:
        return {
            "allowed": False,
            "sanitized_request": original,
            "was_sanitized": False,
            "reason": "Empty story request.",
        }

    refusal_patterns = [
        (r"\b(horror story|violent horror|graphic horror)\b", "violent or intense horror"),
        (r"\b(sexual|erotic|porn|explicit|adult story|for adults)\b", "adult or sexual content"),
        (r"\b(gore|bloody|torture|murder|kill)\b", "graphic violence"),
        (r"\b(diagnose|diagnosis|medical advice|prescribe|dosage)\b", "medical advice"),
        (r"\b(hide a crime|cover up a crime|get away with|break into)\b", "crime or evasion"),
        (r"\b(make a bomb|poison someone|self harm|suicide)\b", "dangerous instructions"),
    ]

    for pattern, reason in refusal_patterns:
        if re.search(pattern, text):
            return {
                "allowed": False,
                "sanitized_request": original,
                "was_sanitized": False,
                "reason": f"Request is out of scope because it asks for {reason}.",
            }

    sanitized = original
    replacements = [
        (r"\bspooky\b", "mysterious"),
        (r"\bscary forest\b", "moonlit forest"),
        (r"\bscary\b", "surprising"),
        (
            r"\bfights? monsters\b|\bfighting monsters\b|\bfight monsters\b",
            "solves a gentle mystery with friendly creatures",
        ),
    ]

    reasons: list[str] = []
    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        if updated != sanitized:
            sanitized = updated
            reasons.append(f"Softened '{pattern}' into bedtime-safe language.")

    return {
        "allowed": True,
        "sanitized_request": sanitized,
        "was_sanitized": sanitized != original,
        "reason": " ".join(reasons) if reasons else None,
    }

