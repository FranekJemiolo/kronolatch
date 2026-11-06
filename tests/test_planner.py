"""
Tests for KronoLatch AI Wishlist Tour Planner & Research Engine.
"""

from __future__ import annotations

from kronolatch.dag_engine import validate_dag
from kronolatch.models import NodeType
from kronolatch.planner import TripPlanner, WishlistRequest


def test_match_pois_from_text():
    """Verify keyword and alias recognition for attractions."""
    pois = TripPlanner.match_pois("I'd love to see the Colosseum, Pantheon, and Uffizi Gallery.")
    names = [p.name for p in pois]

    assert any("Colosseum" in n for n in names)
    assert any("Pantheon" in n for n in names)
    assert any("Uffizi" in n for n in names)


def test_generate_trip_from_wishlist():
    """Verify end-to-end TripDAG synthesis and DAG mathematical validity."""
    req = WishlistRequest(
        destination="Rome & Florence",
        wishlist_text="Colosseum, Vatican, Pantheon, Uffizi Gallery",
        travelers=["Franek", "Anna", "Marek", "Kasia"],
        pace="moderate",
        transport_mode="mixed_car_and_rail",
    )

    trip = TripPlanner.generate_trip(req)

    assert trip.destination == "Rome & Florence"
    assert len(trip.travelers) == 4
    assert len(trip.nodes) >= 4

    # Verify inter-city rail transfer was injected between Rome and Florence
    titles = [n.title for n in trip.nodes]
    assert any("Frecciarossa" in t for t in titles)

    # Verify official domains are attached to ticketed monuments
    colosseum_node = next(n for n in trip.nodes if "Colosseum" in n.title)
    assert colosseum_node.type == NodeType.FIXED
    assert colosseum_node.official_domain == "ticketing.colosseo.it"
    assert colosseum_node.fixed_start_time is not None

    # Verify expenses were generated with subgroup allocations
    assert len(trip.expenses) >= 3
    car_exp = next((e for e in trip.expenses if "Rental Car" in e.title), None)
    assert car_exp is not None
    assert len(car_exp.participants) == 2  # Asymmetric split: only drivers!

    # Verify DAG engine mathematical validation passes with zero hard conflicts
    audit = validate_dag(trip)
    assert audit.is_valid
    assert len(audit.conflicts) == 0


def test_pacing_variation():
    """Verify that pace profile affects scheduled dwell durations."""
    req_relaxed = WishlistRequest(
        wishlist_text="Colosseum, Pantheon",
        pace="relaxed",
    )
    req_fast = WishlistRequest(
        wishlist_text="Colosseum, Pantheon",
        pace="fast-paced",
    )

    trip_relaxed = TripPlanner.generate_trip(req_relaxed)
    trip_fast = TripPlanner.generate_trip(req_fast)

    relaxed_colosseum = next(n for n in trip_relaxed.nodes if "Colosseum" in n.title)
    fast_colosseum = next(n for n in trip_fast.nodes if "Colosseum" in n.title)

    assert relaxed_colosseum.duration_min > fast_colosseum.duration_min
