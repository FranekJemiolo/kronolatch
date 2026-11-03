"""
Temporal DAG Engine for KronoLatch.
Computes deterministic time-graph transitions, dynamic buffers, domino-effect delay propagation,
hard conflict detection, and auto-cut/compression optimization.
"""

from __future__ import annotations

import copy
import math
from typing import Dict, List, Optional, Tuple

from kronolatch.models import (
    Category,
    DAGAuditResult,
    NodeScheduleResult,
    NodeType,
    TransitMode,
    TripDAG,
    minutes_to_time_str,
)

# Standard default transit mode rules
DEFAULT_TRANSIT_RULES: Dict[TransitMode, Tuple[int, float]] = {
    TransitMode.FLIGHT: (120, 0.15),  # 120m airport overhead, 15% risk
    TransitMode.TRAIN: (15, 0.20),  # 15m platform/station overhead, 20% risk
    TransitMode.BUS: (15, 0.20),  # 15m station overhead, 20% risk
    TransitMode.CAR: (15, 0.25),  # 15m parking/walk overhead, 25% risk
    TransitMode.WALK: (5, 0.10),  # 5m walk buffer, 10% risk
    TransitMode.NONE: (0, 0.0),
}


def calculate_transition_time(
    transit_min: int,
    transit_mode: TransitMode = TransitMode.WALK,
    risk_multiplier: Optional[float] = None,
    hub_overhead: Optional[int] = None,
    fixed_buffer: int = 0,
    injected_delay: int = 0,
) -> int:
    """
    Computes:
    Total Transition Time = T_transit + T_overhead + ceil(T_transit * alpha_risk) + B_fixed + Delta_t
    """
    if transit_min <= 0 and injected_delay <= 0:
        return 0

    rule_overhead, rule_risk = DEFAULT_TRANSIT_RULES.get(transit_mode, (5, 0.10))

    eff_overhead = hub_overhead if hub_overhead is not None else rule_overhead
    eff_risk = risk_multiplier if risk_multiplier is not None else rule_risk

    risk_padding = math.ceil(transit_min * eff_risk)
    total = transit_min + eff_overhead + risk_padding + fixed_buffer + injected_delay
    return max(0, total)


def validate_dag(
    trip: TripDAG,
    injected_delays: Optional[Dict[str, int]] = None,
    risk_multiplier: Optional[float] = None,
    hub_overhead: Optional[int] = None,
) -> DAGAuditResult:
    """
    Propagates time sequentially across all active nodes in the DAG.
    Calculates slack for FIXED constraints and detects HARD_CONFLICTs.
    """
    delays = injected_delays or {}
    eff_risk = risk_multiplier if risk_multiplier is not None else trip.parameters.risk_multiplier
    eff_hub = hub_overhead if hub_overhead is not None else trip.parameters.hub_overhead_minutes

    active_nodes = [n for n in trip.nodes if n.active]
    if not active_nodes:
        return DAGAuditResult(
            is_valid=True,
            total_sightseeing_min=0,
            total_transit_min=0,
            total_buffer_min=0,
            schedule_results=[],
            conflicts=[],
            remediation_recommendations=[],
        )

    # Initial anchor: either the first fixed node start, or 08:00 (480)
    first_fixed = active_nodes[0].get_effective_fixed_start_min()
    cursor = first_fixed if first_fixed is not None else 8 * 60

    total_sightseeing = 0
    total_transit = 0
    total_buffer = 0
    results: List[NodeScheduleResult] = []
    conflicts: List[NodeScheduleResult] = []

    for idx, node in enumerate(active_nodes):
        node_delay = delays.get(node.id, 0)

        if idx == 0:
            eff_transition = 0
            transit_base = 0
            buffer_portion = 0
        else:
            # Derive transit mode based on category or explicit mode
            mode = node.transit_mode
            if mode == TransitMode.WALK and node.category in (Category.FLIGHT,):
                mode = TransitMode.FLIGHT
            elif mode == TransitMode.WALK and node.category in (Category.RAIL,):
                mode = TransitMode.TRAIN
            elif mode == TransitMode.WALK and node.category in (Category.CAR,):
                mode = TransitMode.CAR

            transit_base = node.transit_min
            eff_transition = calculate_transition_time(
                transit_min=node.transit_min,
                transit_mode=mode,
                risk_multiplier=eff_risk,
                hub_overhead=eff_hub,
                fixed_buffer=0,
                injected_delay=0,
            )
            buffer_portion = max(0, eff_transition - transit_base)

        total_transit += transit_base
        total_buffer += buffer_portion

        effective_duration = node.duration_min + node_delay
        if node.category in (Category.SIGHTSEEING, Category.FOOD, Category.LODGING):
            total_sightseeing += node.duration_min
        else:
            total_transit += effective_duration

        earliest_arrival = cursor if idx == 0 else (cursor + eff_transition)
        fixed_start = node.get_effective_fixed_start_min()

        slack_min = None
        is_conflict = False
        deficit = 0
        actual_start = earliest_arrival

        if node.type == NodeType.FIXED and fixed_start is not None:
            if idx == 0:
                actual_start = fixed_start
                slack_min = 30  # Standard on-time start buffer
            else:
                slack_min = fixed_start - earliest_arrival
                if slack_min < 0:
                    is_conflict = True
                    deficit = abs(slack_min)
                    actual_start = earliest_arrival  # Overdue arrival
                else:
                    actual_start = fixed_start

        end_min = actual_start + effective_duration
        cursor = end_min

        window_str = f"{minutes_to_time_str(actual_start)} -> {minutes_to_time_str(end_min)}"

        res = NodeScheduleResult(
            node_id=node.id,
            title=node.title,
            node_type=node.type,
            category=node.category,
            earliest_arrival_min=earliest_arrival,
            actual_start_min=actual_start,
            end_min=end_min,
            slack_min=slack_min,
            is_conflict=is_conflict,
            conflict_deficit_min=deficit,
            transition_time_min=eff_transition,
            time_window_str=window_str,
            active=True,
            notes=node.notes,
        )
        results.append(res)
        if is_conflict:
            conflicts.append(res)

    recommendations: List[str] = []
    if conflicts:
        for c in conflicts:
            recommendations.append(
                f"HARD_CONFLICT at locked stop '{c.title}': Arrival is {c.conflict_deficit_min}m late. "
                "Recommend compressing upstream flexible windows or auto-trimming lowest priority stops."
            )

    return DAGAuditResult(
        is_valid=len(conflicts) == 0,
        total_sightseeing_min=total_sightseeing,
        total_transit_min=total_transit,
        total_buffer_min=total_buffer,
        schedule_results=results,
        conflicts=conflicts,
        remediation_recommendations=recommendations,
    )


