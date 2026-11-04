"""
Peer-to-Peer (P2P) Offline Group Sync & State Transfer Engine for KronoLatch.
Enables serverless, offline-first sharing of newly logged expenses and itinerary updates
via compressed tokens and QR codes without cloud databases or accounts.
"""

from __future__ import annotations

import base64
import json
import time
import zlib
from typing import Dict, List, Literal, Tuple

from pydantic import BaseModel, Field

from kronolatch.models import Expense, TripDAG, TripNode


class SyncPayload(BaseModel):
    """Portable, self-contained bundle of trip state delta for peer synchronization."""

    version: int = Field(default=1, description="Protocol format version")
    trip_id: str = Field(description="Trip identifier to match")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="Epoch timestamp")
    sender: str = Field(default="Traveler", description="Name of traveler sending the update")
    sync_type: Literal["all", "expenses", "itinerary"] = Field(
        default="expenses", description="Scope of synchronized entities"
    )
    expenses: List[Expense] = Field(default_factory=list, description="List of expenses to merge")
    nodes: List[TripNode] = Field(
        default_factory=list, description="List of itinerary nodes to merge"
    )


class SyncEngine:
    """Encoder, decoder, and conflict-free merger for offline travel updates."""

    TOKEN_PREFIX = "krono1_"

    @classmethod
    def encode_token(cls, payload: SyncPayload) -> str:
        """Serialize payload into a compact, URL-safe base64 compressed token."""
        json_bytes = json.dumps(payload.model_dump(mode="json"), separators=(",", ":")).encode(
            "utf-8"
        )
        compressed = zlib.compress(json_bytes, level=9)
        b64 = base64.urlsafe_b64encode(compressed).decode("ascii")
        return f"{cls.TOKEN_PREFIX}{b64}"

    @classmethod
    def decode_token(cls, token: str) -> SyncPayload:
        """Decode a compressed sync token back into a verified SyncPayload."""
        clean = token.strip()
        if clean.startswith(cls.TOKEN_PREFIX):
            clean = clean[len(cls.TOKEN_PREFIX) :]

        try:
            compressed = base64.urlsafe_b64decode(clean.encode("ascii"))
            json_bytes = zlib.decompress(compressed)
            data = json.loads(json_bytes.decode("utf-8"))
            return SyncPayload.model_validate(data)
        except Exception as exc:
            raise ValueError(f"Invalid or corrupted KronoLatch sync token: {exc}") from exc

    @classmethod
    def create_payload_from_trip(
        cls,
        trip: TripDAG,
        sender: str = "Traveler",
        sync_type: Literal["all", "expenses", "itinerary"] = "all",
    ) -> SyncPayload:
        """Construct a sync payload from a local TripDAG."""
        expenses = trip.expenses if sync_type in ("all", "expenses") else []
        nodes = trip.nodes if sync_type in ("all", "itinerary") else []

        return SyncPayload(
            trip_id=trip.trip_id,
            sender=sender,
            sync_type=sync_type,
            expenses=expenses,
            nodes=nodes,
        )

    @classmethod
    def merge_into_trip(
        cls, incoming: SyncPayload, trip: TripDAG
    ) -> Tuple[TripDAG, Dict[str, int]]:
        """
        Merge incoming peer updates into the local TripDAG without duplicating existing records.
        Returns the updated TripDAG and a summary of new additions.
        """
        existing_exp_ids = {e.id for e in trip.expenses}
        existing_node_ids = {n.id for n in trip.nodes}

        new_expenses_count = 0
        new_nodes_count = 0

        # Merge Expenses (idempotent deduplication)
        merged_expenses = list(trip.expenses)
        for inc_exp in incoming.expenses:
            if inc_exp.id not in existing_exp_ids:
                merged_expenses.append(inc_exp)
                existing_exp_ids.add(inc_exp.id)
                new_expenses_count += 1

        # Merge Nodes (idempotent deduplication + chronological ordering)
        merged_nodes = list(trip.nodes)
        for inc_node in incoming.nodes:
            if inc_node.id not in existing_node_ids:
                merged_nodes.append(inc_node)
                existing_node_ids.add(inc_node.id)
                new_nodes_count += 1

        # Re-sort nodes chronologically by start time
        merged_nodes.sort(key=lambda n: n.get_effective_fixed_start_min() or 0)

        # Merge travelers if new participant appeared
        travelers_set = set(trip.travelers)
        for exp in merged_expenses:
            travelers_set.add(exp.payer)
            travelers_set.update(exp.participants)
        merged_travelers = sorted(list(travelers_set))

        updated_trip = TripDAG(
            trip_id=trip.trip_id,
            title=trip.title,
            destination=trip.destination,
            base_currency=trip.base_currency,
            travelers=merged_travelers,
            parameters=trip.parameters,
            nodes=merged_nodes,
            expenses=merged_expenses,
            vendor_checks=trip.vendor_checks,
        )

        stats = {
            "new_expenses": new_expenses_count,
            "new_nodes": new_nodes_count,
            "total_expenses": len(merged_expenses),
            "total_nodes": len(merged_nodes),
        }
        return updated_trip, stats
