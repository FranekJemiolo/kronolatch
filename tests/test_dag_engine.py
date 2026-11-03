"""
Unit tests for KronoLatch Temporal DAG Engine.
Validates buffer calculations, domino-effect propagation, hard conflict detection, and auto-cut optimizer.
"""

from kronolatch.dag_engine import calculate_transition_time, optimize_and_cut, validate_dag
from kronolatch.models import (
    Category,
    DAGParameters,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
)


def test_transition_buffer_formula():
    """Validates default mode-specific overheads and risk percentages."""
    # Flight: 120m overhead + 15% risk + transit
    flight_t = calculate_transition_time(transit_min=60, transit_mode=TransitMode.FLIGHT)
    # 60 + 120 + ceil(60 * 0.15 = 9) = 189
    assert flight_t == 189

    # Train: 15m overhead + 20% risk + transit
    train_t = calculate_transition_time(transit_min=45, transit_mode=TransitMode.TRAIN)
    # 45 + 15 + ceil(45 * 0.20 = 9) = 69
    assert train_t == 69

    # Car: 15m overhead + 25% risk + transit
    car_t = calculate_transition_time(transit_min=40, transit_mode=TransitMode.CAR)
    # 40 + 15 + ceil(40 * 0.25 = 10) = 65
    assert car_t == 65

    # Walk: 5m overhead + 10% risk + transit
    walk_t = calculate_transition_time(transit_min=20, transit_mode=TransitMode.WALK)
    # 20 + 5 + ceil(20 * 0.10 = 2) = 27
    assert walk_t == 27


def test_hard_conflict_detection():
    """Asserts that arriving after a locked fixed start time flags HARD_CONFLICT."""
    trip = TripDAG(
        trip_id="test-conflict",
        title="Conflict Test",
        destination="Rome",
        base_currency="EUR",
        travelers=["Alice"],
        parameters=DAGParameters(risk_multiplier=0.20, hub_overhead_minutes=15),
        nodes=[
            TripNode(
                id="n1",
                title="Morning Tour",
                type=NodeType.FIXED,
                category=Category.SIGHTSEEING,
                fixed_start_time="09:00",
                duration_min=180,  # ends 12:00
            ),
            TripNode(
                id="n2",
                title="Colosseum Timed Slot",
                type=NodeType.FIXED,
                category=Category.SIGHTSEEING,
                transit_min=30,  # 30 + 15 overhead + 6 risk = 51m -> arrival 12:51
                duration_min=120,
                fixed_start_time="12:30",  # Arriving 12:51 is 21m late!
            ),
        ],
    )

    audit = validate_dag(trip)
    assert audit.is_valid is False
    assert len(audit.conflicts) == 1
    conflict = audit.conflicts[0]
    assert conflict.node_id == "n2"
    assert conflict.is_conflict is True
    assert conflict.conflict_deficit_min == 21


def test_domino_effect_propagation():
    """Injected delay on upstream node cascades downstream into locked nodes."""
    trip = TripDAG(
        trip_id="test-domino",
        title="Domino Cascade",
        destination="Rome",
        base_currency="EUR",
        travelers=["Alice"],
        parameters=DAGParameters(risk_multiplier=0.0, hub_overhead_minutes=10),
        nodes=[
            TripNode(
                id="leg1",
                title="Airport Shuttle Train",
                type=NodeType.FIXED,
                category=Category.RAIL,
                fixed_start_time="10:00",
                duration_min=40,  # Normally lands 10:40
            ),
            TripNode(
                id="leg2",
                title="Quick Snack",
                type=NodeType.FLEXIBLE,
                category=Category.FOOD,
                transit_min=10,  # 10 + 10 = 20m -> 11:00
                duration_min=30,  # 11:00 -> 11:30
                priority=3,
            ),
            TripNode(
                id="leg3",
                title="Timed Museum Slot",
                type=NodeType.FIXED,
                category=Category.SIGHTSEEING,
                transit_min=15,  # 15 + 10 = 25m -> arrives 11:55
                duration_min=60,
                fixed_start_time="12:00",  # On time (5m slack)
            ),
        ],
    )

    # Without delay: valid
    base_audit = validate_dag(trip)
    assert base_audit.is_valid is True

    # With +30m delay on leg1: leg1 ends at 11:10 instead of 10:40
    # Snack transit 20m -> 11:30 -> ends 12:00
    # Museum transit 25m -> arrives 12:25 -> 25m HARD CONFLICT against 12:00
    delayed_audit = validate_dag(trip, injected_delays={"leg1": 30})
    assert delayed_audit.is_valid is False
    assert len(delayed_audit.conflicts) == 1
    assert delayed_audit.conflicts[0].conflict_deficit_min == 25


def test_auto_cut_optimizer():
    """Asserts auto-cut first compresses flexible stops and then drops lowest priority stops."""
    trip = TripDAG(
        trip_id="test-autocut",
        title="Auto Cut Test",
        destination="Rome",
        base_currency="EUR",
        travelers=["Alice"],
        parameters=DAGParameters(risk_multiplier=0.0, hub_overhead_minutes=10),
        nodes=[
            TripNode(
                id="s1",
                title="Inbound Train",
                type=NodeType.FIXED,
                category=Category.RAIL,
                fixed_start_time="10:00",
                duration_min=40,
            ),
            TripNode(
                id="s2",
                title="Low Priority Photo Detour",
                type=NodeType.FLEXIBLE,
                category=Category.SIGHTSEEING,
                transit_min=15,
                duration_min=45,
                min_duration_min=15,
                priority=2,  # lowest priority
            ),
            TripNode(
                id="s3",
                title="Medium Priority Lunch",
                type=NodeType.FLEXIBLE,
                category=Category.FOOD,
                transit_min=10,
                duration_min=60,
                min_duration_min=30,
                priority=5,
            ),
            TripNode(
                id="s4",
                title="Timed Museum Entry",
                type=NodeType.FIXED,
                category=Category.SIGHTSEEING,
                transit_min=15,
                duration_min=90,
                fixed_start_time="12:30",  # Tight deadline
            ),
        ],
    )

    # Inject delay on train
    opt_trip, actions = optimize_and_cut(trip, injected_delays={"s1": 45})
    opt_audit = validate_dag(opt_trip, injected_delays={"s1": 45})

    assert opt_audit.is_valid is True
    assert len(actions) > 0
    # Low priority stop should have been compressed or pruned
    low_node = next(n for n in opt_trip.nodes if n.id == "s2")
    assert not low_node.active or low_node.duration_min <= 15
