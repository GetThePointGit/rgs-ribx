import pytest

from rgs_ribx.lost_capacity.compute import compute_lost_capacity
from rgs_ribx.lost_capacity.profile import MeasurementPoint
from rgs_ribx.model.entities import Manhole, Pipe


def _circular(bob, diameter=0.3):
    return MeasurementPoint(dist=0.0, bob=bob, obb=bob + diameter)


def test_single_pipe_with_dip_floods_the_dip():
    # Two manholes, one pipe sloping down then up: a dip in the middle holds water.
    manholes = {
        "P1": Manhole(code="P1", is_sink=True),
        "P2": Manhole(code="P2", is_sink=True),
    }
    pipes = {
        "L1": Pipe(code="L1", manhole1="P1", manhole2="P2",
                   bob1=-2.0, bob2=-2.0, diameter=0.3, shape="A"),
    }
    mid = MeasurementPoint(dist=15.0, bob=-2.3, obb=-2.0)
    profiles = {"L1": [mid]}

    compute_lost_capacity(manholes, pipes, profiles)

    assert mid.water_level == pytest.approx(-2.0)
    assert mid.flooded_pct is not None
    assert mid.flooded_pct > 0


def test_no_dip_means_no_flooding():
    manholes = {
        "P1": Manhole(code="P1", is_sink=False),
        "P2": Manhole(code="P2", is_sink=True),
    }
    pipes = {
        "L1": Pipe(code="L1", manhole1="P1", manhole2="P2",
                   bob1=-2.0, bob2=-2.6, diameter=0.3, shape="A"),
    }
    mid = MeasurementPoint(dist=15.0, bob=-2.3, obb=-2.0)
    profiles = {"L1": [mid]}

    compute_lost_capacity(manholes, pipes, profiles)

    assert mid.flooded_pct == 0
