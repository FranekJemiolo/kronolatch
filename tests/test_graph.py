"""
Unit tests for KronoLatch Critical Path Method (CPM) & Graph Topology Engine (Phase 8).
"""

from __future__ import annotations

from kronolatch.graph import CriticalPathEngine
from kronolatch.models import (
    Category,
    DAGParameters,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
)


def create_topological_trip() -> TripDAG:
    """Creates a sample trip with tight locked deadlines and flexible slack."""
    nodes = [
        TripNode(
            id="n1_morning_walk",
            title="Morning Scenic Walk",
            type=NodeType.FLEXIBLE,
            category=Category.WALK,
            transit_mode=TransitMode.NONE,
            transit_min=0,
            duration_min=45,
            active=True,
        ),
        TripNode(
            id="n2_train",
            title="Frecciarossa High-Speed Rail",
            type=NodeType.FIXED,
            category=Category.RAIL,
            transit_mode=TransitMode.TRAIN,
            transit_min=15,
            duration_min=90,
            fixed_start_min=9 * 60 + 30,  # 09:30 (Leaves little slack after walk starting at 08:00)
            active=True,
        ),
        TripNode(
            id="n3_lunch",
            title="Trastevere Casual Lunch",
            type=NodeType.FLEXIBLE,
            category=Category.FOOD,
            transit_mode=TransitMode.WALK,
            transit_min=15,
            duration_min=60,
            active=True,
        ),
        TripNode(
            id="n4_colosseum",
            title="Colosseum Strict Reservation",
            type=NodeType.FIXED,
            category=Category.SIGHTSEEING,
            transit_mode=TransitMode.WALK,
            transit_min=20,
            duration_min=90,
            fixed_start_min=14 * 60,  # 14:00 strict lock
            active=True,
        ),
    ]

    return TripDAG(
        trip_id="topo-test-trip",
        title="Topological Test Trip",
        destination="Rome",
        travelers=["Franek", "Anna"],
        parameters=DAGParameters(risk_multiplier=0.20, hub_overhead_minutes=15),
        nodes=nodes,
    )


def test_cpm_forward_backward_pass():
    """Verify that CPM correctly computes forward and backward passes and positive duration."""
    trip = create_topological_trip()
    result = CriticalPathEngine.analyze_trip(trip)

    assert result.total_duration_min > 0
    assert len(result.node_metrics) == 4

    # Every node's EF should equal ES + duration
    for m in result.node_metrics:
        assert m.earliest_finish_min == m.earliest_start_min + m.duration_min
        assert m.latest_finish_min == m.latest_start_min + m.duration_min
        assert m.total_float_min >= 0


def test_critical_path_identification():
    """Verify that nodes with tight connections to fixed deadlines are identified as critical."""
    trip = create_topological_trip()
    result = CriticalPathEngine.analyze_trip(trip, critical_slack_threshold_min=15)

    assert len(result.critical_path_node_ids) >= 1
    # The fixed nodes must be represented in metrics
    crit_nodes = [m for m in result.node_metrics if m.is_critical]
    assert len(crit_nodes) > 0
