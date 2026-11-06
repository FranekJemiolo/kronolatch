"""
Unit tests for KronoLatch Monte Carlo Stochastic Simulation Engine (Phase 6).
"""

from __future__ import annotations

from kronolatch.models import (
    Category,
    DAGParameters,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
)
from kronolatch.simulation import MonteCarloSimulator, SimulationParameters


def create_sample_trip(tight: bool = False) -> TripDAG:
    """Helper creating a 3-node itinerary with flight, train, and fixed museum entry."""
    nodes = [
        TripNode(
            id="n1_flight",
            title="Inbound Flight to Rome",
            type=NodeType.FIXED,
            category=Category.FLIGHT,
            transit_mode=TransitMode.NONE,
            transit_min=0,
            duration_min=120,
            fixed_start_min=9 * 60,  # 09:00
            active=True,
        ),
        TripNode(
            id="n2_train",
            title="Express Train to City Center",
            type=NodeType.FIXED,
            category=Category.RAIL,
            transit_mode=TransitMode.TRAIN,
            transit_min=30,
            duration_min=35,
            # Flight ends 11:00. Transition is 30m transit + 15m overhead = 45m (11:45).
            # Tight has only 15m slack (12:00); relaxed has 75m slack (13:00).
            fixed_start_min=11 * 60 + 45 + (15 if tight else 75),
            active=True,
        ),
        TripNode(
            id="n3_museum",
            title="Vatican Museums Timed Entry",
            type=NodeType.FIXED,
            category=Category.SIGHTSEEING,
            transit_mode=TransitMode.WALK,
            transit_min=20,
            duration_min=120,
            fixed_start_min=13 * 60 + (30 if tight else 15 * 60),
            active=True,
        ),
    ]

    return TripDAG(
        trip_id="test-sim-trip",
        title="Simulation Test Trip",
        destination="Rome",
        travelers=["Alice", "Bob"],
        parameters=DAGParameters(risk_multiplier=0.15, hub_overhead_minutes=15),
        nodes=nodes,
    )


def test_simulation_reproducibility():
    """Verify that specifying a seed guarantees 100% reproducible statistical results."""
    trip = create_sample_trip(tight=True)
    p1 = SimulationParameters(iterations=500, seed=42)
    p2 = SimulationParameters(iterations=500, seed=42)

    res1 = MonteCarloSimulator.run_simulation(trip, p1)
    res2 = MonteCarloSimulator.run_simulation(trip, p2)

    assert res1.trip_fragility_score == res2.trip_fragility_score
    assert res1.p50_total_delay == res2.p50_total_delay
    assert res1.p95_total_delay == res2.p95_total_delay
    assert res1.conflict_runs_count == res2.conflict_runs_count


def test_simulation_tight_vs_relaxed():
    """Verify that a tight schedule shows high fragility and recommends higher alpha_risk."""
    tight_trip = create_sample_trip(tight=True)
    relaxed_trip = create_sample_trip(tight=False)

    p = SimulationParameters(iterations=1000, seed=123)

    tight_res = MonteCarloSimulator.run_simulation(tight_trip, p)
    relaxed_res = MonteCarloSimulator.run_simulation(relaxed_trip, p)

    # Tight itinerary should have significant fragility
    assert tight_res.trip_fragility_score > 5.0
    assert not tight_res.is_robust
    assert len(tight_res.critical_nodes) > 0
    assert tight_res.recommended_risk_multiplier > tight_res.current_risk_multiplier

    # Relaxed itinerary should have low fragility and be robust
    assert relaxed_res.trip_fragility_score < tight_res.trip_fragility_score
    assert relaxed_res.is_robust


def test_simulation_speed_benchmark():
    """Verify that 2,500 simulation trials complete in well under 100 milliseconds."""
    trip = create_sample_trip(tight=False)
    p = SimulationParameters(iterations=2500, seed=99)

    res = MonteCarloSimulator.run_simulation(trip, p)

    assert res.iterations == 2500
    assert res.simulation_duration_ms < 100.0  # High-performance requirement
