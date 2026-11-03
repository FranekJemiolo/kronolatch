"""
Google Spreadsheets and CSV / XLS Import & Export Engine for KronoLatch.
Converts Google Sheets URLs into CSV export streams, parses flexible spreadsheet headers,
and generates standardized CSV exports for itineraries and multi-currency expense ledgers.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

from kronolatch.models import (
    Category,
    Expense,
    LedgerSettlementResult,
    NodeType,
    TransitMode,
    TripNode,
    minutes_to_time_str,
)


def google_sheets_url_to_csv_export_url(url: str) -> str:
    """
    Transforms any standard Google Sheets sharing URL into its direct CSV export endpoint.
    Examples:
      - https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?usp=sharing
      -> https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=csv
      - Supports sheet/tab specific gid parameter (e.g. gid=123456789)
    """
    cleaned = url.strip()
    if "docs.google.com/spreadsheets" not in cleaned:
        return cleaned

    # Match the spreadsheet document ID
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", cleaned)
    if not match:
        return cleaned

    sheet_id = match.group(1)

    # Extract gid (specific worksheet/tab) if present
    parsed = urlparse(cleaned)
    params = parse_qs(parsed.query)
    gid = None
    if "gid" in params:
        gid = params["gid"][0]
    elif parsed.fragment and "gid=" in parsed.fragment:
        frag_match = re.search(r"gid=(\d+)", parsed.fragment)
        if frag_match:
            gid = frag_match.group(1)

    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid:
        export_url += f"&gid={gid}"
    return export_url


def _normalize_header(header: str) -> str:
    """Normalizes header string for robust matching (e.g. 'Event Title' -> 'title')."""
    return re.sub(r"[^a-z0-9]", "", header.lower().strip())


def parse_itinerary_csv(csv_content: str) -> List[TripNode]:
    """
    Parses CSV text into a list of validated TripNode objects.
    Flexible header recognition handles common variations like 'Stop', 'Activity', 'Start Time', 'Duration (mins)'.
    """
    if not csv_content.strip():
        return []

    # Detect delimiter (comma, semicolon, tab)
    sample = csv_content[:1024]
    delimiter = ","
    if ";" in sample and sample.count(";") > sample.count(","):
        delimiter = ";"
    elif "\t" in sample and sample.count("\t") > sample.count(","):
        delimiter = "\t"

    reader = csv.reader(io.StringIO(csv_content), delimiter=delimiter)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return []

    headers = [_normalize_header(h) for h in rows[0]]
    header_map: Dict[str, int] = {h: idx for idx, h in enumerate(headers) if h}

    def get_val(row: List[str], *aliases: str) -> str:
        for alias in aliases:
            norm = _normalize_header(alias)
            if norm in header_map and header_map[norm] < len(row):
                val = row[header_map[norm]].strip()
                if val:
                    return val
            for h, col_idx in header_map.items():
                if norm == h or norm in h or h in norm:
                    if col_idx < len(row):
                        val = row[col_idx].strip()
                        if val:
                            return val
        return ""

    nodes: List[TripNode] = []
    for idx, row in enumerate(rows[1:], start=1):
        if not any(cell.strip() for cell in row):
            continue

        title = get_val(row, "title", "name", "event", "stop", "activity", "item")
        if not title:
            title = f"Stop {idx}"

        raw_type = get_val(row, "type", "nodetype", "kind", "fixedflexible").lower()
        is_fixed = any(k in raw_type for k in ["fix", "lock", "strict", "hard"])
        node_type = NodeType.FIXED if is_fixed else NodeType.FLEXIBLE

        raw_cat = get_val(row, "category", "cat", "class").lower()
        category = Category.SIGHTSEEING
        if any(k in raw_cat for k in ["flight", "plane", "airport"]):
            category = Category.FLIGHT
        elif any(k in raw_cat for k in ["train", "rail", "metro", "subway"]):
            category = Category.RAIL
        elif any(k in raw_cat for k in ["bus", "coach", "shuttle"]):
            category = Category.BUS
        elif any(k in raw_cat for k in ["car", "drive", "road", "rental"]):
            category = Category.CAR
        elif any(
            k in raw_cat for k in ["food", "lunch", "dinner", "breakfast", "cafe", "restaurant"]
        ):
            category = Category.FOOD
        elif any(k in raw_cat for k in ["hotel", "lodging", "airbnb", "stay"]):
            category = Category.LODGING

        raw_mode = get_val(row, "transitmode", "mode", "transport").lower()
        transit_mode = TransitMode.WALK
        if "flight" in raw_mode:
            transit_mode = TransitMode.FLIGHT
        elif "train" in raw_mode or "rail" in raw_mode:
            transit_mode = TransitMode.TRAIN
        elif "bus" in raw_mode:
            transit_mode = TransitMode.BUS
        elif "car" in raw_mode or "drive" in raw_mode:
            transit_mode = TransitMode.CAR
        elif "none" in raw_mode:
            transit_mode = TransitMode.NONE

        raw_dur = get_val(row, "durationmin", "duration", "dur", "lengthmin", "minutes", "length")
        try:
            duration_min = max(5, int(float(raw_dur))) if raw_dur else 45
        except ValueError:
            duration_min = 45

        raw_transit = get_val(row, "transitmin", "transit", "travelmin", "traveltime", "travel")
        try:
            transit_min = (
                max(0, int(float(raw_transit))) if raw_transit else (0 if idx == 1 else 15)
            )
        except ValueError:
            transit_min = 0 if idx == 1 else 15

        start_time = get_val(row, "fixedstarttime", "starttime", "time", "departure", "slot")
        fixed_time_clean = None
        if start_time:
            # Match HH:MM format
            m = re.search(r"(\d{1,2}):(\d{2})", start_time)
            if m:
                fixed_time_clean = f"{int(m.group(1)):02d}:{m.group(2)}"
                if not is_fixed and "flex" not in raw_type:
                    node_type = NodeType.FIXED

        raw_prio = get_val(row, "priority", "prio", "importance", "score")
        try:
            priority = max(1, min(10, int(float(raw_prio)))) if raw_prio else 5
        except ValueError:
            priority = 5

        domain = get_val(row, "officialdomain", "domain", "website", "url", "link")
        pnr = get_val(row, "pnr", "bookingcode", "ref", "ticket")
        notes = get_val(row, "notes", "note", "desc", "details", "comments")
        raw_id = get_val(row, "id", "nodeid", "key") or f"csv-{idx}"

        node = TripNode(
            id=raw_id,
            title=title,
            type=node_type,
            category=category,
            transit_mode=transit_mode,
            transit_min=transit_min,
            duration_min=duration_min,
            min_duration_min=max(10, int(duration_min * 0.4))
            if node_type == NodeType.FLEXIBLE
            else None,
            fixed_start_time=fixed_time_clean,
            priority=priority,
            official_domain=domain or None,
            pnr=pnr or None,
            notes=notes or None,
            active=True,
        )
        nodes.append(node)

    return nodes


def export_itinerary_to_csv(nodes: List[TripNode]) -> str:
    """Exports a list of TripNode objects into clean, standard CSV text for Google Sheets or Excel."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "ID",
            "Title",
            "Type",
            "Category",
            "Transit Mode",
            "Transit Min",
            "Duration Min",
            "Fixed Start Time",
            "Priority",
            "Official Domain",
            "PNR",
            "Notes",
        ]
    )
    for n in nodes:
        writer.writerow(
            [
                n.id,
                n.title,
                n.type.value,
                n.category.value,
                n.transit_mode.value,
                n.transit_min,
                n.duration_min,
                n.fixed_start_time
                or (minutes_to_time_str(n.fixed_start_min) if n.fixed_start_min else ""),
                n.priority,
                n.official_domain or "",
                n.pnr or "",
                n.notes or "",
            ]
        )
    return output.getvalue()


