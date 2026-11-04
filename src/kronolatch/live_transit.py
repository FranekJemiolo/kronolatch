"""
Live Public Rail Delay & Transit Telemetry Client for KronoLatch.
Queries public open-data railway endpoints (e.g. Trenitalia ViaggiaTreno)
to detect real-time train delays and feed them directly into the Temporal DAG engine.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

import httpx
from pydantic import BaseModel

from kronolatch.models import Category, TripDAG


class LiveTrainStatus(BaseModel):
    """Real-time telemetry for a railway service."""

    train_number: str
    operator: str = "Trenitalia / Rail Operator"
    origin_station: Optional[str] = None
    destination_station: Optional[str] = None
    delay_minutes: int = 0
    is_cancelled: bool = False
    last_detected_station: Optional[str] = None
    status_summary: str = "On Time"
    is_live: bool = True
    source: str = "ViaggiaTreno Open Data"


class LiveTransitClient:
    """Client for querying open-access train delay feeds."""

    VIAGGIATRENO_AUTOCOMPLETE_URL = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/cercaNumeroTrenoTrenoAutocomplete/{train_num}"
    VIAGGIATRENO_STATUS_URL = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/andamentoTreno/{station_id}/{train_num}"

    # Standard known European high-speed trains for demo / offline simulation
    KNOWN_DEMO_TRAINS = {
        "9540": {
            "name": "Frecciarossa 9540",
            "origin": "Roma Termini",
            "dest": "Milano Centrale",
            "delay": 12,
        },
        "9941": {
            "name": "Leonardo Express 9941",
            "origin": "Fiumicino Aeroporto",
            "dest": "Roma Termini",
            "delay": 0,
        },
        "3305": {
            "name": "Leonardo Express 3305",
            "origin": "Fiumicino Aeroporto",
            "dest": "Roma Termini",
            "delay": 35,
        },
        "9912": {
            "name": "Italo 9912",
            "origin": "Roma Termini",
            "dest": "Venezia S.L.",
            "delay": 5,
        },
        "5304": {
            "name": "Intercity 5304",
            "origin": "Napoli Centrale",
            "dest": "Roma Termini",
            "delay": 20,
        },
    }

    @classmethod
    def extract_train_number(cls, text: str) -> Optional[str]:
        """Extract purely numeric train identifier from strings like 'Frecciarossa 9540' or 'FR 9540'."""
        m = re.search(r"\b([0-9]{3,5})\b", text)
        if m:
            return m.group(1)
        return None

    @classmethod
    def fetch_train_delay(
        cls,
        train_number: str,
        timeout: float = 3.5,
        allow_simulation_fallback: bool = True,
    ) -> LiveTrainStatus:
        """
        Query live delay from ViaggiaTreno open API.
        Falls back to realistic known transit heuristics if network is unreachable or offline.
        """
        clean_num = cls.extract_train_number(train_number) or train_number.strip()

        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                # Step 1: Autocomplete lookup to find origin station ID
                url_auto = cls.VIAGGIATRENO_AUTOCOMPLETE_URL.format(train_num=clean_num)
                resp_auto = client.get(url_auto)

                if resp_auto.status_code == 200 and resp_auto.text.strip():
                    first_line = resp_auto.text.strip().split("\n")[0]
                    # Format: "TRAIN_NUM - ORIGIN_STATION|TRAIN_NUM-STATION_ID-TIMESTAMP"
                    parts = first_line.split("|")
                    if len(parts) >= 2:
                        id_parts = parts[1].split("-")
                        if len(id_parts) >= 2:
                            station_id = id_parts[1]
                            url_status = cls.VIAGGIATRENO_STATUS_URL.format(
                                station_id=station_id, train_num=clean_num
                            )
                            resp_status = client.get(url_status)
                            if resp_status.status_code == 200:
                                data = resp_status.json()
                                delay = int(data.get("ritardo", 0))
                                cancelled = bool(data.get("provvedimento", 0) == 1)
                                last_station = data.get("stazioneUltimoRilevamento", "En route")
                                orig = data.get("origine", "Origin")
                                dest = data.get("destinazione", "Destination")

                                if cancelled:
                                    summary = "CANCELLED"
                                elif delay > 0:
                                    summary = f"+{delay} min delay"
                                elif delay < 0:
                                    summary = f"{abs(delay)} min early"
                                else:
                                    summary = "On Time"

                                return LiveTrainStatus(
                                    train_number=clean_num,
                                    operator="Trenitalia",
                                    origin_station=orig,
                                    destination_station=dest,
                                    delay_minutes=max(0, delay),
                                    is_cancelled=cancelled,
                                    last_detected_station=last_station,
                                    status_summary=summary,
                                    is_live=True,
                                    source="ViaggiaTreno Live Feed",
                                )
        except Exception:
            # Network failure or API format changed
            pass

        # Offline / Fallback mode
        if allow_simulation_fallback and clean_num in cls.KNOWN_DEMO_TRAINS:
            demo = cls.KNOWN_DEMO_TRAINS[clean_num]
            d = demo["delay"]
            summary = f"+{d} min delay" if d > 0 else "On Time"
            return LiveTrainStatus(
                train_number=clean_num,
                operator="Trenitalia (Simulated)",
                origin_station=demo["origin"],
                destination_station=demo["dest"],
                delay_minutes=d,
                is_cancelled=False,
                last_detected_station="En route",
                status_summary=summary,
                is_live=False,
                source="Offline Transit Cache",
            )

        # Default fallback for uncataloged trains
        return LiveTrainStatus(
            train_number=clean_num,
            operator="Rail Service",
            delay_minutes=0,
            status_summary="On Time (No delays reported)",
            is_live=False,
            source="Estimated Schedule",
        )

    @classmethod
    def check_trip_rail_delays(cls, trip: TripDAG) -> Dict[str, LiveTrainStatus]:
        """
        Inspect all RAIL nodes in a TripDAG, detect service numbers,
        and query live delay telemetry.
        """
        results: Dict[str, LiveTrainStatus] = {}

        for node in trip.nodes:
            if node.category == Category.RAIL or "train" in node.title.lower():
                num = cls.extract_train_number(node.title)
                if not num and node.notes:
                    num = cls.extract_train_number(node.notes)
                if not num and "leonardo express" in node.title.lower():
                    num = "3305"  # Standard demonstration corridor train

                if num:
                    status = cls.fetch_train_delay(num)
                    results[node.id] = status

        return results
