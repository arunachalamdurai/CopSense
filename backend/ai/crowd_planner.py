"""
CopSense AI — Crowd Planning Engine
Generates full deployment blueprints for events.
"""
import math
from datetime import datetime


def calculate_risk_score(
    crowd_size: int,
    duration_hrs: int,
    risk_level: str,
    vip_presence: bool = False,
    past_incidents: int = 0,
    event_type: str = "",
) -> int:
    """Compute 0-100 risk score."""
    score = 0

    # Crowd size component (0-40)
    if crowd_size >= 100_000:
        score += 40
    elif crowd_size >= 50_000:
        score += 32
    elif crowd_size >= 20_000:
        score += 24
    elif crowd_size >= 5_000:
        score += 15
    elif crowd_size >= 1_000:
        score += 8
    else:
        score += 3

    # Duration component (0-15)
    score += min(duration_hrs * 2, 15)

    # Risk level base
    rl = risk_level.lower()
    risk_map = {"low": 0, "medium": 15, "high": 25, "critical": 35}
    score += risk_map.get(rl, 15)

    # VIP / past incidents
    if vip_presence:
        score += 10
    score += min(past_incidents * 5, 20)

    # Event type adjustments
    et = event_type.lower()
    if any(k in et for k in ["political", "rally", "protest"]):
        score += 15
    elif any(k in et for k in ["religious", "festival"]):
        score += 10
    elif any(k in et for k in ["sports", "concert"]):
        score += 8

    return min(score, 100)


def generate_blueprint(
    event_name: str,
    location: str,
    crowd_size: int,
    duration_hrs: int,
    risk_score: int,
    event_type: str = "",
) -> dict:
    """
    Generate full AI deployment blueprint.
    Returns a structured dict with personnel, zones, routes.
    """
    # Officers needed
    base_ratio = 1 / 100   # 1 officer per 100 people
    if risk_score >= 70:
        base_ratio = 1 / 50
    elif risk_score >= 45:
        base_ratio = 1 / 75

    total_officers = max(math.ceil(crowd_size * base_ratio), 5)

    # Role split
    senior_officers = max(math.ceil(total_officers * 0.10), 1)
    inspectors       = max(math.ceil(total_officers * 0.15), 1)
    constables        = total_officers - senior_officers - inspectors

    # Support resources
    ambulances     = max(math.ceil(crowd_size / 10_000), 2)
    barricades     = max(math.ceil(crowd_size / 2_000), 5)
    cameras        = max(math.ceil(crowd_size / 5_000), 3)
    water_cannons  = 1 if risk_score >= 65 else 0
    swift_teams    = math.ceil(risk_score / 30)

    # Patrol zones
    n_zones = max(math.ceil(total_officers / 10), 3)
    zones = []
    for i in range(n_zones):
        sector = chr(65 + i)  # A, B, C ...
        zones.append({
            "zone":         f"Zone {sector}",
            "description":  f"Sector {sector} — {location}",
            "officers":     max(math.ceil(total_officers / n_zones), 2),
            "patrol_type":  "mobile" if i % 2 == 0 else "static",
            "priority":     "high" if i == 0 else ("medium" if i < n_zones // 2 else "low"),
        })

    # Entry/Exit points
    entry_points = [
        {"point": "Main Gate", "officers": senior_officers, "type": "entry_exit", "has_detector": True},
        {"point": "North Gate", "officers": max(inspectors // 2, 1), "type": "entry", "has_detector": risk_score >= 50},
        {"point": "South Gate", "officers": max(inspectors // 2, 1), "type": "exit", "has_detector": False},
    ]
    if risk_score >= 60:
        entry_points.append({"point": "Emergency Exit A", "officers": 2, "type": "emergency", "has_detector": False})

    # Emergency routes
    emergency_routes = [
        {"route": "Route 1", "to": "District Hospital", "distance_km": 3.2, "type": "medical"},
        {"route": "Route 2", "to": "Fire Station",       "distance_km": 2.1, "type": "fire"},
        {"route": "Route 3", "to": "Police HQ",          "distance_km": 1.8, "type": "evacuation"},
    ]

    risk_label = "Low Risk" if risk_score < 35 else ("Medium Risk" if risk_score < 65 else "High Risk")

    return {
        "event_name":   event_name,
        "location":     location,
        "crowd_size":   crowd_size,
        "duration_hrs": duration_hrs,
        "risk_score":   risk_score,
        "risk_label":   risk_label,
        "generated_at": datetime.utcnow().isoformat(),

        "personnel": {
            "total_officers": total_officers,
            "senior_officers": senior_officers,
            "inspectors":      inspectors,
            "constables":      constables,
            "swift_teams":     swift_teams,
        },
        "resources": {
            "ambulances":    ambulances,
            "barricades":    barricades,
            "cctv_cameras":  cameras,
            "water_cannons": water_cannons,
        },
        "patrol_zones":     zones,
        "entry_exit_points": entry_points,
        "emergency_routes": emergency_routes,
        "recommendations": _get_recommendations(risk_score, event_type),
    }


def _get_recommendations(risk_score: int, event_type: str) -> list[str]:
    recs = ["Conduct pre-event venue inspection 2 hours before start"]
    if risk_score >= 70:
        recs += [
            "Deploy SWIFT response team on standby",
            "Coordinate with district hospital for emergency beds",
            "Enable CCTV monitoring room with 24/7 surveillance",
            "Establish command post at main venue entry",
        ]
    elif risk_score >= 45:
        recs += [
            "Place plainclothes officers in crowd for intelligence",
            "Coordinate with local fire brigade",
            "Designate assembly points for emergency evacuation",
        ]
    else:
        recs += [
            "Standard patrol deployment sufficient",
            "Maintain communication with nearby PS for backup",
        ]
    if "political" in event_type.lower():
        recs.append("VIP security protocol — clear 50m perimeter around dignitaries")
    return recs