def parse_expenses_csv(csv_content: str, default_currency: str = "EUR") -> List[Expense]:
    """
    Parses CSV text into a list of Expense records.
    Flexible header recognition supports fields like 'Title', 'Payer', 'Amount', 'Currency', 'Participants'.
    """
    if not csv_content.strip():
        return []

    sample = csv_content[:1024]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","

    reader = csv.reader(io.StringIO(csv_content), delimiter=delimiter)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return []

    headers = [_normalize_header(h) for h in rows[0]]
    header_map = {h: idx for idx, h in enumerate(headers) if h}

    def get_val(row: List[str], *aliases: str) -> str:
        for alias in aliases:
            norm = _normalize_header(alias)
            if norm in header_map and header_map[norm] < len(row):
                val = row[header_map[norm]].strip()
                if val:
                    return val
            for h, col_idx in header_map.items():
                if norm == h or norm in h or h in norm:
                    if col_idx < len(row):
                        val = row[col_idx].strip()
                        if val:
                            return val
        return ""

    expenses: List[Expense] = []
    for idx, row in enumerate(rows[1:], start=1):
        if not any(cell.strip() for cell in row):
            continue

        title = get_val(row, "title", "item", "description", "expense", "name") or f"Expense {idx}"
        payer = get_val(row, "payer", "paidby", "who", "person") or "Traveler"
        raw_amt = get_val(row, "amount", "cost", "price", "val", "sum")
        try:
            # Strip currency symbols if present
            amt_clean = re.sub(r"[^\d.]", "", raw_amt.replace(",", "."))
            amount = float(amt_clean) if amt_clean else 10.0
        except ValueError:
            amount = 10.0

        currency = get_val(row, "currency", "curr", "curr_code") or default_currency
        currency = currency.upper().strip()

        raw_rate = get_val(row, "exchangerateto_base", "rate", "exchangerate", "fx")
        try:
            rate = (
                float(raw_rate.replace(",", "."))
                if raw_rate
                else (4.30 if currency == "PLN" else 1.0)
            )
        except ValueError:
            rate = 1.0

        raw_parts = get_val(
            row, "participants", "splitbetween", "who_split", "travelers", "for", "split"
        )
        if raw_parts:
            # Split by comma, semicolon, or slash
            parts = [p.strip() for p in re.split(r"[,;/]", raw_parts) if p.strip()]
        else:
            parts = [payer]

        raw_id = get_val(row, "id", "exp_id") or f"e-csv-{idx}"
        node_id = get_val(row, "nodeid", "stopid", "node") or None

        expenses.append(
            Expense(
                id=raw_id,
                title=title,
                payer=payer,
                amount=amount,
                currency=currency,
                exchange_rate_to_base=rate,
                participants=parts,
                node_id=node_id,
            )
        )
    return expenses


def export_expenses_to_csv(expenses: List[Expense]) -> str:
    """Exports Expense records into clean, standard CSV format."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "ID",
            "Title",
            "Payer",
            "Amount",
            "Currency",
            "Exchange Rate to Base",
            "Participants",
            "Linked Node ID",
        ]
    )
    for e in expenses:
        writer.writerow(
            [
                e.id,
                e.title,
                e.payer,
                f"{e.amount:.2f}",
                e.currency,
                f"{e.exchange_rate_to_base:.4f}",
                "; ".join(e.participants),
                e.node_id or "",
            ]
        )
    return output.getvalue()


def export_settlement_to_csv(result: LedgerSettlementResult) -> str:
    """Exports minimal debt settlement transfers to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "From (Debtor)",
            "To (Creditor)",
            "Amount",
            "Base Currency",
            "Amount Alternate",
            "Alternate Currency",
        ]
    )
    for t in result.transfers:
        writer.writerow(
            [
                t.from_person,
                t.to_person,
                f"{t.amount:.2f}",
                t.currency,
                f"{t.amount_alternate:.2f}" if t.amount_alternate else "",
                t.alternate_currency or "",
            ]
        )
    return output.getvalue()
