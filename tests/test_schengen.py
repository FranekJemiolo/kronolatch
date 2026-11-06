"""
Unit tests for KronoLatch Schengen 90/180-Day Rule Calculator (Phase 10).
"""

from __future__ import annotations

from kronolatch.schengen import SchengenCalculator, StayInterval


def test_schengen_compliant_short_stay():
    """Verify standard short-stay calculation with no prior visits."""
    past: list[StayInterval] = []
    planned = StayInterval(entry_date="2026-06-01", exit_date="2026-06-15")  # 15 days

    audit = SchengenCalculator.audit_stay(
        past_stays=past,
        planned_stay=planned,
        passport_expiry_date="2028-12-31",
    )

    assert audit.is_compliant
    assert audit.planned_stay_days == 15
    assert audit.max_days_used_in_window == 15
    assert audit.days_remaining_on_entry == 90
    assert audit.days_remaining_on_exit == 75
    assert audit.overstay_days == 0
    assert audit.passport_valid


def test_schengen_multi_entry_overstay_detection():
    """Verify that multiple visits exceeding 90 days in rolling 180 days flag an overstay."""
    # Stay 1: 60 days in Schengen (Jan 1 to March 1)
    past = [
        StayInterval(entry_date="2026-01-01", exit_date="2026-03-01"),  # 60 days
    ]
    # Stay 2: 40 days starting May 1 (within 180 days of Jan 1!)
    # Total = 60 + 40 = 100 days (> 90!)
    planned = StayInterval(entry_date="2026-05-01", exit_date="2026-06-09")  # 40 days

    audit = SchengenCalculator.audit_stay(
        past_stays=past,
        planned_stay=planned,
    )

    assert not audit.is_compliant
    assert audit.overstay_days > 0
    assert audit.max_days_used_in_window > 90
    assert audit.earliest_reentry_date is not None


def test_passport_validity_rule():
    """Verify passport 3-month rule beyond planned Schengen departure."""
    planned = StayInterval(entry_date="2026-06-01", exit_date="2026-06-15")

    # Passport expiring July 1, 2026 is only 16 days after exit (must be >= 90 days)
    audit = SchengenCalculator.audit_stay(
        past_stays=[],
        planned_stay=planned,
        passport_expiry_date="2026-07-01",
    )

    assert not audit.passport_valid
    assert audit.passport_warning is not None
    assert "at least 3 months" in audit.passport_warning
