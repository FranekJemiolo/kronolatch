"""
Multi-Currency Group Ledger and Minimum-Transaction Debt Settlement Engine for KronoLatch.
Supports contextual itinerary node linking, uneven subgroup shares, multi-currency conversion,
and deterministic greedy min-cash-flow graph reduction.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from kronolatch.models import Expense, LedgerSettlementResult, SettlementTransfer


def compute_net_balances(
    expenses: List[Expense],
    all_travelers: Optional[List[str]] = None,
) -> Tuple[Dict[str, float], float]:
    """
    Computes net balances for all travelers in base currency.
    Returns (net_balances_dict, total_spend_base).
    Positive balance = Creditor (is owed money).
    Negative balance = Debtor (owes money).
    """
    balances: Dict[str, float] = {}
    if all_travelers:
        for t in all_travelers:
            balances[t] = 0.0

    total_spend_base = 0.0

    for exp in expenses:
        base_amt = exp.amount_in_base()
        total_spend_base += base_amt

        # Initialize payer if not present
        if exp.payer not in balances:
            balances[exp.payer] = 0.0
        balances[exp.payer] += base_amt

        # Calculate splits for participants
        parts = exp.participants
        if not parts:
            parts = [exp.payer]

        if exp.weights:
            total_weight = sum(exp.weights.get(p, 1.0) for p in parts)
            for p in parts:
                w = exp.weights.get(p, 1.0)
                share = (
                    (w / total_weight) * base_amt if total_weight > 0 else (base_amt / len(parts))
                )
                if p not in balances:
                    balances[p] = 0.0
                balances[p] -= share
        else:
            share = base_amt / len(parts)
            for p in parts:
                if p not in balances:
                    balances[p] = 0.0
                balances[p] -= share

    # Round balances to 2 decimal places to eliminate floating-point drift
    cleaned_balances: Dict[str, float] = {k: round(v, 2) for k, v in balances.items()}
    return cleaned_balances, round(total_spend_base, 2)


def settle_expenses(
    expenses: List[Expense],
    base_currency: str = "EUR",
    all_travelers: Optional[List[str]] = None,
    alternate_currency: Optional[str] = "PLN",
    alternate_rate: float = 4.30,
) -> LedgerSettlementResult:
    """
    Executes greedy minimum-cash-flow debt settlement graph reduction.
    Finds the minimum number of peer-to-peer transfers to clear all net debts.
    """
    net_balances, total_spend = compute_net_balances(expenses, all_travelers)

    debtors: List[Dict] = []
    creditors: List[Dict] = []

    for person, bal in net_balances.items():
        if bal < -0.005:
            debtors.append({"person": person, "amount": abs(bal)})
        elif bal > 0.005:
            creditors.append({"person": person, "amount": bal})

    # Sort descending by amount for greedy matching
    debtors.sort(key=lambda x: x["amount"], reverse=True)
    creditors.sort(key=lambda x: x["amount"], reverse=True)

    transfers: List[SettlementTransfer] = []
    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):
        pay = min(debtors[i]["amount"], creditors[j]["amount"])
        pay = round(pay, 2)

        if pay > 0.005:
            alt_amt = round(pay * alternate_rate, 2) if alternate_currency else None
            transfers.append(
                SettlementTransfer(
                    from_person=debtors[i]["person"],
                    to_person=creditors[j]["person"],
                    amount=pay,
                    currency=base_currency,
                    amount_alternate=alt_amt,
                    alternate_currency=alternate_currency,
                )
            )

        debtors[i]["amount"] = round(debtors[i]["amount"] - pay, 4)
        creditors[j]["amount"] = round(creditors[j]["amount"] - pay, 4)

        if debtors[i]["amount"] <= 0.005:
            i += 1
        if creditors[j]["amount"] <= 0.005:
            j += 1

    return LedgerSettlementResult(
        base_currency=base_currency,
        total_spend_base=total_spend,
        net_balances=net_balances,
        transfers=transfers,
    )
