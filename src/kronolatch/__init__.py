"""
KronoLatch: Deterministic-first, agent-assisted trip orchestrator,
anti-phishing ticket domain verifier, temporal DAG validator,
and multi-currency group expense splitter.
"""

__version__ = "1.0.0"

from kronolatch.dag_engine import calculate_transition_time, optimize_and_cut, validate_dag
from kronolatch.ledger import compute_net_balances, settle_expenses
from kronolatch.models import (
    DAGAuditResult,
    DAGParameters,
    Expense,
    LedgerSettlementResult,
    NodeScheduleResult,
    NodeType,
    SettlementTransfer,
    TransitMode,
    TripDAG,
    TripNode,
    VendorCheckResult,
    VerificationStatus,
)
from kronolatch.sheets import (
    export_expenses_to_csv,
    export_itinerary_to_csv,
    export_settlement_to_csv,
    google_sheets_url_to_csv_export_url,
    parse_expenses_csv,
    parse_itinerary_csv,
)
from kronolatch.verifier import normalize_root_domain, verify_vendor_url

__all__ = [
    "TripDAG",
    "TripNode",
    "NodeType",
    "TransitMode",
    "DAGParameters",
    "DAGAuditResult",
    "NodeScheduleResult",
    "Expense",
    "SettlementTransfer",
    "LedgerSettlementResult",
    "VendorCheckResult",
    "VerificationStatus",
    "validate_dag",
    "optimize_and_cut",
    "calculate_transition_time",
    "normalize_root_domain",
    "verify_vendor_url",
    "compute_net_balances",
    "settle_expenses",
    "google_sheets_url_to_csv_export_url",
    "parse_itinerary_csv",
    "export_itinerary_to_csv",
    "parse_expenses_csv",
    "export_expenses_to_csv",
    "export_settlement_to_csv",
]
