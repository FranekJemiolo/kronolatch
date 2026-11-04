"""
Tests for KronoLatch Peer-to-Peer Offline Sync Engine.
"""

from __future__ import annotations

import pytest

from kronolatch.models import Expense, TripDAG, TripNode
from kronolatch.sync import SyncEngine, SyncPayload


def test_sync_token_roundtrip():
    """Verify encoding and decoding of offline sync tokens."""
    payload = SyncPayload(
        trip_id="rome-florence-2026",
        sender="Anna",
        sync_type="expenses",
        expenses=[
            Expense(
                id="e_sync_1",
                title="Gelato near Trevi",
                payer="Anna",
                amount=18.50,
                currency="EUR",
                participants=["Franek", "Anna", "Marek", "Kasia"],
            )
        ],
    )

    token = SyncEngine.encode_token(payload)
    assert token.startswith("krono1_")

    decoded = SyncEngine.decode_token(token)
    assert decoded.trip_id == "rome-florence-2026"
    assert decoded.sender == "Anna"
    assert len(decoded.expenses) == 1
    assert decoded.expenses[0].id == "e_sync_1"
    assert decoded.expenses[0].amount == 18.50


def test_sync_token_invalid():
    """Verify invalid or corrupted token raises ValueError."""
    with pytest.raises(ValueError, match="Invalid or corrupted"):
        SyncEngine.decode_token("krono1_not_a_valid_token_xyz")


def test_merge_into_trip_deduplication():
    """Verify that merging incoming peer expenses is idempotent and prevents double-counting."""
    base_trip = TripDAG(
        trip_id="rome-florence-2026",
        title="Rome Tour",
        destination="Rome",
        travelers=["Franek", "Anna"],
        nodes=[],
        expenses=[
            Expense(
                id="e1",
                title="Car Rental",
                payer="Franek",
                amount=120.0,
                currency="EUR",
                participants=["Franek", "Anna"],
            )
        ],
    )

    incoming_payload = SyncPayload(
        trip_id="rome-florence-2026",
        sender="Anna",
        expenses=[
            # Duplicate expense (should not be added twice)
            Expense(
                id="e1",
                title="Car Rental",
                payer="Franek",
                amount=120.0,
                currency="EUR",
                participants=["Franek", "Anna"],
            ),
            # New expense from companion
            Expense(
                id="e2",
                title="Vatican Museum Tickets",
                payer="Anna",
                amount=60.0,
                currency="EUR",
                participants=["Franek", "Anna"],
            ),
        ],
    )

    updated_trip, stats = SyncEngine.merge_into_trip(incoming_payload, base_trip)

    assert stats["new_expenses"] == 1
    assert stats["total_expenses"] == 2
    assert len(updated_trip.expenses) == 2
    assert updated_trip.expenses[0].id == "e1"
    assert updated_trip.expenses[1].id == "e2"


def test_merge_into_trip_nodes():
    """Verify merging new itinerary stops maintains chronological ordering."""
    base_trip = TripDAG(
        trip_id="rome-florence-2026",
        title="Rome Tour",
        destination="Rome",
        travelers=["Franek"],
        nodes=[
            TripNode(
                id="n1",
                title="Colosseum",
                type="fixed",
                fixed_start_time="14:00",
                duration_min=90,
            )
        ],
        expenses=[],
    )

    incoming_payload = SyncPayload(
        trip_id="rome-florence-2026",
        sender="Marek",
        sync_type="itinerary",
        nodes=[
            TripNode(
                id="n2",
                title="Morning Espresso at Piazza del Popolo",
                type="fixed",
                fixed_start_time="09:15",
                duration_min=30,
            )
        ],
    )

    updated_trip, stats = SyncEngine.merge_into_trip(incoming_payload, base_trip)

    assert stats["new_nodes"] == 1
    assert len(updated_trip.nodes) == 2
    # 09:15 node must come before 14:00 node
    assert updated_trip.nodes[0].id == "n2"
    assert updated_trip.nodes[0].fixed_start_time == "09:15"
    assert updated_trip.nodes[1].id == "n1"
    assert updated_trip.nodes[1].fixed_start_time == "14:00"
