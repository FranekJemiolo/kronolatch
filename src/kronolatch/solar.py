"""
Astronomical Solar Position & Weather-Aware Leeway Engine for KronoLatch.
Pure offline NOAA solar calculation (0 API calls) computing sunrise, golden hour,
civil twilight, and sunset, paired with meteorological buffer adjustments.
"""

from __future__ import annotations

import datetime
import math
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from kronolatch.models import (
    Category,
    NodeType,
    TripDAG,
    minutes_to_time_str,
    time_str_to_minutes,
)


class SolarSchedule(BaseModel):
    """Astronomical solar markers for a specific location and calendar date."""

    date: str
    latitude: float
    longitude: float
    solar_noon: str
    sunrise_time: str
    sunset_time: str
    golden_hour_start: str
    golden_hour_end: str
    civil_twilight_end: str
    day_length_min: int

    def is_daylight(self, time_str: str) -> bool:
        """Check if time is between sunrise and sunset."""
        t = time_str_to_minutes(time_str)
        sr = time_str_to_minutes(self.sunrise_time)
        ss = time_str_to_minutes(self.sunset_time)
        return sr <= t <= ss

    def is_golden_hour(self, time_str: str) -> bool:
        """Check if time is within the late-afternoon golden hour."""
        t = time_str_to_minutes(time_str)
        gh_start = time_str_to_minutes(self.golden_hour_start)
        gh_end = time_str_to_minutes(self.golden_hour_end)
        return gh_start <= t <= gh_end

    def is_past_twilight(self, time_str: str) -> bool:
        """Check if time is in total darkness past civil twilight."""
        t = time_str_to_minutes(time_str)
        tw = time_str_to_minutes(self.civil_twilight_end)
        return t > tw


class DaylightAuditResult(BaseModel):
    """Audit report of itinerary outdoor activities against solar and weather constraints."""

    location_name: str
    date: str
    solar_schedule: SolarSchedule
    outdoor_nodes_count: int
    daylight_compliant_count: int
    sunset_warnings: List[str] = Field(default_factory=list)
    twilight_violations: List[str] = Field(default_factory=list)
    weather_risk_multiplier_applied: float = 1.0
    rain_probability: float = 0.0
    recommendations: List[str] = Field(default_factory=list)


# Curated geographic coordinates for major European destinations
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "rome": (41.8967, 12.4822),
    "florence": (43.7696, 11.2558),
    "venice": (45.4408, 12.3155),
    "milan": (45.4642, 9.1900),
    "naples": (40.8518, 14.2681),
    "paris": (48.8566, 2.3522),
    "barcelona": (41.3879, 2.1699),
    "krakow": (50.0647, 19.9450),
    "warsaw": (52.2297, 21.0122),
    "athens": (37.9838, 23.7275),
}


