"""
Unit tests for KronoLatch Itemized Receipt Splitter (Phase 9).
"""

from __future__ import annotations

from kronolatch.receipt import ItemizedBill, ReceiptLineItem, ReceiptSplitter


def test_exact_penny_conservation():
    """Verify that the sum of individual liabilities equals the total bill to the cent."""
    items = [
        ReceiptLineItem(description="Truffle Pasta", price=32.00, participants=["Franek"]),
        ReceiptLineItem(
            description="Chianti Wine Bottle", price=25.00, participants=["Franek", "Anna"]
        ),
        ReceiptLineItem(description="Margherita Pizza", price=12.00, participants=["Marek"]),
        ReceiptLineItem(
            description="Tiramisu to share",
            price=14.00,
            participants=["Franek", "Anna", "Marek", "Kasia"],
        ),
    ]

    bill = ItemizedBill(
        title="Trastevere Dinner",
        payer="Franek",
        currency="EUR",
        items=items,
        tax=8.30,
        tip=10.00,
        service_charge=4.00,
    )

    res = ReceiptSplitter.calculate_split(bill)

    # Subtotal = 32 + 25 + 12 + 14 = 83.00
    assert res.subtotal == 83.00
    # Overhead = 8.30 + 10.00 + 4.00 = 22.30
    assert res.overhead_total == 22.30
    # Total = 105.30
    assert res.total_bill == 105.30

    # Exact penny conservation invariant: sum of liabilities == total bill
    sum_liabilities = round(sum(res.traveler_liabilities.values()), 2)
    assert sum_liabilities == res.total_bill

    # Franek ordered Truffle Pasta (32) + half wine (12.5) + quarter dessert (3.5) = 48.00 base
    # Kasia only had dessert (3.50 base)
    assert res.traveler_liabilities["Franek"] > res.traveler_liabilities["Kasia"]
    assert res.traveler_liabilities["Kasia"] > 0.0


def test_parse_receipt_text():
    """Verify parsing of raw receipt text with bracketed custom diners."""
    raw_text = """
    2x Bruschetta Mista 14.00 [Franek, Anna]
    Bistecca alla Fiorentina 45.00 [Marek, Kasia]
    House Wine Carafe 16.00 [Franek, Marek]
    Coperto 6.00
    IVA Tax 8.10
    """
    bill = ReceiptSplitter.parse_receipt_text(
        text=raw_text,
        payer="Franek",
        default_travelers=["Franek", "Anna", "Marek", "Kasia"],
        title="Florence Trattoria",
        tip=5.00,
    )

    assert len(bill.items) == 3
    assert bill.service_charge == 6.00
    assert bill.tax == 8.10
    assert bill.tip == 5.00

    split = ReceiptSplitter.calculate_split(bill)
    assert round(sum(split.traveler_liabilities.values()), 2) == split.total_bill
