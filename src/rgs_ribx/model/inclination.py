"""Build a longitudinal BOB profile from RIBX inclination measurements (BXA).

Port of lizard-progress ``set_geoms_dists``: integrate the BXA measurements
(distance ``I``, value ``D``, type from characteristic ``B``) into an invert
(bob) per point. Supported measurement types match the old tool:

- ``J`` slope in degrees, ``K`` slope in percent (integrated from ``bob1``)
- ``A`` mm / ``AA`` m relative to the ideal ``bob1`` → ``bob2`` line
- ``B`` absolute m NAP
"""

from __future__ import annotations

import math

from rgs_ribx.lost_capacity.profile import MeasurementPoint


def build_inclination_profile(
    mrios,
    horizontal_distance,
    bob1,
    bob2,
    measurement_type,
    diameter,
    reverse=False,
):
    """Return a list of MeasurementPoint built from inclination measurements.

    Parameters
    ----------
    mrios : list of dict
        Each ``{"distance": float, "measurement": float}`` (BXA I and D).
    horizontal_distance : float
        Straight distance between the two manholes (geometry length).
    bob1, bob2 : float
        Invert levels at the pipe ends (m NAP).
    measurement_type : str
        ``J`` / ``K`` / ``A`` / ``AA`` / ``B`` (from BXA characteristic ``B``).
    diameter : float
        Pipe diameter in metres (``obb = bob + diameter``).
    reverse : bool
        True when the inspection ran from manhole2 to manhole1.
    """
    if not mrios or bob1 is None or bob2 is None:
        return []

    # Sort by distance and drop duplicate distances (keep first).
    ordered = []
    last = None
    for m in sorted(mrios, key=lambda m: m["distance"]):
        if m["distance"] == last:
            continue
        last = m["distance"]
        ordered.append(dict(m))
    mrios = ordered

    vertical_distance = abs(bob1 - bob2)
    straight_length = math.sqrt(vertical_distance ** 2 + horizontal_distance ** 2)
    first_distance = mrios[0]["distance"]
    # Drop measurements more than 20% beyond the straight length (noise tail).
    bound = straight_length * 1.2 + first_distance
    mrios = [m for m in mrios if m["distance"] <= bound]
    if not mrios:
        return []
    last_distance = mrios[-1]["distance"]
    measurement_length = last_distance - first_distance
    length = straight_length if straight_length > measurement_length else measurement_length

    prev_bob = bob1
    prev_real_distance = first_distance
    x = 0.0
    factor = 1.0 if length == 0 else horizontal_distance / length
    if (last_distance - first_distance) > straight_length and (last_distance - first_distance) != 0:
        factor = horizontal_distance / (last_distance - first_distance)
        x = -first_distance
    elif first_distance < 0:
        x = -first_distance
    elif last_distance > length:
        x = length - last_distance

    deg_to_rad = math.pi / 180.0
    for m in mrios:
        m["dist"] = (m["distance"] + x) * factor
        pct = m["dist"] / horizontal_distance if horizontal_distance else 0.0
        value = m["measurement"]
        if measurement_type == "J":
            m["bob"] = prev_bob + (m["distance"] - prev_real_distance) * math.tan(value * deg_to_rad)
        elif measurement_type == "K":
            m["bob"] = prev_bob + (m["distance"] - prev_real_distance) * value / 100.0
        elif measurement_type == "A":
            m["bob"] = bob1 + (bob2 - bob1) * pct + value / 1000.0
        elif measurement_type == "AA":
            m["bob"] = bob1 + (bob2 - bob1) * pct + value
        elif measurement_type == "B":
            m["bob"] = value
        else:
            m["bob"] = bob1 + (bob2 - bob1) * pct
        prev_bob = m["bob"]
        prev_real_distance = m["distance"]

    if reverse:
        for m in mrios:
            m["dist"] = horizontal_distance - m["dist"]
        mrios = list(reversed(mrios))

    return [
        MeasurementPoint(dist=m["dist"], bob=m["bob"], obb=m["bob"] + diameter)
        for m in mrios
    ]
