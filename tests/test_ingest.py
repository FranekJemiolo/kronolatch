"""
Tests for KronoLatch Ticket Ingestion Engine (PDF and Text parsing).
"""

from __future__ import annotations

from pathlib import Path

import pypdf

from kronolatch.ingest import ParsedTicket, TicketIngestor
from kronolatch.models import (
    Category,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
)


def test_parse_train_ticket_text():
    """Verify parsing of European rail booking confirmation."""
    raw_text = """
    TRENITALIA - BIGLIETTO ELETTRONICO
    Codice Prenotazione (PNR): TRN98X
    Treno: Frecciarossa 9540
    Da: Roma Termini
    A: Firenze S.M. Novella
    Data: 15/05/2026
    Partenza: 08:20
    Arrivo: 09:55
    Carrozza: 4
    Posto: 12D (Standard Silenzio)
    Totale: 45.90 EUR
    """
    parsed: ParsedTicket = TicketIngestor.parse(raw_text)

    assert parsed.pnr == "TRN98X"
    assert parsed.service_type == Category.RAIL
    assert parsed.transit_mode == TransitMode.TRAIN
    assert "9540" in (parsed.service_number or "")
    assert "Roma Termini" in parsed.origin
    assert "Firenze" in parsed.destination
    assert parsed.departure_time == "08:20"
    assert parsed.arrival_time == "09:55"
    assert parsed.duration_minutes() == 95
    assert parsed.coach_carriage == "4"
    assert parsed.seat == "12D"
    assert parsed.price == 45.90
    assert parsed.currency == "EUR"

    node = parsed.to_trip_node("node_train_01")
    assert node.id == "node_train_01"
    assert node.type == NodeType.FIXED
    assert node.fixed_start_time == "08:20"
    assert node.duration_min == 95
    assert "TRN98X" in (node.notes or "")


def test_parse_flight_ticket_text():
    """Verify parsing of Airline e-ticket and boarding confirmation."""
    raw_text = """
    AIRLINE CONFIRMATION - BOARDING PASS
    Booking Ref (PNR): RYR77K
    Flight: FR 9941
    From: Warsaw Modlin WMI
    To: Rome Ciampino CIA
    Date: 2026-06-10
    Dep: 14:15
    Arr: 16:45
    Seat: 18B
    Total Paid: 189.50 PLN
    """
    parsed: ParsedTicket = TicketIngestor.parse(raw_text)

    assert parsed.pnr == "RYR77K"
    assert parsed.service_type == Category.FLIGHT
    assert parsed.transit_mode == TransitMode.FLIGHT
    assert "9941" in (parsed.service_number or "")
    assert "WMI" in parsed.origin or "Warsaw" in parsed.origin
    assert "CIA" in parsed.destination or "Rome" in parsed.destination
    assert parsed.departure_time == "14:15"
    assert parsed.arrival_time == "16:45"
    assert parsed.duration_minutes() == 150
    assert parsed.seat == "18B"
    assert parsed.price == 189.50
    assert parsed.currency == "PLN"

    node = parsed.to_trip_node("flight_node_01")
    assert node.type == NodeType.FIXED
    assert node.fixed_start_time == "14:15"
    assert node.duration_min == 150


def test_pdf_extraction_roundtrip(tmp_path: Path):
    """Generate a dynamic PDF with pypdf and verify TicketIngestor extracts from it."""
    pdf_path = tmp_path / "test_ticket.pdf"

    # Create a simple PDF containing ticket text
    writer = pypdf.PdfWriter()
    # Add a blank page
    writer.add_blank_page(width=612, height=792)

    # Minimal valid PDF with text stream
    content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 210 >>
stream
BT
/F1 12 Tf
72 712 Td
(ITALO TRENO BOOKING PNR: ITL889) Tj
0 -20 Td
(Train: Italo 9912 From: Roma Termini To: Venezia S.L.) Tj
0 -20 Td
(Dep: 09:30 Arr: 13:25 Coach: 2 Seat: 15) Tj
0 -20 Td
(Total: 59.00 EUR) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000244 00000 n
0000000506 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
578
%%EOF"""
    pdf_path.write_bytes(content)

    parsed = TicketIngestor.parse(pdf_path)
    assert parsed.pnr == "ITL889"
    assert parsed.departure_time == "09:30"
    assert parsed.arrival_time == "13:25"
    assert parsed.coach_carriage == "2"
    assert parsed.seat == "15"
    assert parsed.price == 59.00
    assert parsed.currency == "EUR"


def test_ingest_into_trip_dag():
    """Verify inserting parsed ticket node into an existing TripDAG."""
    base_trip = TripDAG(
        trip_id="rome-2026",
        title="Rome Exploration",
        destination="Rome, Italy",
        travelers=["Franek", "Anna"],
        nodes=[
            TripNode(
                id="hotel_checkin",
                title="Hotel Check-in",
                type=NodeType.FIXED,
                fixed_start_time="14:00",
                duration_min=45,
            )
        ],
    )

    ticket_text = """
    Treno: Frecciarossa 1000
    PNR: FR9982
    From: Napoli Centrale To: Roma Termini
    Partenza: 10:15 Arrivo: 11:25
    Coach: 5 Seat: 21B
    """

    updated_trip = TicketIngestor.ingest_into_trip(
        ticket_text, base_trip, node_id="frecciarossa_leg"
    )

    assert len(updated_trip.nodes) == 2
    # Since train departs at 10:15 and hotel is at 14:00, train node must be first!
    assert updated_trip.nodes[0].id == "frecciarossa_leg"
    assert updated_trip.nodes[0].fixed_start_time == "10:15"
    assert updated_trip.nodes[0].type == NodeType.FIXED
    assert updated_trip.nodes[1].id == "hotel_checkin"
    assert updated_trip.nodes[1].fixed_start_time == "14:00"