def optimize_and_cut(
    trip: TripDAG,
    target_minutes_to_save: Optional[int] = None,
    injected_delays: Optional[Dict[str, int]] = None,
    risk_multiplier: Optional[float] = None,
    hub_overhead: Optional[int] = None,
) -> Tuple[TripDAG, List[str]]:
    """
    Auto-Cut Optimizer:
    1. First compresses FLEXIBLE nodes toward their min_duration_min (starting from lowest priority).
    2. If conflicts or target deficit persist, drops the lowest-priority FLEXIBLE node with the highest
       detour overhead (transit + duration) until all constraints are satisfied.
    Returns (optimized_trip_dag, action_log).
    """
    optimized = copy.deepcopy(trip)
    actions: List[str] = []

    current_audit = validate_dag(
        optimized,
        injected_delays=injected_delays,
        risk_multiplier=risk_multiplier,
        hub_overhead=hub_overhead,
    )

    if current_audit.is_valid and (target_minutes_to_save is None or target_minutes_to_save <= 0):
        return optimized, ["Schedule is already valid with zero hard conflicts."]

    max_iterations = 20
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        current_audit = validate_dag(
            optimized,
            injected_delays=injected_delays,
            risk_multiplier=risk_multiplier,
            hub_overhead=hub_overhead,
        )

        if current_audit.is_valid:
            if target_minutes_to_save is None or target_minutes_to_save <= 0:
                actions.append("All hard conflicts successfully resolved.")
                break

        # Check total deficit to resolve
        max_conflict_deficit = max(
            [c.conflict_deficit_min for c in current_audit.conflicts], default=0
        )
        needed = max(max_conflict_deficit, target_minutes_to_save or 0)

        # Step 1: Try compressing flexible nodes that have available compress leeway
        compressible = [
            n
            for n in optimized.nodes
            if n.active and n.type == NodeType.FLEXIBLE and (n.duration_min > n.get_min_duration())
        ]
        if compressible:
            # Sort by lowest priority first
            compressible.sort(key=lambda n: (n.priority, -n.duration_min))
            target_node = compressible[0]
            can_shave = target_node.duration_min - target_node.get_min_duration()
            shave = min(can_shave, needed)
            target_node.duration_min -= shave
            if target_minutes_to_save is not None:
                target_minutes_to_save -= shave
            actions.append(
                f"Compressed flexible stop '{target_node.title}' from {target_node.duration_min + shave}m "
                f"to {target_node.duration_min}m (saved {shave}m)."
            )
            continue

        # Step 2: If compression is exhausted, drop the lowest-priority flexible stop
        candidates = [n for n in optimized.nodes if n.active and n.type == NodeType.FLEXIBLE]
        if not candidates:
            actions.append(
                "No further flexible stops available to prune. Cannot resolve all fixed conflicts."
            )
            break

        # Sort by: lowest priority ascending, then highest total overhead (duration + transit) descending
        candidates.sort(key=lambda n: (n.priority, -(n.duration_min + n.transit_min)))
        drop_node = candidates[0]
        drop_node.active = False
        reclaimed = drop_node.duration_min + drop_node.transit_min
        if target_minutes_to_save is not None:
            target_minutes_to_save -= reclaimed
        actions.append(
            f"Pruned lowest-priority stop '{drop_node.title}' (Priority {drop_node.priority}) "
            f"— reclaimed {reclaimed}m ({drop_node.duration_min}m stop + {drop_node.transit_min}m transit)."
        )

    return optimized, actions
