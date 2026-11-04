"""
Tests for KronoLatch Live Transit & Public Rail Delay Telemetry.
"""

from __future__ import annotations

from kronolatch.dag_engine import validate_dag
from kronolatch.live_transit import LiveTrainStatus, LiveTransitClient
from kronolatch.models import (
    Category,
    DAGParameters,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
)


def test_extract_train_number():
    """Verify regex extraction of train numbers."""
    assert LiveTransitClient.extract_train_number("Frecciarossa 9540") == "9540"
    assert LiveTransitClient.extract_train_number("Train FR 3305 Express") == "3305"
    assert LiveTransitClient.extract_train_number("Italo 9912") == "9912"
    assert LiveTransitClient.extract_train_number("Walking to Piazza") is None


def test_fetch_train_delay_simulation_fallback():
    """Verify fallback and known demo train delays."""
    status_3305: LiveTrainStatus = LiveTransitClient.fetch_train_delay("3305")
    assert status_3305.train_number == "3305"
    assert status_3305.delay_minutes == 35
    assert "+35 min delay" in status_3305.status_summary

    status_9941: LiveTrainStatus = LiveTransitClient.fetch_train_delay("9941")
    assert status_9941.train_number == "9941"
    assert status_9941.delay_minutes == 0
    assert "On Time" in status_9941.status_summary

    status_unknown: LiveTrainStatus = LiveTransitClient.fetch_train_delay("88991")
    assert status_unknown.delay_minutes == 0
    assert "Estimated Schedule" in status_unknown.source


def test_check_trip_rail_delays():
    """Verify scanning rail legs in a TripDAG."""
    trip = TripDAG(
        trip_id="rome-live",
        title="Live Transit Test",
        destination="Rome",
        travelers=["Franek"],
        parameters=DAGParameters(risk_multiplier=0.0, hub_overhead_minutes=15),
        nodes=[
            TripNode(
                id="n1",
                title="Leonardo Express Airport Shuttle",
                type=NodeType.FLEXIBLE,
                category=Category.RAIL,
                transit_mode=TransitMode.TRAIN,
                duration_min=32,
            ),
            TripNode(
                id="n2",
                title="Colosseum Timed Ticket",
                type=NodeType.FIXED,
                category=Category.SIGHTSEEING,
                fixed_start_time="12:30",
                duration_min=90,
            ),
        ],
    )

    statuses = LiveTransitClient.check_trip_rail_delays(trip)
    assert "n1" in statuses
    # Leonardo Express demo train 3305 reports 35 min delay
    assert statuses["n1"].delay_minutes == 35


def test_live_delay_propagation_in_dag():
    """Verify live delay propagates into DAGValidator and detects domino conflict."""
    trip = TripDAG(
        trip_id="test-prop",
        title="Propagate Delay",
        destination="Rome",
        travelers=["Franek"],
        parameters=DAGParameters(risk_multiplier=0.0, hub_overhead_minutes=15),
        nodes=[
            TripNode(
                id="t-rail",
                title="Regional Train 3305 to Central Station",
                type=NodeType.FIXED,
                category=Category.RAIL,
                fixed_start_time="10:40",
                duration_min=60,  # Scheduled arrival 11:40
            ),
            TripNode(
                id="t-walk",
                title="Morning Scenic Piazza Walk",
                type=NodeType.FLEXIBLE,
                category=Category.SIGHTSEEING,
                transit_min=0,
                duration_min=30,
            ),
            TripNode(
                id="t-museum",
                title="Timed Museum Entry (HARD LOCK)",
                type=NodeType.FIXED,
                category=Category.SIGHTSEEING,
                transit_mode=TransitMode.WALK,
                transit_min=20,
                duration_min=90,
                fixed_start_time="12:30",
            ),
        ],
    )

    # Fetch live delay
    statuses = LiveTransitClient.check_trip_rail_delays(trip)
    injected = {nid: st.delay_minutes for nid, st in statuses.items() if st.delay_minutes > 0}

    assert "t-rail" in injected
    assert injected["t-rail"] == 35

    audit = validate_dag(trip, injected_delays=injected)
    # Train delayed by 35m -> arrives 12:15.
    # Walk: 12:15 -> 12:45.
    # Transit to museum: 20m + 15m queue buffer = 35m -> Ready at 13:20.
    # Museum is locked at 12:30 -> Conflict deficit!
    assert not audit.is_valid
    assert len(audit.conflicts) >= 1
    assert audit.conflicts[0].is_conflict
    assert audit.conflicts[0].conflict_deficit_min > 0
