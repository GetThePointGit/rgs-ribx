import math

import pytest

from rgs_ribx.lost_capacity.profile import MeasurementPoint, disc_segment


def test_set_water_level_clamps_between_bob_and_obb():
    p = MeasurementPoint(dist=0.0, bob=-2.0, obb=-1.7)
    p.set_water_level(-5.0)
    assert p.water_level == -2.0  # clamped up to bob
    p.set_water_level(0.0)
    assert p.water_level == -1.7  # clamped down to obb
    p.set_water_level(None)
    assert p.water_level is None


def test_flooded_pct_dry_and_full():
    p = MeasurementPoint(dist=0.0, bob=-2.0, obb=-1.7)  # diameter 0.3
    p.set_water_level(-2.0)
    p.compute_flooded_pct(is_rectangular=False)
    assert p.flooded_pct == 0
    p.set_water_level(-1.7)
    p.compute_flooded_pct(is_rectangular=False)
    assert p.flooded_pct == 1


def test_flooded_pct_rectangular_half():
    p = MeasurementPoint(dist=0.0, bob=0.0, obb=1.0)
    p.set_water_level(0.5)
    p.compute_flooded_pct(is_rectangular=True)
    assert p.flooded_pct == pytest.approx(0.5)


def test_flooded_pct_circular_half_is_half():
    # Water exactly at centre of a circular pipe -> 50% area.
    p = MeasurementPoint(dist=0.0, bob=0.0, obb=1.0)  # diameter 1.0, radius 0.5
    p.set_water_level(0.5)
    p.compute_flooded_pct(is_rectangular=False)
    assert p.flooded_pct == pytest.approx(0.5)


def test_disc_segment_quarter_circle_known_value():
    # Segment height = radius/2 of unit-radius circle.
    area = disc_segment(radius=1.0, height=0.5)
    angle = 2 * math.acos(0.5)
    expected = 0.5 * (angle - math.sin(angle))
    assert area == pytest.approx(expected)
