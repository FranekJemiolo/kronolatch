"""
Topological Critical Path Method (CPM) & Graph Analyzer for KronoLatch.
Calculates Earliest/Latest Start and Finish times, identifies float/slack cushions,
and isolates the zero-slack Critical Path across multi-modal travel DAGs.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from kronolatch.dag_engine import calculate_transition_time
from kronolatch.models import (
    NodeType,
    TripDAG,
)


class CPMNodeMetrics(BaseModel):
    """Critical Path Method temporal metrics for a single itinerary node."""

    node_id: str
    title: str
    node_type: NodeType
    duration_min: int
    transit_buffer_before_min: int
    earliest_start_min: int
    earliest_finish_min: int
    latest_start_min: int
    latest_finish_min: int
    total_float_min: int = Field(
        description="Slack cushion in minutes before this node delays downstream fixed deadlines"
    )
    is_critical: bool = Field(
        description="True if total float is zero or negative (zero delay tolerance)"
    )


class CPMGraphResult(BaseModel):
    """Complete topological analysis of trip graph."""

    trip_id: str
    total_duration_min: int
    earliest_completion_min: int
    latest_permissible_completion_min: int
    node_metrics: List[CPMNodeMetrics]
    critical_path_node_ids: List[str] = Field(
        description="Ordered sequence of nodes forming the critical bottleneck path"
    )
    critical_nodes_count: int
    total_slack_cushion_min: int


class CriticalPathEngine:
    """Computes CPM forward and backward passes across sequential and branching travel graphs."""

    @classmethod
    def analyze_trip(cls, trip: TripDAG, critical_slack_threshold_min: int = 5) -> CPMGraphResult:
        """
        Executes CPM Forward Pass (Earliest Times) and Backward Pass (Latest Times).
        Computes Total Float = LS - ES.
        """
        active_nodes = [n for n in trip.nodes if n.active]
        if not active_nodes:
            return CPMGraphResult(
                trip_id=trip.trip_id,
                total_duration_min=0,
                earliest_completion_min=0,
                latest_permissible_completion_min=0,
                node_metrics=[],
                critical_path_node_ids=[],
                critical_nodes_count=0,
                total_slack_cushion_min=0,
            )

        eff_risk = trip.parameters.risk_multiplier
        eff_hub = trip.parameters.hub_overhead_minutes

        n_count = len(active_nodes)
        first_fixed = active_nodes[0].get_effective_fixed_start_min()
        start_min = first_fixed if first_fixed is not None else 8 * 60

        # Compute transition buffers between consecutive nodes
        transitions: List[int] = [0] * n_count
        for i in range(1, n_count):
            node = active_nodes[i]
            trans = calculate_transition_time(
                transit_min=node.transit_min,
                transit_mode=node.transit_mode,
                risk_multiplier=eff_risk,
                hub_overhead=eff_hub,
            )
            transitions[i] = trans

        # -------------------------------------------------------------
        # FORWARD PASS: Earliest Start (ES) and Earliest Finish (EF)
        # -------------------------------------------------------------
        es: List[int] = [0] * n_count
        ef: List[int] = [0] * n_count

        cursor = start_min
        for i, node in enumerate(active_nodes):
            if i == 0:
                es[i] = cursor
            else:
                cursor += transitions[i]
                fixed_start = node.get_effective_fixed_start_min()
                if node.type == NodeType.FIXED and fixed_start is not None:
                    es[i] = max(cursor, fixed_start)
                else:
                    es[i] = cursor

            ef[i] = es[i] + node.duration_min
            cursor = ef[i]

        earliest_project_finish = ef[-1]

        # -------------------------------------------------------------
        # BACKWARD PASS: Latest Finish (LF) and Latest Start (LS)
        # -------------------------------------------------------------
        lf: List[int] = [0] * n_count
        ls: List[int] = [0] * n_count

        # Target end anchor: if last node is fixed, use its end, else earliest finish
        lf[-1] = earliest_project_finish
        ls[-1] = lf[-1] - active_nodes[-1].duration_min

        for i in range(n_count - 2, -1, -1):
            next_node = active_nodes[i + 1]
            next_fixed = next_node.get_effective_fixed_start_min()

            # Permissible finish of node i must allow transition to node i+1's latest start
            latest_before_next = ls[i + 1] - transitions[i + 1]

            if next_node.type == NodeType.FIXED and next_fixed is not None:
                # If next node is strictly locked, node i MUST finish in time for next_fixed
                hard_deadline = next_fixed - transitions[i + 1]
                lf[i] = min(latest_before_next, hard_deadline)
            else:
                lf[i] = latest_before_next

            ls[i] = lf[i] - active_nodes[i].duration_min

        # -------------------------------------------------------------
        # FLOAT & CRITICAL PATH EVALUATION
        # -------------------------------------------------------------
        metrics: List[CPMNodeMetrics] = []
        critical_ids: List[str] = []
        total_float_sum = 0

        for i, node in enumerate(active_nodes):
            total_float = max(0, ls[i] - es[i])
            total_float_sum += total_float
            is_crit = total_float <= critical_slack_threshold_min

            if is_crit:
                critical_ids.append(node.id)

            metrics.append(
                CPMNodeMetrics(
                    node_id=node.id,
                    title=node.title,
                    node_type=node.type,
                    duration_min=node.duration_min,
                    transit_buffer_before_min=transitions[i],
                    earliest_start_min=es[i],
                    earliest_finish_min=ef[i],
                    latest_start_min=ls[i],
                    latest_finish_min=lf[i],
                    total_float_min=total_float,
                    is_critical=is_crit,
                )
            )

        return CPMGraphResult(
            trip_id=trip.trip_id,
            total_duration_min=earliest_project_finish - start_min,
            earliest_completion_min=earliest_project_finish,
            latest_permissible_completion_min=lf[-1],
            node_metrics=metrics,
            critical_path_node_ids=critical_ids,
            critical_nodes_count=len(critical_ids),
            total_slack_cushion_min=total_float_sum,
        )
