"""
CopSense AI — Emergency Response Optimizer
Haversine GPS distance + multi-factor officer scoring.
"""
import math
from typing import Any


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in km between two GPS coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


VEHICLE_SPEED_KMH = {
    "pcr_van":    40,
    "motorcycle": 35,
    "foot":       5,
    "car":        45,
}

STATUS_MULTIPLIER = {
    "available":  1.0,
    "patrolling": 1.3,  # slight delay to disengage
    "engaged":    2.5,  # major delay
    "off_duty":   3.0,
}

INCIDENT_TYPE_WEIGHTS = {
    "assault":  {"armed_bonus": 25, "pcr_bonus": 10},
    "robbery":  {"armed_bonus": 20, "pcr_bonus": 8},
    "missing":  {"detective_bonus": 15, "pcr_bonus": 5},
    "fire":     {"pcr_bonus": 15, "armed_bonus": 0},
    "accident": {"medical_bonus": 20, "pcr_bonus": 12},
    "default":  {"armed_bonus": 5,  "pcr_bonus": 5},
}


def score_officer(
    officer: dict,
    incident_lat: float,
    incident_lng: float,
    incident_type: str,
    severity: str = "high",
) -> dict:
    """
    Score an officer for an incident.
    Returns officer dict augmented with: dist_km, eta_min, ai_score.
    """
    dist = haversine_km(officer["lat"], officer["lng"], incident_lat, incident_lng)

    vehicle   = officer.get("vehicle", "foot").lower().replace(" ", "_")
    speed     = VEHICLE_SPEED_KMH.get(vehicle, 10)
    status    = officer.get("status", "available").lower()
    mult      = STATUS_MULTIPLIER.get(status, 2.0)

    eta_min = max(2, round((dist / speed) * 60 * mult))

    # Base score — lower is better (time-based)
    base_score = eta_min

    # Penalties / bonuses
    weights = INCIDENT_TYPE_WEIGHTS.get(incident_type, INCIDENT_TYPE_WEIGHTS["default"])
    if officer.get("armed") and weights.get("armed_bonus", 0):
        base_score -= weights["armed_bonus"]
    if "pcr" in vehicle and weights.get("pcr_bonus", 0):
        base_score -= weights["pcr_bonus"]
    if status == "engaged":
        base_score += 20
    if status == "available":
        base_score -= 5
    if severity == "critical" and officer.get("rank_level", 1) >= 2:
        base_score -= 8  # prefer senior officers for critical incidents

    return {
        **officer,
        "dist_km": round(dist, 2),
        "eta_min": eta_min,
        "ai_score": max(base_score, 1),
    }


def rank_officers(
    officers: list[dict],
    incident_lat: float,
    incident_lng: float,
    incident_type: str = "assault",
    severity: str = "high",
    top_n: int = 5,
) -> list[dict]:
    """
    Return top_n officers ranked by AI score (ascending = best).
    Officers must include: id, name, lat, lng, status, vehicle, armed.
    """
    scored = [
        score_officer(o, incident_lat, incident_lng, incident_type, severity)
        for o in officers
    ]
    scored.sort(key=lambda x: x["ai_score"])
    return scored[:top_n]


def explain_recommendation(officer: dict) -> str:
    """Generate human-readable explanation for the recommendation."""
    lines = [
        f"{officer['name']} selected as optimal unit.",
        f"Distance: {officer['dist_km']} km | ETA: {officer['eta_min']} min.",
    ]
    if officer.get("armed"):
        lines.append("Armed officer — suitable for violent incidents.")
    if "pcr" in officer.get("vehicle", "").lower():
        lines.append("PCR Van available — fast response vehicle.")
    return " ".join(lines)
