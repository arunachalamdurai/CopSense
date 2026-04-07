"""
CopSense AI — Priority Engine
NLP keyword scoring for complaints & feedback sensitivity classification.
"""
import re
from typing import Literal

# ── Keyword weight tables ────────────────────────────────────────────────────
CRITICAL_KEYWORDS = [
    "murder", "killed", "rape", "kidnap", "abduct", "terrorist", "bomb",
    "shoot", "shot", "stab", "dead", "death", "homicide", "massacre",
    "हत्या", "बलात्कार", "अपहरण",
]
HIGH_KEYWORDS = [
    "assault", "attack", "violence", "threat", "threaten", "weapon", "gun",
    "knife", "missing", "disappear", "extort", "ransom", "arson", "robbery",
    "bribe", "corrupt", "misconduct", "abuse", "molest", "harass",
    "मारपीट", "धमकी", "गायब",
]
MEDIUM_KEYWORDS = [
    "theft", "steal", "stolen", "fraud", "cheat", "scam", "accident",
    "drunk", "fight", "dispute", "illegal", "forgery", "counterfeit",
    "चोरी", "धोखाधड़ी",
]
LOW_KEYWORDS = [
    "noise", "nuisance", "parking", "stray", "slow", "delay", "unhelpful",
    "rude", "complaint", "issue", "problem",
]


def _score_text(text: str) -> int:
    """Return raw score 0-100 based on keyword presence."""
    t = text.lower()
    score = 0
    for kw in CRITICAL_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', t):
            score += 35
    for kw in HIGH_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', t):
            score += 20
    for kw in MEDIUM_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', t):
            score += 10
    for kw in LOW_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', t):
            score += 3
    return min(score, 100)


def classify_complaint(text: str, complaint_type: str = "") -> tuple[str, int]:
    """
    Returns (priority_label, score).
    priority_label: 'critical' | 'high' | 'medium' | 'low'
    """
    score = _score_text(text)
    # Boost for certain complaint types
    ct = complaint_type.lower()
    if any(k in ct for k in ["murder", "rape", "kidnap", "terrorism"]):
        score = max(score, 85)
    elif any(k in ct for k in ["assault", "robbery", "missing"]):
        score = max(score, 55)

    if score >= 70:
        return "critical", score
    elif score >= 45:
        return "high", score
    elif score >= 20:
        return "medium", score
    else:
        return "low", score


def classify_feedback(text: str, rating: int = 3) -> tuple[str, int]:
    """
    NLP sensitivity classification for citizen feedback.
    Returns (sensitivity_label, score).
    sensitivity: 'critical' | 'high' | 'medium' | 'low'
    """
    score = _score_text(text)
    # Low rating amplifies scores
    if rating <= 1:
        score = min(int(score * 1.4), 100)
    elif rating == 2:
        score = min(int(score * 1.2), 100)

    if score >= 65:
        return "critical", score
    elif score >= 40:
        return "high", score
    elif score >= 15:
        return "medium", score
    else:
        return "low", score


def assign_case_priority(
    crime_type: str,
    days_pending: int,
    station_workload: int,
) -> str:
    """
    Smart Alert case assignment logic.
    Returns recommended priority for officer assignment.
    """
    base_score = 0
    ct = crime_type.lower()
    if any(k in ct for k in ["murder", "rape", "kidnap"]):
        base_score = 90
    elif any(k in ct for k in ["robbery", "assault", "missing"]):
        base_score = 65
    elif any(k in ct for k in ["theft", "fraud"]):
        base_score = 40
    else:
        base_score = 20

    # Escalate based on pending days
    if days_pending > 30:
        base_score += 25
    elif days_pending > 14:
        base_score += 10

    # Reduce workload bias for assignment
    workload_penalty = min(station_workload * 2, 20)
    final = max(base_score - workload_penalty, 5)
    final = min(final, 100)

    if final >= 70:
        return "critical"
    elif final >= 45:
        return "high"
    elif final >= 20:
        return "medium"
    else:
        return "low"
