"""
Schengen 90/180-Day Rule & Zero-Cloud Visa Compliance Vault for KronoLatch.
Deterministic implementation conforming strictly to EU Regulation (EU) 2016/399.
Runs 100% locally with zero cloud telemetry or sensitive border data leakage.
"""

from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field


class StayInterval(BaseModel):
    """A continuous entry and exit period in the Schengen Area."""

    entry_date: str = Field(description="Date of entry (YYYY-MM-DD)")
    exit_date: str = Field(description="Date of exit (YYYY-MM-DD)")
    country: Optional[str] = "Schengen Area"
    purpose: Optional[str] = "Tourism"

    def get_dates(self) -> Set[datetime.date]:
        """Returns set of all calendar days present in Schengen (entry and exit days both count)."""
        start = datetime.date.fromisoformat(self.entry_date)
        end = datetime.date.fromisoformat(self.exit_date)
        if start > end:
            raise ValueError(
                f"Entry date {self.entry_date} cannot be after exit date {self.exit_date}"
            )

        days: Set[datetime.date] = set()
        curr = start
        while curr <= end:
            days.add(curr)
            curr += datetime.timedelta(days=1)
        return days


class SchengenAuditResult(BaseModel):
    """Official Schengen rolling 90/180-day compliance evaluation."""

    is_compliant: bool
    total_past_days: int
    planned_stay_days: int
    max_days_used_in_window: int = Field(
        description="Highest rolling 180-day count during the planned stay"
    )
    days_remaining_on_entry: int
    days_remaining_on_exit: int
    overstay_days: int = 0
    earliest_reentry_date: Optional[str] = None
    passport_valid: bool = True
    passport_warning: Optional[str] = None
    daily_breakdown: List[Dict[str, object]] = Field(default_factory=list)


class SchengenCalculator:
    """Official rolling 180-day window calculator for Schengen Area short-stays."""

    @classmethod
    def audit_stay(
        cls,
        past_stays: List[StayInterval],
        planned_stay: StayInterval,
        passport_expiry_date: Optional[str] = None,
    ) -> SchengenAuditResult:
        """
        Calculates short-stay compliance under Regulation (EU) 2016/399.
        Both entry and exit dates count as full days in the Schengen Area.
        """
        # Collect all past Schengen days
        past_days: Set[datetime.date] = set()
        for stay in past_stays:
            past_days.update(stay.get_dates())

        planned_days = planned_stay.get_dates()
        planned_start = datetime.date.fromisoformat(planned_stay.entry_date)
        planned_end = datetime.date.fromisoformat(planned_stay.exit_date)

        all_days = past_days.union(planned_days)

        # For every day during the planned stay, evaluate the 180-day lookback window: [d - 179, d]
        max_used = 0
        overstay = 0
        breakdown: List[Dict[str, object]] = []

        curr = planned_start
        days_on_entry = 0
        days_on_exit = 0

        while curr <= planned_end:
            window_start = curr - datetime.timedelta(days=179)
            # Count how many days in [window_start, curr] were spent in Schengen
            used_in_window = sum(1 for d in all_days if window_start <= d <= curr)

            if used_in_window > max_used:
                max_used = used_in_window

            if used_in_window > 90:
                day_overstay = used_in_window - 90
                if day_overstay > overstay:
                    overstay = day_overstay

            remaining = max(0, 90 - used_in_window)

            if curr == planned_start:
                # On entry, calculate remaining days based on past days only
                past_in_window = sum(1 for d in past_days if window_start <= d < planned_start)
                days_on_entry = max(0, 90 - past_in_window)

            if curr == planned_end:
                days_on_exit = remaining

            breakdown.append(
                {
                    "date": curr.isoformat(),
                    "window_start": window_start.isoformat(),
                    "days_in_180": used_in_window,
                    "remaining": remaining,
                    "is_overstay": used_in_window > 90,
                }
            )
            curr += datetime.timedelta(days=1)

        is_compliant = overstay == 0

        # Calculate earliest re-entry date if 90 days are reached
        earliest_reentry: Optional[str] = None
        if max_used >= 90:
            test_date = planned_end + datetime.timedelta(days=1)
            for _ in range(185):
                test_window_start = test_date - datetime.timedelta(days=179)
                count = sum(1 for d in all_days if test_window_start <= d <= test_date)
                if count < 90:
                    earliest_reentry = test_date.isoformat()
                    break
                test_date += datetime.timedelta(days=1)

        # Passport validity check: valid for at least 3 months (90 days) beyond planned departure
        passport_valid = True
        passport_warning = None
        if passport_expiry_date:
            try:
                pass_exp = datetime.date.fromisoformat(passport_expiry_date)
                min_validity = planned_end + datetime.timedelta(days=90)
                if pass_exp < planned_end:
                    passport_valid = False
                    passport_warning = f"CRITICAL: Passport expires on {passport_expiry_date}, BEFORE your planned departure ({planned_stay.exit_date})!"
                elif pass_exp < min_validity:
                    passport_valid = False
                    passport_warning = f"WARNING: Passport expires on {passport_expiry_date}. EU requires at least 3 months validity after departure ({min_validity.isoformat()})."
            except ValueError:
                passport_warning = f"Invalid passport expiry date format '{passport_expiry_date}'"

        return SchengenAuditResult(
            is_compliant=is_compliant,
            total_past_days=len(past_days),
            planned_stay_days=len(planned_days),
            max_days_used_in_window=max_used,
            days_remaining_on_entry=days_on_entry,
            days_remaining_on_exit=days_on_exit,
            overstay_days=overstay,
            earliest_reentry_date=earliest_reentry,
            passport_valid=passport_valid,
            passport_warning=passport_warning,
            daily_breakdown=breakdown,
        )
