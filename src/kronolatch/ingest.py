"""
Ticket & Document Ingestion Engine for KronoLatch.
Deterministic extraction of PNRs, train/flight details, seat assignments,
and timestamps from PDF tickets and text confirmations without cloud reliance.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field

from kronolatch.models import (
    Category,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
    time_str_to_minutes,
)


class ParsedTicket(BaseModel):
    """Normalized structured entity extracted from raw ticket text or PDF."""

    pnr: Optional[str] = Field(default=None, description="Booking reference code / PNR")
    service_type: Category = Field(default=Category.RAIL, description="Category of service")
    transit_mode: TransitMode = Field(default=TransitMode.TRAIN, description="Transit mode")
    service_number: Optional[str] = Field(
        default=None, description="Flight or Train number (e.g. FR 9540, AZ 204)"
    )
    origin: str = Field(default="Origin Station", description="Departure location")
    destination: str = Field(default="Destination Station", description="Arrival location")
    departure_time: str = Field(default="10:00", description="Departure time in HH:MM format")
    arrival_time: str = Field(default="11:30", description="Arrival time in HH:MM format")
    date: Optional[str] = Field(default=None, description="Travel date YYYY-MM-DD or DD/MM/YYYY")
    coach_carriage: Optional[str] = Field(default=None, description="Coach/Carriage number")
    seat: Optional[str] = Field(default=None, description="Seat number or assignment")
    price: Optional[float] = Field(default=None, description="Total ticket price")
    currency: str = Field(default="EUR", description="Currency of the ticket")
    raw_snippet: Optional[str] = Field(default=None, description="Snippet of original text")

    def duration_minutes(self) -> int:
        """Calculate transit duration in minutes, handling midnight wrapping."""
        dep_m = time_str_to_minutes(self.departure_time)
        arr_m = time_str_to_minutes(self.arrival_time)
        diff = arr_m - dep_m
        if diff <= 0:
            diff += 1440
        return diff

    def to_trip_node(self, node_id: str) -> TripNode:
        """Convert parsed ticket into a deterministic FIXED TripNode."""
        dur = self.duration_minutes()
        dep_m = time_str_to_minutes(self.departure_time)

        label_parts = []
        if self.service_number:
            label_parts.append(self.service_number)
        label_parts.append(f"{self.origin} -> {self.destination}")
        title = f"{'Flight' if self.service_type == Category.FLIGHT else 'Train'} {' '.join(label_parts)}"

        notes_parts = []
        if self.pnr:
            notes_parts.append(f"PNR: {self.pnr}")
        if self.coach_carriage:
            notes_parts.append(f"Coach: {self.coach_carriage}")
        if self.seat:
            notes_parts.append(f"Seat: {self.seat}")
        if self.date:
            notes_parts.append(f"Date: {self.date}")

        return TripNode(
            id=node_id,
            title=title,
            type=NodeType.FIXED,
            category=self.service_type,
            transit_mode=self.transit_mode,
            transit_min=dur,
            duration_min=dur,
            min_duration_min=dur,
            ideal_duration_min=dur,
            fixed_start_min=dep_m,
            fixed_start_time=self.departure_time,
            priority=10,  # Max priority for fixed reservations
            pnr=self.pnr,
            notes=" | ".join(notes_parts) if notes_parts else None,
            active=True,
        )


class TicketIngestor:
    """Deterministic extractor for travel tickets and confirmations."""

    # Regex patterns for booking references (PNR)
    PNR_PATTERNS = [
        re.compile(
            r"(?:PNR|Booking\s*(?:Ref|Reference|Code)|Codice\s*Prenotazione|Numer\s*rezerwacji)[\s:]*([A-Z0-9]{5,8})",
            re.IGNORECASE,
        ),
        re.compile(r"\b([A-Z0-9]{6})\b"),  # General 6-character IATA/rail PNR
    ]

    # Rail operator and train number patterns
    RAIL_PATTERNS = [
        re.compile(
            r"\b(Frecciarossa|Frecciargento|Frecciabianca|Intercity|Regionale|Italo|Eurostar|EIP|TLK|TGV|ICE)\s*([0-9]{2,5})\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(FR|FA|FB|IC|EC|REG)\s*([0-9]{2,5})\b", re.IGNORECASE),
        re.compile(r"\b(Leonardo\s*Express)\b", re.IGNORECASE),
        re.compile(r"(?:Train|Treno|Pociąg|Zug)[\s#:]*([A-Z0-9\s-]{2,10})", re.IGNORECASE),
    ]

    # Airline and flight number patterns
    FLIGHT_PATTERNS = [
        re.compile(
            r"\b(Flight|Volo|Lot|Flug)[\s#:]*([A-Z0-9]{2}\s*[0-9]{2,4})\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b([A-Z]{2}|[A-Z][0-9]|[0-9][A-Z])\s*([0-9]{3,4})\b"),  # IATA flight codes
    ]

    # Time patterns: HH:MM
    TIME_PATTERN = re.compile(r"\b([01]?[0-9]|2[0-3]):([0-5][0-9])\b")

    # Date patterns: YYYY-MM-DD or DD/MM/YYYY or DD.MM.YYYY
    DATE_PATTERNS = [
        re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
        re.compile(r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b"),
    ]

    # Carriage and Seat patterns
    COACH_PATTERNS = [
        re.compile(r"(?:Carriage|Coach|Carrozza|Wagon|Wag[\.:])[\s:]*([0-9]{1,3})", re.IGNORECASE),
    ]
    SEAT_PATTERNS = [
        re.compile(r"(?:Seat|Posto|Miejsce|Sitzplatz)[\s:]*([0-9]{1,3}[A-Z]?)", re.IGNORECASE),
    ]

    # Price patterns
    PRICE_PATTERNS = [
        re.compile(r"([€$£]|PLN|EUR|USD)\s*([0-9]+[.,][0-9]{2})", re.IGNORECASE),
        re.compile(r"([0-9]+[.,][0-9]{2})\s*([€$£]|PLN|EUR|USD)", re.IGNORECASE),
    ]

    @classmethod
    def extract_text_from_pdf(cls, pdf_path: Union[str, Path]) -> str:
        """Extract text from a PDF document using pypdf."""
        import pypdf

        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(f"PDF ticket not found at: {path}")

        reader = pypdf.PdfReader(str(path))
        text_parts = []
        for i, page in enumerate(reader.pages):
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
        return "\n".join(text_parts)

    @classmethod
    def parse(cls, input_source: Union[str, Path]) -> ParsedTicket:
        """
        Parse a ticket from either a PDF file path or raw text string.
        Extracts PNR, service type, route, timing, seat, and pricing deterministically.
        """
        # Determine if input is a PDF file path
        raw_text = ""
        try:
            path = Path(str(input_source))
            if path.is_file() and path.suffix.lower() == ".pdf":
                raw_text = cls.extract_text_from_pdf(path)
            elif path.is_file():
                raw_text = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            pass

        if not raw_text:
            raw_text = str(input_source)

        return cls.parse_text(raw_text)

    @classmethod
    def parse_text(cls, text: str) -> ParsedTicket:
        """Extract structured entities from normalized ticket text."""
        cleaned = text.strip()

        # 1. Detect Category / Service Type
        flight_match = any(
            p.search(cleaned)
            for p in [re.compile(r"\b(flight|airline|boarding|airport|volo|lot)\b", re.IGNORECASE)]
        )
        is_flight = bool(flight_match)
        service_type = Category.FLIGHT if is_flight else Category.RAIL
        transit_mode = TransitMode.FLIGHT if is_flight else TransitMode.TRAIN

        # 2. Extract Service Number (Train or Flight)
        service_number: Optional[str] = None
        if is_flight:
            for pat in cls.FLIGHT_PATTERNS:
                m = pat.search(cleaned)
                if m:
                    service_number = m.group(0).strip()
                    break
        else:
            for pat in cls.RAIL_PATTERNS:
                m = pat.search(cleaned)
                if m:
                    service_number = m.group(0).strip()
                    break

        # 3. Extract PNR
        pnr: Optional[str] = None
        for pat in cls.PNR_PATTERNS:
            m = pat.search(cleaned)
            if m:
                pnr = m.group(1).strip().upper()
                break

        # 4. Extract Times (Expect at least 2 distinct times for departure and arrival)
        all_times = cls.TIME_PATTERN.findall(cleaned)
        dep_time = "10:00"
        arr_time = "11:30"
        if len(all_times) >= 2:
            dep_time = f"{int(all_times[0][0]):02d}:{all_times[0][1]}"
            arr_time = f"{int(all_times[1][0]):02d}:{all_times[1][1]}"
        elif len(all_times) == 1:
            dep_time = f"{int(all_times[0][0]):02d}:{all_times[0][1]}"
            dep_m = time_str_to_minutes(dep_time)
            # Default to 90 min duration
            arr_time = f"{((dep_m + 90) // 60) % 24:02d}:{(dep_m + 90) % 60:02d}"

        # 5. Extract Origin & Destination Stations / Cities
        origin = "Roma Termini" if not is_flight else "Rome FCO"
        destination = "Firenze S.M. Novella" if not is_flight else "Paris CDG"

        # Line-by-line check first (e.g. "From: ...", "To: ...", "Da: ...", "A: ...")
        for line in cleaned.splitlines():
            l_str = line.strip()
            from_m = re.match(
                r"^(?:From|Da|Od|Z|Origin|Origine)[\s:]+(.+)$",
                l_str,
                re.IGNORECASE,
            )
            if from_m:
                val = from_m.group(1).strip()
                # If "To: ..." is on the same line
                if re.search(r"\b(?:To|A|Do)\b", val, re.IGNORECASE):
                    subparts = re.split(r"\b(?:To|A|Do)\b[\s:]*", val, flags=re.IGNORECASE)
                    if len(subparts) >= 2:
                        origin = subparts[0].strip()
                        destination = subparts[1].strip()
                else:
                    origin = val

            to_m = re.match(
                r"^(?:To|A|Do|Destination|Destinazione)[\s:]+(.+)$",
                l_str,
                re.IGNORECASE,
            )
            if to_m:
                destination = to_m.group(1).strip()

        # Alternative route check: "Station A -> Station B" or "Station A - Station B"
        if " -> " in cleaned:
            parts = cleaned.split(" -> ")
            candidate_orig = parts[0].splitlines()[-1].strip()
            candidate_dest = parts[1].splitlines()[0].strip()
            if candidate_orig and candidate_dest:
                origin = candidate_orig
                destination = candidate_dest

        # 6. Extract Coach and Seat
        coach: Optional[str] = None
        for pat in cls.COACH_PATTERNS:
            m = pat.search(cleaned)
            if m:
                coach = m.group(1).strip()
                break

        seat: Optional[str] = None
        for pat in cls.SEAT_PATTERNS:
            m = pat.search(cleaned)
            if m:
                seat = m.group(1).strip().upper()
                break

        # 7. Extract Date
        date_str: Optional[str] = None
        for pat in cls.DATE_PATTERNS:
            m = pat.search(cleaned)
            if m:
                date_str = m.group(1).strip()
                break

        # 8. Extract Price
        price: Optional[float] = None
        curr = "EUR"
        for pat in cls.PRICE_PATTERNS:
            m = pat.search(cleaned)
            if m:
                g1, g2 = m.group(1), m.group(2)
                # Determine which group is price and which is currency
                if re.match(r"[0-9]+[.,][0-9]{2}", g1):
                    raw_val, raw_curr = g1, g2
                else:
                    raw_curr, raw_val = g1, g2

                try:
                    price = float(raw_val.replace(",", "."))
                    if "PLN" in raw_curr.upper():
                        curr = "PLN"
                    elif "$" in raw_curr or "USD" in raw_curr.upper():
                        curr = "USD"
                    elif "£" in raw_curr or "GBP" in raw_curr.upper():
                        curr = "GBP"
                    else:
                        curr = "EUR"
                    break
                except ValueError:
                    pass

        return ParsedTicket(
            pnr=pnr,
            service_type=service_type,
            transit_mode=transit_mode,
            service_number=service_number,
            origin=origin,
            destination=destination,
            departure_time=dep_time,
            arrival_time=arr_time,
            date=date_str,
            coach_carriage=coach,
            seat=seat,
            price=price,
            currency=curr,
            raw_snippet=cleaned[:300],
        )

    @classmethod
    def ingest_into_trip(
        cls,
        input_source: Union[str, Path],
        trip: TripDAG,
        node_id: Optional[str] = None,
    ) -> TripDAG:
        """
        Parse ticket and append as a locked FIXED TripNode in the trip itinerary.
        Sorts the nodes chronologically by start time.
        """
        parsed = cls.parse(input_source)
        if not node_id:
            node_id = f"node_{len(trip.nodes) + 1}_{parsed.service_type.value}"

        new_node = parsed.to_trip_node(node_id)

        # Append or replace node with same id
        updated_nodes = [n for n in trip.nodes if n.id != node_id]
        updated_nodes.append(new_node)

        # Sort nodes by effective start minutes
        updated_nodes.sort(key=lambda n: n.get_effective_fixed_start_min() or 0)

        return TripDAG(
            trip_id=trip.trip_id,
            title=trip.title,
            destination=trip.destination,
            base_currency=trip.base_currency,
            travelers=trip.travelers,
            parameters=trip.parameters,
            nodes=updated_nodes,
            expenses=trip.expenses,
            vendor_checks=trip.vendor_checks,
        )
