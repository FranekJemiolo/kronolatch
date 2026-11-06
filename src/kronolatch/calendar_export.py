"""
RFC 5545 iCalendar (.ics) Generator for KronoLatch.
Converts verified TripDAG itineraries into standard calendar events with transition-aware
VALARM alarms scheduled ahead of physical station and airport buffers.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

from kronolatch.models import (
    Category,
    NodeType,
    TransitMode,
    TripDAG,
)


class CalendarExporter:
    """Generates clean, RFC 5545-compliant .ics files with buffer-aware reminder alarms."""

    @classmethod
    def generate_ics(
        cls,
        trip: TripDAG,
        base_date: Optional[datetime.date] = None,
    ) -> str:
        """
        Generate RFC 5545 iCalendar formatted string for all active nodes in the TripDAG.
        """
        d = base_date or datetime.date(2026, 6, 15)
        now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//KronoLatch//Deterministic Travel Orchestrator//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:{trip.title}",
            "X-WR-TIMEZONE:Europe/Rome",
        ]

        active_nodes = [n for n in trip.nodes if n.active]
        first_start = active_nodes[0].get_effective_fixed_start_min() if active_nodes else 8 * 60
        cursor = first_start if first_start is not None else 8 * 60

        for idx, node in enumerate(active_nodes):
            if idx > 0:
                cursor += node.transit_min + 15

            start_m = (
                node.get_effective_fixed_start_min()
                if node.type == NodeType.FIXED and node.get_effective_fixed_start_min() is not None
                else cursor
            )
            end_m = start_m + node.duration_min
            cursor = end_m

            # Calculate start and end datetimes
            start_dt = datetime.datetime.combine(
                d, datetime.time(hour=(start_m // 60) % 24, minute=start_m % 60)
            )
            end_dt = datetime.datetime.combine(
                d, datetime.time(hour=(end_m // 60) % 24, minute=end_m % 60)
            )

            dtstart_str = start_dt.strftime("%Y%m%dT%H%M%S")
            dtend_str = end_dt.strftime("%Y%m%dT%H%M%S")

            # Description metadata
            desc_parts = [
                f"KronoLatch Node ID: {node.id}",
                f"Type: {node.type.value.upper()}",
                f"Category: {node.category.value.upper()}",
                f"Duration: {node.duration_min} min",
            ]
            if node.pnr:
                desc_parts.append(f"PNR / Confirmation: {node.pnr}")
            if node.official_domain:
                desc_parts.append(f"Official Verified Portal: {node.official_domain}")
            if node.notes:
                desc_parts.append(f"Notes: {node.notes}")

            description_clean = "\\n".join(desc_parts)

            # Determine buffer-aware alarm offset
            # Flights: alarm 120m ahead; Rail: 25m ahead; Sightseeing: 20m ahead
            if node.category == Category.FLIGHT or node.transit_mode == TransitMode.FLIGHT:
                alarm_offset_min = 120 + node.transit_min
            elif node.category == Category.RAIL or node.transit_mode == TransitMode.TRAIN:
                alarm_offset_min = 25 + node.transit_min
            else:
                alarm_offset_min = max(15, node.transit_min + 10)

            event_lines = [
                "BEGIN:VEVENT",
                f"UID:{node.id}-{trip.trip_id}@kronolatch.org",
                f"DTSTAMP:{now_utc}",
                f"DTSTART:{dtstart_str}",
                f"DTEND:{dtend_str}",
                f"SUMMARY:{node.title}",
                f"DESCRIPTION:{description_clean}",
                f"LOCATION:{trip.destination}",
                "STATUS:CONFIRMED",
                "BEGIN:VALARM",
                f"TRIGGER:-PT{alarm_offset_min}M",
                "ACTION:DISPLAY",
                f"DESCRIPTION:KronoLatch Alert: {alarm_offset_min}m buffer ahead of {node.title}",
                "END:VALARM",
                "END:VEVENT",
            ]
            lines.extend(event_lines)

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"

    @classmethod
    def export_to_file(
        cls,
        trip: TripDAG,
        target_path: str,
        base_date: Optional[datetime.date] = None,
    ) -> Path:
        """Saves generated .ics content to a local path."""
        content = cls.generate_ics(trip, base_date=base_date)
        p = Path(target_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p
