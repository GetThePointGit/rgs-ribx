import math

import pytest

from rgs_ribx.lost_capacity.profile import (
    MeasurementPoint,
    correct_profile_to_bobs,
    disc_segment,
)


def test_correct_profile_aligns_ends_to_bobs():
    # A straight measured line -2.0 -> -3.0 (too steep) corrected onto the true
    # BOBs -2.0 -> -2.3; the relative shape (here none) is preserved.
    pts = [
        MeasurementPoint(dist=0.0, bob=-2.0, obb=-1.7),
        MeasurementPoint(dist=15.0, bob=-2.5, obb=-2.2),
        MeasurementPoint(dist=30.0, bob=-3.0, obb=-2.7),
    ]
    correct_profile_to_bobs(pts, bob1=-2.0, bob2=-2.3, length=30.0)
    assert pts[0].bob == pytest.approx(-2.0)
    assert pts[-1].bob == pytest.approx(-2.3)
    assert pts[1].bob == pytest.approx(-2.15)
    assert pts[1].obb == pytest.approx(pts[1].bob + 0.3)


def test_correct_profile_preserves_sag():
    # A 0.1 m sag at the middle survives the de-trend (only drift is removed).
    pts = [
        MeasurementPoint(dist=0.0, bob=-2.0, obb=-1.7),
        MeasurementPoint(dist=15.0, bob=-2.6, obb=-2.3),
        MeasurementPoint(dist=30.0, bob=-3.0, obb=-2.7),
    ]
    correct_profile_to_bobs(pts, bob1=-2.0, bob2=-2.3, length=30.0)
    assert pts[1].bob == pytest.approx(-2.25)


def test_correct_profile_removes_linear_drift_on_all_points():
    # A purely linear drift below a flat ideal must be fully de-trended to the
    # ideal at EVERY point (regresses the bug where only the first point moved).
    pts = [
        MeasurementPoint(dist=0.0, bob=-2.5, obb=-2.2),
        MeasurementPoint(dist=15.0, bob=-2.6, obb=-2.3),
        MeasurementPoint(dist=30.0, bob=-2.7, obb=-2.4),
    ]
    correct_profile_to_bobs(pts, bob1=-2.0, bob2=-2.0, length=30.0)
    assert pts[0].bob == pytest.approx(-2.0)
    assert pts[1].bob == pytest.approx(-2.0)   # would be -2.25 with the bug
    assert pts[2].bob == pytest.approx(-2.0)


def test_correct_profile_noop_when_too_few_points():
    pts = [
        MeasurementPoint(dist=0.0, bob=-2.0, obb=-1.7),
        MeasurementPoint(dist=30.0, bob=-3.0, obb=-2.7),
    ]
    correct_profile_to_bobs(pts, bob1=-2.0, bob2=-2.3, length=30.0)
    assert pts[1].bob == -3.0  # unchanged


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
