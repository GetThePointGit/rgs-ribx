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
