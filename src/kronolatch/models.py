"""
Pydantic v2 models for KronoLatch.
Deterministic Trip DAG entities, vendor verification records, and group expense ledgers.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    FIXED = "fixed"
    FLEXIBLE = "flexible"


class Category(str, Enum):
    FLIGHT = "flight"
    RAIL = "rail"
    BUS = "bus"
    CAR = "car"
    WALK = "walk"
    SIGHTSEEING = "sightseeing"
    FOOD = "food"
    LODGING = "lodging"
    OTHER = "other"


class TransitMode(str, Enum):
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    CAR = "car"
    WALK = "walk"
    NONE = "none"


class VerificationStatus(str, Enum):
    VERIFIED_OFFICIAL = "VERIFIED_OFFICIAL"
    TRUSTED_AGGREGATOR = "TRUSTED_AGGREGATOR"
    HIGH_RISK_CLONE = "HIGH_RISK_CLONE"
    UNVERIFIED_THIRD_PARTY = "UNVERIFIED_THIRD_PARTY"


def time_str_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' string to minutes from midnight."""
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format '{time_str}', expected 'HH:MM'")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time_str(minutes: int) -> str:
    """Convert minutes from midnight to 'HH:MM' string."""
    normalized = ((int(round(minutes)) % 1440) + 1440) % 1440
    hrs = normalized // 60
    mins = normalized % 60
    return f"{hrs:02d}:{mins:02d}"


class DAGParameters(BaseModel):
    risk_multiplier: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Proportional transit delay risk multiplier (alpha_risk)",
    )
    hub_overhead_minutes: int = Field(
        default=15,
        ge=0,
        le=240,
        description="Default station / queue buffer in minutes",
    )


class TripNode(BaseModel):
    id: str
    title: str
    type: NodeType
    category: Category = Category.SIGHTSEEING
    transit_mode: TransitMode = TransitMode.WALK
    transit_min: int = Field(default=0, ge=0)
    duration_min: int = Field(ge=1)
    min_duration_min: Optional[int] = Field(default=None, ge=0)
    ideal_duration_min: Optional[int] = Field(default=None, ge=1)
    fixed_start_min: Optional[int] = Field(default=None, ge=0)
    fixed_start_time: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)
    pnr: Optional[str] = None
    official_domain: Optional[str] = None
    booking_url: Optional[str] = None
    active: bool = True
    notes: Optional[str] = None

    @field_validator("fixed_start_min", mode="before")
    @classmethod
    def set_fixed_start_min(cls, v: Optional[int], info) -> Optional[int]:
        return v

    def get_effective_fixed_start_min(self) -> Optional[int]:
        if self.fixed_start_min is not None:
            return self.fixed_start_min
        if self.fixed_start_time:
            return time_str_to_minutes(self.fixed_start_time)
        return None

    def get_min_duration(self) -> int:
        if self.min_duration_min is not None:
            return self.min_duration_min
        # Default minimum duration is 30% of scheduled duration or at least 15 min
        return max(15, int(self.duration_min * 0.4))


class TransitEdge(BaseModel):
    from_node_id: str
    to_node_id: str
    mode: TransitMode = TransitMode.WALK
    base_transit_min: int = 0
    risk_multiplier: float = 0.20
    overhead_min: int = 0
    fixed_buffer_min: int = 0
    injected_delay_min: int = 0

    @property
    def calculated_transition_min(self) -> int:
        import math

        risk_padding = math.ceil(self.base_transit_min * self.risk_multiplier)
        return (
            self.base_transit_min
            + self.overhead_min
            + risk_padding
            + self.fixed_buffer_min
            + self.injected_delay_min
        )


class NodeScheduleResult(BaseModel):
    node_id: str
    title: str
    node_type: NodeType
    category: Category
    earliest_arrival_min: int
    actual_start_min: int
    end_min: int
    slack_min: Optional[int] = None
    is_conflict: bool = False
    conflict_deficit_min: int = 0
    transition_time_min: int = 0
    time_window_str: str
    active: bool = True
    notes: Optional[str] = None


class DAGAuditResult(BaseModel):
    is_valid: bool
    total_sightseeing_min: int
    total_transit_min: int
    total_buffer_min: int
    schedule_results: List[NodeScheduleResult]
    conflicts: List[NodeScheduleResult]
    remediation_recommendations: List[str] = Field(default_factory=list)


class Expense(BaseModel):
    id: str
    title: str
    payer: str
    amount: float = Field(gt=0)
    currency: str = "EUR"
    exchange_rate_to_base: float = Field(default=1.0, gt=0)
    participants: List[str] = Field(min_length=1)
    node_id: Optional[str] = None
    weights: Optional[Dict[str, float]] = None

    def amount_in_base(self) -> float:
        return (
            self.amount / self.exchange_rate_to_base if self.exchange_rate_to_base else self.amount
        )


class SettlementTransfer(BaseModel):
    from_person: str
    to_person: str
    amount: float
    currency: str = "EUR"
    amount_alternate: Optional[float] = None
    alternate_currency: Optional[str] = None


class LedgerSettlementResult(BaseModel):
    base_currency: str
    total_spend_base: float
    net_balances: Dict[str, float]
    transfers: List[SettlementTransfer]


class VendorCheckResult(BaseModel):
    venue: str
    candidate_url: str
    candidate_root_domain: str
    ground_truth_root_domain: Optional[str] = None
    status: VerificationStatus
    official_base_price: Optional[float] = None
    candidate_price: Optional[float] = None
    markup_percent: Optional[float] = None
    is_blocked: bool = False
    reasons: List[str] = Field(default_factory=list)
    verified_official_url: Optional[str] = None
    places_id: Optional[str] = None
    wikidata_id: Optional[str] = None
    booking_rule: Optional[str] = None


class TripDAG(BaseModel):
    trip_id: str
    title: str
    destination: str
    base_currency: str = "EUR"
    travelers: List[str] = Field(min_length=1)
    parameters: DAGParameters = Field(default_factory=DAGParameters)
    nodes: List[TripNode]
    expenses: List[Expense] = Field(default_factory=list)
    vendor_checks: List[VendorCheckResult] = Field(default_factory=list)
