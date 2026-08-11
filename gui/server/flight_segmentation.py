"""
Groups an ordered list of position_history rows into "flights" — runs
of consecutive points that plausibly belong to the same physical
flight — so trails can be colored per-flight instead of drawing one
undifferentiated line across everything ever recorded for a hex.

Squawk is deliberately NOT used as a boundary signal: ATC reassigns
squawk codes mid-flight routinely, so a squawk change alone doesn't
mean a new flight — see the DB-structure discussion earlier in this
conversation.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class PositionRow(Protocol):
    """Documents the shape `rows` needs (ORM rows or any duck-typed
    equivalent, e.g. plain namedtuples in tests). Not used as the actual
    parameter type below — SQLAlchemy's `Mapped[T]` column wrapper
    doesn't structurally satisfy a plain `T` under static checking, even
    though real instances behave exactly like this at runtime."""

    latitude: float | None
    longitude: float | None
    altitude_baro: float | None
    callsign: str | None
    recorded_at: dt.datetime


@dataclass
class SegmentedPoint:
    latitude: float | None
    longitude: float | None
    altitude_baro: float | None
    callsign: str | None
    recorded_at: dt.datetime
    flight_id: int


def segment_flights(rows: Sequence[Any], gap_minutes: float) -> list[SegmentedPoint]:
    """`rows` must already be ordered by recorded_at ascending, and
    each element must match the PositionRow shape above (checked only
    by duck typing at runtime, not statically — see that class's
    docstring for why).
    """
    segmented: list[SegmentedPoint] = []
    flight_id = 1
    prev_callsign: str | None = None
    prev_time: dt.datetime | None = None
    # True once the CURRENT flight has positively reported ground since
    # it started (or since the last new-flight boundary). Reset to
    # False every time a new flight begins.
    landed_since_flight_start = False

    for row in rows:
        callsign = (row.callsign or "").strip() or None
        altitude = row.altitude_baro
        is_ground = altitude is not None and altitude == 0
        # Require *positive* confirmation of a nonzero altitude to count
        # as airborne - a missing/unknown altitude (None) is neither
        # "still on the ground" nor "confirmed flying again", so it
        # shouldn't itself end a grounded period.
        is_airborne = altitude is not None and altitude != 0
        is_new_flight = False

        if prev_time is not None:
            if landed_since_flight_start:
                # Already know this flight landed. From here, the ONLY
                # thing that starts a new flight is taking off again -
                # not a data gap or callsign change while still on the
                # ground, since neither of those means it flew anywhere.
                if is_airborne:
                    is_new_flight = True
            else:
                # No confirmed landing yet for this flight - fall back
                # to the old heuristics, the best available signal when
                # there's no ground reading to anchor on.
                gap = (row.recorded_at - prev_time).total_seconds() / 60
                if (
                    gap > gap_minutes
                    or callsign
                    and prev_callsign
                    and callsign != prev_callsign
                ):
                    is_new_flight = True

        if is_new_flight:
            flight_id += 1
            landed_since_flight_start = False

        if is_ground:
            landed_since_flight_start = True

        segmented.append(
            SegmentedPoint(
                latitude=row.latitude,
                longitude=row.longitude,
                altitude_baro=row.altitude_baro,
                callsign=callsign,
                recorded_at=row.recorded_at,
                flight_id=flight_id,
            )
        )

        prev_time = row.recorded_at
        # Carry the last-known callsign forward through gaps where it's
        # missing, so a brief dropout doesn't look like a callsign
        # change once data resumes.
        prev_callsign = callsign or prev_callsign

    return segmented


def latest_flight_only(segmented: list[SegmentedPoint]) -> list[SegmentedPoint]:
    if not segmented:
        return []
    last_id = segmented[-1].flight_id
    return [p for p in segmented if p.flight_id == last_id]
