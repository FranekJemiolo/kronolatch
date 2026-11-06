"""
Unit tests for KronoLatch Astronomical Solar & Weather-Aware Leeway Engine (Phase 7).
"""

from __future__ import annotations

import datetime

from kronolatch.models import (
    Category,
    DAGParameters,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
)
from kronolatch.solar import SolarEngine


def test_solar_calculations_summer_vs_winter():
    """Verify astronomical calculations for summer vs winter solstices in Rome."""
    # Rome coordinates: 41.8967, 12.4822
    summer_date = datetime.date(2026, 6, 21)
    winter_date = datetime.date(2026, 12, 21)

    summer_solar = SolarEngine.calculate_solar_schedule(41.8967, 12.4822, date_val=summer_date)
    winter_solar = SolarEngine.calculate_solar_schedule(41.8967, 12.4822, date_val=winter_date)

    # In summer, sunrise is early (~05:30) and sunset is late (~20:45 CET)
    assert summer_solar.day_length_min > 14 * 60  # >14 hours of sunlight
    assert summer_solar.is_daylight("12:00")
    assert summer_solar.is_daylight("20:00")
    assert not summer_solar.is_past_twilight("21:00")

    # In winter, sunrise is later (~07:30) and sunset is early (~16:40 CET)
    assert winter_solar.day_length_min < 10 * 60  # <10 hours of sunlight
    assert winter_solar.is_daylight("12:00")
    assert not winter_solar.is_daylight("18:00")  # Already dark by 18:00
    assert winter_solar.is_past_twilight("18:30")


def test_daylight_audit_trip():
    """Verify detection of outdoor nodes scheduled past twilight and weather leeway."""
    winter_date = datetime.date(2026, 12, 21)

    # In winter in Rome, sunset is ~16:40, civil twilight ends ~17:15
    nodes = [
        TripNode(
            id="n1_forum",
            title="Roman Forum & Palatine Hill Walk",
            type=NodeType.FIXED,
            category=Category.SIGHTSEEING,
            transit_mode=TransitMode.WALK,
            transit_min=10,
            duration_min=90,
            fixed_start_min=14 * 60,  # 14:00 - 15:30 (Daylight OK)
            active=True,
        ),
        TripNode(
            id="n2_viewpoint",
            title="Piazzale Michelangelo Night Stroll",
            type=NodeType.FIXED,
            category=Category.SIGHTSEEING,
            transit_mode=TransitMode.WALK,
            transit_min=20,
            duration_min=60,
            fixed_start_min=18 * 60,  # 18:00 - 19:00 (Darkness violation!)
            active=True,
        ),
    ]

    trip = TripDAG(
        trip_id="rome-winter-tour",
        title="Rome Winter Walking Tour",
        destination="Rome, Italy",
        travelers=["Franek", "Anna"],
        parameters=DAGParameters(),
        nodes=nodes,
    )

    audit = SolarEngine.audit_trip_daylight(trip, date_val=winter_date, rain_probability=0.75)

    assert audit.outdoor_nodes_count == 2
    assert audit.daylight_compliant_count == 1  # Only n1 is in daylight
    assert len(audit.twilight_violations) >= 1  # n2 flagged for darkness
    assert "Piazzale Michelangelo" in audit.twilight_violations[0]

    # Weather buffer adjustment check
    assert audit.weather_risk_multiplier_applied == 1.25
    assert len(audit.recommendations) >= 1
