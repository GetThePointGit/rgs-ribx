"""Integrate raw measurements into a height profile per pipe (re-runnable).

Uses the pipe's current BOBs (so edited BOBs are honoured) and, optionally,
de-trends the profile onto those BOBs (sawtooth correction).
"""

from __future__ import annotations

from rgs_ribx.lost_capacity.profile import correct_profile_to_bobs
from rgs_ribx.model.inclination import build_inclination_profile


def integrate_profiles(pipes_by_code, raw_by_code, correct_bob=True):
    """Return ``{pipe_code: [MeasurementPoint]}`` for pipes that have raw points.

    Parameters
    ----------
    pipes_by_code : dict[str, Pipe]
        Pipes keyed by code; BOBs/length/diameter drive the integration.
    raw_by_code : dict[str, RawMeasurements]
        Raw (un-integrated) measurements keyed by pipe code. Each point is a
        ``{"dist": float, "value": float}`` mapping.
    correct_bob : bool
        Apply BOB de-trending after integration.

    Returns
    -------
    dict[str, list]
        Pipes lacking BOBs, a known pipe, or any raw points are skipped.
    """
    profiles = {}
    for code, raw in raw_by_code.items():
        pipe = pipes_by_code.get(code)
        if pipe is None or pipe.bob1 is None or pipe.bob2 is None:
            continue
        if not raw.points:
            continue
        # ``build_inclination_profile`` consumes ``distance``/``measurement``;
        # raw points use ``dist``/``value`` -> translate the keys here.
        mrios = [{"distance": p["dist"], "measurement": p["value"]} for p in raw.points]
        # Survey ran from manhole2 when reversed -> integrate from bob2.
        start_bob, end_bob = (pipe.bob2, pipe.bob1) if raw.reverse else (pipe.bob1, pipe.bob2)
        points = build_inclination_profile(
            mrios,
            horizontal_distance=pipe.length or 0.0,
            bob1=start_bob,
            bob2=end_bob,
            measurement_type=raw.measurement_type,
            diameter=pipe.diameter or 0.0,
            reverse=raw.reverse,
        )
        if not points:
            continue
        if correct_bob:
            correct_profile_to_bobs(points, pipe.bob1, pipe.bob2, pipe.length)
        profiles[code] = points
    return profiles
