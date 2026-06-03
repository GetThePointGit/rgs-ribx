"""Measurement points and flooded-area math.

Ported from lizard-progress src/sewer/models.py (PipeMeasurement.set_water_level,
compute_flooded_pct, disc_segment). Decoupled from Django: the circular/
rectangular choice is passed in as a flag instead of reading the Pipe model.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class MeasurementPoint:
    """A point along a pipe with an invert (bob) and crown (obb) level.

    ``obb`` (top of pipe) is normally ``bob + diameter``. ``water_level`` and
    ``flooded_pct`` are filled in by the lost-capacity algorithm.
    """

    dist: float
    bob: float
    obb: float
    virtual: bool = False
    water_level: Optional[float] = None
    flooded_pct: Optional[float] = None

    def set_water_level(self, water_level: Optional[float]) -> None:
        """Clamp the water level to lie within [bob, obb]."""
        if water_level is None:
            self.water_level = None
        else:
            self.water_level = max(self.bob, min(self.obb, water_level))

    def compute_flooded_pct(self, is_rectangular: bool) -> None:
        """Compute the fraction of the cross-section that is flooded."""
        if self.water_level is None:
            self.flooded_pct = None
            return

        depth = self.water_level - self.bob
        if depth <= 0.0:
            self.flooded_pct = 0
            return

        diameter = self.obb - self.bob
        if depth >= diameter:
            self.flooded_pct = 1
            return

        if is_rectangular:
            self.flooded_pct = depth / diameter
            return

        # Circular cross-section.
        area = math.pi * ((diameter / 2) ** 2)
        if depth == diameter / 2:
            percentage = 0.5
        elif depth < diameter / 2:
            percentage = disc_segment(radius=diameter / 2, height=depth) / area
        else:
            percentage = (area - disc_segment(radius=diameter / 2, height=diameter - depth)) / area
        self.flooded_pct = percentage


def disc_segment(radius: float, height: float) -> float:
    """Area of a circular segment of given height in a circle of given radius.

    Requires ``0 < height < radius``. See
    https://en.wikipedia.org/wiki/Circular_segment.
    """
    assert height < radius
    assert height != 0
    assert radius != 0

    radius = float(radius)
    height = float(height)

    angle = 2 * math.acos((radius - height) / radius)
    area = ((radius ** 2) / 2) * (angle - math.sin(angle))
    return area


def correct_profile_to_bobs(points, bob1, bob2, length) -> None:
    """De-trend a measured profile so its ends align with the pipe's known BOBs.

    Ported from lizard-progress ``correct_bob_values``: inclination (helling)
    measurements drift — they tend to end too deep, giving a sawtooth in the
    side-view. This rotates the line through the first/last measurement onto the
    ideal ``bob1`` → ``bob2`` line, preserving the relative sag shape. Modifies
    each point's ``bob`` and ``obb`` in place (the diameter is unchanged).

    No-op when there are fewer than 3 points, the length is missing/zero, or the
    measurements span no distance.
    """
    pts = sorted(points, key=lambda p: p.dist)
    if len(pts) < 3 or not length:
        return
    # Snapshot the apparent-line endpoints BEFORE the loop. Reading first.bob /
    # last.bob inside the loop would use values already mutated by this same
    # loop, collapsing every correction after the first point to ~zero.
    first_dist, first_bob = pts[0].dist, pts[0].bob
    last_dist, last_bob = pts[-1].dist, pts[-1].bob
    span = last_dist - first_dist
    if span == 0:
        return

    for point in pts:
        ideal = bob1 + (bob2 - bob1) * (point.dist / length)
        apparent = first_bob + (last_bob - first_bob) * ((point.dist - first_dist) / span)
        correction = ideal - apparent
        point.bob += correction
        point.obb += correction
