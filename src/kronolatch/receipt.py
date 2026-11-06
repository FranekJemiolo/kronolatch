"""
Itemized Receipt Parsing & Proportional Overhead Splitter for KronoLatch.
Splits restaurant, supermarket, and group bills where different travelers ordered
different items, distributing tax, tip, and service fees with cent-exact precision.
"""

from __future__ import annotations

import re
from typing import Dict, List

from pydantic import BaseModel, Field

from kronolatch.models import Expense


class ReceiptLineItem(BaseModel):
    """Single itemized entry on a receipt."""

    description: str
    price: float = Field(ge=0.0)
    participants: List[str] = Field(
        min_length=1, description="Travelers sharing this specific item"
    )


class ItemizedBill(BaseModel):
    """Full itemized receipt with tax, tip, and payer information."""

    title: str = "Group Restaurant / Store Bill"
    payer: str
    currency: str = "EUR"
    items: List[ReceiptLineItem] = Field(min_length=1)
    tax: float = Field(default=0.0, ge=0.0)
    tip: float = Field(default=0.0, ge=0.0)
    service_charge: float = Field(default=0.0, ge=0.0)


class SplitResult(BaseModel):
    """Breakdown of individual liabilities and converted Expense entities."""

    title: str
    payer: str
    currency: str
    subtotal: float
    total_bill: float
    overhead_total: float
    overhead_percentage: float
    traveler_liabilities: Dict[str, float] = Field(
        description="Exact rounded amount owed by each traveler"
    )
    generated_expenses: List[Expense] = Field(
        description="Normalized Expense objects ready for ledger settlement"
    )


class ReceiptSplitter:
    """Computes exact proportional expense allocation for itemized bills."""

    @classmethod
    def calculate_split(cls, bill: ItemizedBill) -> SplitResult:
        """
        Computes proportional liability for each traveler:
        Liabilities sum exactly to total_bill with penny-exact rounding.
        """
        subtotal = round(sum(item.price for item in bill.items), 2)
        overhead = round(bill.tax + bill.tip + bill.service_charge, 2)
        total_bill = round(subtotal + overhead, 2)

        overhead_ratio = (overhead / subtotal) if subtotal > 0 else 0.0

        # Calculate raw liability per traveler
        raw_shares: Dict[str, float] = {}
        for item in bill.items:
            count = len(item.participants)
            per_person_base = item.price / count
            per_person_with_overhead = per_person_base * (1.0 + overhead_ratio)

            for traveler in item.participants:
                raw_shares[traveler] = raw_shares.get(traveler, 0.0) + per_person_with_overhead

        # Cent-exact rounding and discrepancy reconciliation
        rounded_shares: Dict[str, float] = {t: round(amt, 2) for t, amt in raw_shares.items()}
        sum_rounded = round(sum(rounded_shares.values()), 2)
        discrepancy = round(total_bill - sum_rounded, 2)

        # Distribute any fractional cent discrepancy to the largest share
        if abs(discrepancy) > 0.0 and rounded_shares:
            highest_payer = max(rounded_shares.keys(), key=lambda k: rounded_shares[k])
            rounded_shares[highest_payer] = round(rounded_shares[highest_payer] + discrepancy, 2)

        # Convert to KronoLatch Expense records
        # If payer is part of the group, their net balance will correctly reflect total paid vs consumed
        generated_expenses: List[Expense] = []
        for i, item in enumerate(bill.items):
            effective_item_amount = round(item.price * (1.0 + overhead_ratio), 2)
            generated_expenses.append(
                Expense(
                    id=f"exp_rcpt_{i + 1}",
                    title=f"{item.description} ({bill.title})",
                    payer=bill.payer,
                    amount=effective_item_amount,
                    currency=bill.currency,
                    participants=item.participants,
                    node_id=None,
                )
            )

        return SplitResult(
            title=bill.title,
            payer=bill.payer,
            currency=bill.currency,
            subtotal=subtotal,
            total_bill=total_bill,
            overhead_total=overhead,
            overhead_percentage=round(overhead_ratio * 100.0, 1),
            traveler_liabilities=rounded_shares,
            generated_expenses=generated_expenses,
        )

    @classmethod
    def parse_receipt_text(
        cls,
        text: str,
        payer: str,
        default_travelers: List[str],
        title: str = "Restaurant Bill",
        currency: str = "EUR",
        tip: float = 0.0,
    ) -> ItemizedBill:
        """
        Parses receipt lines in common formats:
        Example line: '2x Pizza Margherita 18.00 [Franek, Anna]' or 'Wine Bottle 24.50'
        """
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        items: List[ReceiptLineItem] = []
        tax = 0.0
        service = 0.0

        for line in lines:
            # Check for tax or coperto lines
            if re.search(r"\b(tax|iva|vat)\b", line, re.IGNORECASE):
                m_tax = re.search(r"(\d+[.,]\d{2})", line)
                if m_tax:
                    tax += float(m_tax.group(1).replace(",", "."))
                continue
            if re.search(r"\b(coperto|service)\b", line, re.IGNORECASE):
                m_srv = re.search(r"(\d+[.,]\d{2})", line)
                if m_srv:
                    service += float(m_srv.group(1).replace(",", "."))
                continue

            # Standard item line: Name Price [Participants]
            # Match price at end or before brackets
            price_match = re.search(r"(\d+[.,]\d{2})", line)
            if not price_match:
                continue

            price = float(price_match.group(1).replace(",", "."))
            # Extract description (everything before price)
            desc = line[: price_match.start()].strip().lstrip("0123456789xX*•- ")
            if not desc:
                desc = "Menu Item"

            # Check for explicit bracketed participants: [Franek, Anna]
            participants = default_travelers
            part_match = re.search(r"\[(.*?)\]", line)
            if part_match:
                custom_parts = [p.strip() for p in part_match.group(1).split(",") if p.strip()]
                if custom_parts:
                    participants = custom_parts

            items.append(
                ReceiptLineItem(
                    description=desc,
                    price=price,
                    participants=participants,
                )
            )

        if not items:
            items.append(
                ReceiptLineItem(
                    description="Group Dinner",
                    price=50.0,
                    participants=default_travelers,
                )
            )

        return ItemizedBill(
            title=title,
            payer=payer,
            currency=currency,
            items=items,
            tax=tax,
            tip=tip,
            service_charge=service,
        )
