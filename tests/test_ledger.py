"""
Unit tests for KronoLatch Multi-Currency Group Ledger and Settlement Engine.
Validates multi-currency conversion, uneven subgroup allocations, and greedy minimum transfer debt settlement.
"""

from kronolatch.ledger import compute_net_balances, settle_expenses
from kronolatch.models import Expense


def test_asymmetric_subgroup_cost_split_case():
    """
    Test Case 3 from KronoLatch Specification:
    4 travelers: Franek, Anna, Marek, Kasia.
    1. Franek pays €160 for Rental Car + Fuel (split Franek & Anna)
    2. Marek pays €90 for High-Speed Train (split Marek & Kasia)
    3. Kasia pays €200 for Group Dinner (split equally all 4)
    Expected balances:
      Franek : +€30
      Anna   : -€130
      Marek  : -€5
      Kasia  : +€105
    Minimum settlement transfers: at most 3 transfers totaling €135.
    """
    travelers = ["Franek", "Anna", "Marek", "Kasia"]
    expenses = [
        Expense(
            id="e1",
            title="Rental Car + Fuel",
            payer="Franek",
            amount=160.0,
            currency="EUR",
            participants=["Franek", "Anna"],
        ),
        Expense(
            id="e2",
            title="High-Speed Train",
            payer="Marek",
            amount=90.0,
            currency="EUR",
            participants=["Marek", "Kasia"],
        ),
        Expense(
            id="e3",
            title="Group Dinner",
            payer="Kasia",
            amount=200.0,
            currency="EUR",
            participants=["Franek", "Anna", "Marek", "Kasia"],
        ),
    ]

    balances, total_spend = compute_net_balances(expenses, travelers)
    assert total_spend == 450.0
    assert balances["Franek"] == 30.0
    assert balances["Anna"] == -130.0
    assert balances["Marek"] == -5.0
    assert balances["Kasia"] == 105.0

    # Invariant: Zero-sum balance
    assert sum(balances.values()) == 0.0

    result = settle_expenses(expenses, base_currency="EUR", all_travelers=travelers)
    assert len(result.transfers) <= 3
    total_transferred = sum(t.amount for t in result.transfers)
    assert round(total_transferred, 2) == 135.0


def test_multi_currency_conversion():
    """Validates expense conversion from PLN to EUR base currency."""
    expenses = [
        Expense(
            id="p1",
            title="Warsaw Modlin Airport Parking",
            payer="Franek",
            amount=215.0,  # 215 PLN @ 4.30 = 50 EUR
            currency="PLN",
            exchange_rate_to_base=4.30,
            participants=["Franek", "Anna"],
        ),
    ]

    balances, total_spend = compute_net_balances(expenses, ["Franek", "Anna"])
    assert total_spend == 50.0
    assert balances["Franek"] == 25.0
    assert balances["Anna"] == -25.0

    result = settle_expenses(expenses, base_currency="EUR", all_travelers=["Franek", "Anna"])
    assert len(result.transfers) == 1
    tr = result.transfers[0]
    assert tr.from_person == "Anna"
    assert tr.to_person == "Franek"
    assert tr.amount == 25.0
    assert tr.amount_alternate == 107.5  # 25 * 4.30 PLN
