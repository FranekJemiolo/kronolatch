"""
Unit tests for KronoLatch RFC 5545 iCalendar Exporter (Phase 11).
"""

from __future__ import annotations

import datetime
from pathlib import Path

from kronolatch.calendar_export import CalendarExporter
from kronolatch.models import (
    Category,
    DAGParameters,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
)


def create_sample_trip() -> TripDAG:
    nodes = [
        TripNode(
            id="n1_flight",
            title="Flight WMI → FCO",
            type=NodeType.FIXED,
            category=Category.FLIGHT,
            transit_mode=TransitMode.FLIGHT,
            transit_min=0,
            duration_min=140,
            fixed_start_min=8 * 60,
            pnr="RYR-1234",
            official_domain="ryanair.com",
            active=True,
        ),
        TripNode(
            id="n2_colosseum",
            title="Colosseum Arena Entry",
            type=NodeType.FIXED,
            category=Category.SIGHTSEEING,
            transit_mode=TransitMode.WALK,
            transit_min=20,
            duration_min=90,
            fixed_start_min=14 * 60,
            pnr="COL-998",
            official_domain="ticketing.colosseo.it",
            active=True,
        ),
    ]
    return TripDAG(
        trip_id="rome-cal-test",
        title="Rome Calendar Test Trip",
        destination="Rome, Italy",
        travelers=["Alice"],
        parameters=DAGParameters(),
        nodes=nodes,
    )


def test_calendar_ics_structure():
    """Verify RFC 5545 structure, events count, and buffer alarms."""
    trip = create_sample_trip()
    ics_text = CalendarExporter.generate_ics(trip, base_date=datetime.date(2026, 7, 10))

    assert "BEGIN:VCALENDAR" in ics_text
    assert "VERSION:2.0" in ics_text
    assert "END:VCALENDAR" in ics_text
    assert ics_text.count("BEGIN:VEVENT") == 2
    assert ics_text.count("BEGIN:VALARM") == 2

    # Verify PNR and official portal were embedded in description
    assert "RYR-1234" in ics_text
    assert "ticketing.colosseo.it" in ics_text

    # Flight alarm should have >= 120m buffer trigger
    assert "-PT120M" in ics_text or "-PT140M" in ics_text


def test_calendar_export_to_file(tmp_path: Path):
    """Verify writing .ics file to disk."""
    trip = create_sample_trip()
    out_file = tmp_path / "test_trip.ics"

    saved_path = CalendarExporter.export_to_file(trip, str(out_file))

    assert saved_path.exists()
    content = saved_path.read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "Flight WMI → FCO" in content
