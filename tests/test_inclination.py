import math

import pytest

from rgs_ribx.model.inclination import build_inclination_profile


def test_absolute_type_b():
    mrios = [
        {"distance": 0.0, "measurement": -2.0},
        {"distance": 10.0, "measurement": -2.5},
        {"distance": 20.0, "measurement": -2.2},
    ]
    pts = build_inclination_profile(
        mrios, horizontal_distance=20.0, bob1=-2.0, bob2=-2.2,
        measurement_type="B", diameter=0.3,
    )
    assert [round(p.dist, 1) for p in pts] == [0.0, 10.0, 20.0]
    assert [round(p.bob, 2) for p in pts] == [-2.0, -2.5, -2.2]
    assert pts[1].obb == pytest.approx(pts[1].bob + 0.3)


def test_slope_degrees_type_j():
    mrios = [
        {"distance": 0.0, "measurement": 0.0},
        {"distance": 10.0, "measurement": -5.0},  # -5 degrees over 10 m
    ]
    pts = build_inclination_profile(
        mrios, horizontal_distance=10.0, bob1=-2.0, bob2=-2.0,
        measurement_type="J", diameter=0.3,
    )
    assert pts[0].bob == pytest.approx(-2.0)
    assert pts[-1].bob == pytest.approx(-2.0 + 10 * math.tan(math.radians(-5)))


def test_reverse_flips_distance():
    mrios = [
        {"distance": 0.0, "measurement": -2.0},
        {"distance": 20.0, "measurement": -2.4},
    ]
    pts = build_inclination_profile(
        mrios, horizontal_distance=20.0, bob1=-2.0, bob2=-2.4,
        measurement_type="B", diameter=0.3, reverse=True,
    )
    # Reversed: distances mirrored and order flipped.
    assert [round(p.dist, 1) for p in pts] == [0.0, 20.0]
    assert [round(p.bob, 2) for p in pts] == [-2.4, -2.0]


def test_empty_or_missing_bobs():
    assert build_inclination_profile([], 20.0, -2.0, -2.4, "B", 0.3) == []
    mrios = [{"distance": 0.0, "measurement": -2.0}]
    assert build_inclination_profile(mrios, 20.0, None, -2.4, "B", 0.3) == []
