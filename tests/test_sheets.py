"""
Unit tests for KronoLatch Google Spreadsheets and CSV / XLS Import & Export Engine.
"""

from kronolatch.ledger import settle_expenses
from kronolatch.models import (
    Category,
    Expense,
    NodeType,
    TransitMode,
    TripNode,
)
from kronolatch.sheets import (
    export_expenses_to_csv,
    export_itinerary_to_csv,
    export_settlement_to_csv,
    google_sheets_url_to_csv_export_url,
    parse_expenses_csv,
    parse_itinerary_csv,
)


def test_google_sheets_url_transformation():
    # Standard view / edit link
    edit_url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?usp=sharing"
    export_url = google_sheets_url_to_csv_export_url(edit_url)
    assert (
        export_url
        == "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=csv"
    )

    # With gid query param
    gid_url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?gid=987654321#gid=987654321"
    export_with_gid = google_sheets_url_to_csv_export_url(gid_url)
    assert "export?format=csv&gid=987654321" in export_with_gid

    # With gid in fragment only
    frag_url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms#gid=112233"
    export_frag = google_sheets_url_to_csv_export_url(frag_url)
    assert "export?format=csv&gid=112233" in export_frag

    # Non-Google Sheets URL
    plain_url = "https://example.com/data.csv"
    assert google_sheets_url_to_csv_export_url(plain_url) == plain_url


def test_itinerary_csv_roundtrip():
    original_nodes = [
        TripNode(
            id="n1",
            title="Flight Ryanair 9941",
            type=NodeType.FIXED,
            category=Category.FLIGHT,
            transit_mode=TransitMode.FLIGHT,
            transit_min=0,
            duration_min=145,
            fixed_start_time="08:00",
            priority=10,
            official_domain="ryanair.com",
            pnr="RYR-9941K",
            notes="Check-in 2h prior",
        ),
        TripNode(
            id="n2",
            title="Leonardo Express Airport Train",
            type=NodeType.FLEXIBLE,
            category=Category.RAIL,
            transit_mode=TransitMode.TRAIN,
            transit_min=25,
            duration_min=32,
            priority=8,
            official_domain="trenitalia.com",
        ),
    ]

    csv_data = export_itinerary_to_csv(original_nodes)
    assert "Title" in csv_data
    assert "Flight Ryanair 9941" in csv_data
    assert "ryanair.com" in csv_data

    parsed_nodes = parse_itinerary_csv(csv_data)
    assert len(parsed_nodes) == 2
    assert parsed_nodes[0].title == "Flight Ryanair 9941"
    assert parsed_nodes[0].type == NodeType.FIXED
    assert parsed_nodes[0].category == Category.FLIGHT
    assert parsed_nodes[0].fixed_start_time == "08:00"
    assert parsed_nodes[0].official_domain == "ryanair.com"
    assert parsed_nodes[0].pnr == "RYR-9941K"

    assert parsed_nodes[1].title == "Leonardo Express Airport Train"
    assert parsed_nodes[1].type == NodeType.FLEXIBLE
    assert parsed_nodes[1].category == Category.RAIL
    assert parsed_nodes[1].transit_min == 25
    assert parsed_nodes[1].duration_min == 32


def test_itinerary_csv_flexible_headers_and_delimiters():
    # Messy user-created CSV with semicolons and custom column titles
    custom_csv = (
        "Activity;Kind;Transport;Travel Min;Length Min;Slot Time;Official Link\n"
        "Colosseum Visit;Fixed Entry;Walk;20;120;15:30;ticketing.colosseo.it\n"
        "Trastevere Pasta;Flexible;Walk;15;60;;maps.google.com\n"
    )
    nodes = parse_itinerary_csv(custom_csv)
    assert len(nodes) == 2
    assert nodes[0].title == "Colosseum Visit"
    assert nodes[0].type == NodeType.FIXED
    assert nodes[0].duration_min == 120
    assert nodes[0].fixed_start_time == "15:30"
    assert nodes[0].official_domain == "ticketing.colosseo.it"

    assert nodes[1].title == "Trastevere Pasta"
    assert nodes[1].type == NodeType.FLEXIBLE
    assert nodes[1].duration_min == 60


def test_expenses_csv_roundtrip():
    original_expenses = [
        Expense(
            id="e1",
            title="Rental Car",
            payer="Franek",
            amount=160.0,
            currency="EUR",
            participants=["Franek", "Anna"],
        ),
        Expense(
            id="e2",
            title="Airport Parking",
            payer="Kasia",
            amount=258.0,
            currency="PLN",
            exchange_rate_to_base=4.30,
            participants=["Franek", "Anna", "Marek", "Kasia"],
        ),
    ]

    csv_data = export_expenses_to_csv(original_expenses)
    parsed_expenses = parse_expenses_csv(csv_data)
    assert len(parsed_expenses) == 2
    assert parsed_expenses[0].title == "Rental Car"
    assert parsed_expenses[0].payer == "Franek"
    assert parsed_expenses[0].amount == 160.0
    assert parsed_expenses[0].participants == ["Franek", "Anna"]

    assert parsed_expenses[1].title == "Airport Parking"
    assert parsed_expenses[1].payer == "Kasia"
    assert parsed_expenses[1].currency == "PLN"
    assert parsed_expenses[1].exchange_rate_to_base == 4.30
    assert parsed_expenses[1].participants == ["Franek", "Anna", "Marek", "Kasia"]


def test_settlement_csv_export():
    expenses = [
        Expense(
            id="e1",
            title="Dinner",
            payer="Franek",
            amount=100.0,
            currency="EUR",
            participants=["Franek", "Anna"],
        ),
    ]
    settlement = settle_expenses(expenses, base_currency="EUR", all_travelers=["Franek", "Anna"])
    csv_data = export_settlement_to_csv(settlement)

    assert "From (Debtor)" in csv_data
    assert "Anna" in csv_data
    assert "Franek" in csv_data
    assert "50.00" in csv_data