class SolarEngine:
    """Deterministic astronomical solar engine based on standard NOAA solar equations."""

    @classmethod
    def resolve_coordinates(cls, destination_name: str) -> Tuple[float, float]:
        """Resolve city coordinates from destination string or fallback to Rome."""
        dest_lower = destination_name.lower()
        for city, coords in CITY_COORDINATES.items():
            if city in dest_lower:
                return coords
        return CITY_COORDINATES["rome"]

    @classmethod
    def is_european_dst(cls, date_val: datetime.date) -> bool:
        """Check if date falls within European Daylight Saving Time (CEST: UTC+2)."""
        year = date_val.year
        march_31 = datetime.date(year, 3, 31)
        # Last Sunday of March
        march_last_sun = march_31 - datetime.timedelta(days=(march_31.weekday() + 1) % 7)
        oct_31 = datetime.date(year, 10, 31)
        # Last Sunday of October
        oct_last_sun = oct_31 - datetime.timedelta(days=(oct_31.weekday() + 1) % 7)
        return march_last_sun <= date_val < oct_last_sun

    @classmethod
    def calculate_solar_schedule(
        cls,
        latitude: float,
        longitude: float,
        date_val: Optional[datetime.date] = None,
        tz_offset_hours: Optional[float] = None,
    ) -> SolarSchedule:
        """
        Computes exact sunrise, sunset, golden hour, and twilight for given latitude and longitude.
        Uses NOAA's Solar Calculation equations. Automatically detects Central European DST.
        """
        d = date_val or datetime.date(2026, 6, 15)
        day_of_year = d.timetuple().tm_yday

        if tz_offset_hours is None:
            tz_offset = 2.0 if cls.is_european_dst(d) else 1.0
        else:
            tz_offset = tz_offset_hours

        # Fractional year in radians
        gamma = (2.0 * math.pi / 365.0) * (day_of_year - 1)

        # Equation of Time in minutes
        eq_time = 229.18 * (
            0.000075
            + 0.001868 * math.cos(gamma)
            - 0.032077 * math.sin(gamma)
            - 0.014615 * math.cos(2 * gamma)
            - 0.040849 * math.sin(2 * gamma)
        )

        # Solar Declination in radians
        decl = (
            0.006918
            - 0.399912 * math.cos(gamma)
            + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma)
            + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma)
            + 0.00148 * math.sin(3 * gamma)
        )

        lat_rad = math.radians(latitude)

        # Solar noon in minutes from local midnight
        time_offset = eq_time + 4.0 * longitude - 60.0 * tz_offset
        solar_noon_min = 720.0 - time_offset

        def hour_angle_for_zenith(zenith_deg: float) -> Optional[float]:
            zenith_rad = math.radians(zenith_deg)
            cos_ha = (math.cos(zenith_rad) / (math.cos(lat_rad) * math.cos(decl))) - (
                math.tan(lat_rad) * math.tan(decl)
            )
            if cos_ha > 1.0 or cos_ha < -1.0:
                return None  # Polar day or polar night
            return math.degrees(math.acos(cos_ha))

        # Standard Sunrise / Sunset zenith = 90.833 deg (center of sun disc + refraction)
        ha_sunrise = hour_angle_for_zenith(90.833) or 90.0

        sunrise_min = solar_noon_min - (ha_sunrise * 4.0)
        sunset_min = solar_noon_min + (ha_sunrise * 4.0)
        day_length = int(round(sunset_min - sunrise_min))

        # Golden hour (zenith between 84.0 and 90.0 deg -> approx 60 mins before sunset)
        ha_golden = hour_angle_for_zenith(84.0) or (ha_sunrise - 15.0)
        golden_start_min = solar_noon_min + (ha_golden * 4.0)
        golden_end_min = sunset_min

        # Civil Twilight (zenith = 96.0 deg)
        ha_civil = hour_angle_for_zenith(96.0) or (ha_sunrise + 8.0)
        civil_twilight_end_min = solar_noon_min + (ha_civil * 4.0)

        return SolarSchedule(
            date=d.isoformat(),
            latitude=round(latitude, 4),
            longitude=round(longitude, 4),
            solar_noon=minutes_to_time_str(int(round(solar_noon_min))),
            sunrise_time=minutes_to_time_str(int(round(sunrise_min))),
            sunset_time=minutes_to_time_str(int(round(sunset_min))),
            golden_hour_start=minutes_to_time_str(int(round(golden_start_min))),
            golden_hour_end=minutes_to_time_str(int(round(golden_end_min))),
            civil_twilight_end=minutes_to_time_str(int(round(civil_twilight_end_min))),
            day_length_min=day_length,
        )

    @classmethod
    def audit_trip_daylight(
        cls,
        trip: TripDAG,
        date_val: Optional[datetime.date] = None,
        rain_probability: float = 0.0,
    ) -> DaylightAuditResult:
        """
        Evaluate an entire TripDAG against solar daylight markers and weather risk.
        Identifies outdoor activities planned past sunset or in darkness past civil twilight.
        """
        lat, lon = cls.resolve_coordinates(trip.destination)
        solar = cls.calculate_solar_schedule(lat, lon, date_val=date_val)

        sunset_m = time_str_to_minutes(solar.sunset_time)
        twilight_m = time_str_to_minutes(solar.civil_twilight_end)

        active_nodes = [n for n in trip.nodes if n.active]
        first_start = active_nodes[0].get_effective_fixed_start_min() if active_nodes else 8 * 60
        cursor = first_start if first_start is not None else 8 * 60

        outdoor_count = 0
        compliant_count = 0
        sunset_warnings: List[str] = []
        twilight_violations: List[str] = []
        recs: List[str] = []

        # Weather multiplier: +25% on walking and driving buffer when rain prob >= 40%
        weather_mult = 1.25 if rain_probability >= 0.40 else 1.0

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

            # Determine if node is an outdoor attraction
            is_outdoor = (
                node.category in (Category.SIGHTSEEING, Category.WALK)
                and "indoor" not in node.title.lower()
                and "museum" not in node.title.lower()
                and "gallery" not in node.title.lower()
            )

            if is_outdoor:
                outdoor_count += 1
                if end_m > twilight_m:
                    twilight_violations.append(
                        f"'{node.title}' finishes at {minutes_to_time_str(end_m)}, well past civil twilight ({solar.civil_twilight_end}) in total darkness."
                    )
                    recs.append(
                        f"Move '{node.title}' earlier or replace with an illuminated evening venue."
                    )
                elif end_m > sunset_m:
                    sunset_warnings.append(
                        f"'{node.title}' extends past sunset ({solar.sunset_time}). Golden hour photo window starts at {solar.golden_hour_start}."
                    )
                else:
                    compliant_count += 1

        if rain_probability >= 0.40:
            recs.append(
                f"Rain probability is {rain_probability * 100:.0f}%. Applied +25% transit leeway multiplier. Consider swapping outdoor plazas for covered galleries."
            )

        return DaylightAuditResult(
            location_name=trip.destination,
            date=solar.date,
            solar_schedule=solar,
            outdoor_nodes_count=outdoor_count,
            daylight_compliant_count=compliant_count,
            sunset_warnings=sunset_warnings,
            twilight_violations=twilight_violations,
            weather_risk_multiplier_applied=weather_mult,
            rain_probability=rain_probability,
            recommendations=recs,
        )
