import rgs_ribx
from rgs_ribx.lost_capacity.profile import MeasurementPoint
from rgs_ribx.model.segments import build_segments


def _pipe(code, bob1, bob2, length=30.0, diameter=0.3):
    return rgs_ribx.Pipe(code=code, manhole1="A", manhole2="B",
                         bob1=bob1, bob2=bob2, length=length, diameter=diameter, shape="A")


def test_measured_segments_merge_to_min_length():
    pipe = _pipe("L1", -2.0, -2.0, length=4.0)
    # 0.5 m spacing -> 8 short steps; min_length 1.0 -> ~4 segments.
    pts = [MeasurementPoint(dist=d / 2.0, bob=-2.0 - (0.1 if d == 3 else 0.0), obb=-1.7)
           for d in range(9)]
    segs = build_segments(pipe, pts, min_length=1.0)
    assert all(s["length"] >= 1.0 - 1e-9 or s is segs[-1] for s in segs)
    assert segs[0]["dist_from"] == 0.0
    assert round(segs[-1]["dist_to"], 1) == 4.0
    assert all(s["source"] == "measured" for s in segs)
    # carries required attributes
    s = segs[0]
    for key in ("pipe_code", "dist_from", "dist_to", "length", "bob_start",
                "bob_end", "bob_highest", "slope_avg", "diameter", "n_measurements", "source"):
        assert key in s


def test_bob_segments_for_pipe_without_measurements():
    pipe = _pipe("L1", -2.0, -2.6, length=12.0)
    segs = build_segments(pipe, [], bob_length=5.0)
    # 12 m / 5 m -> 3 segments (5, 5, 2)
    assert [round(s["length"], 1) for s in segs] == [5.0, 5.0, 2.0]
    assert all(s["source"] == "bob" for s in segs)
    # straight line: bob_start of first = bob1
    assert round(segs[0]["bob_start"], 2) == -2.0
    assert round(segs[-1]["bob_end"], 2) == -2.6


def test_no_segments_without_bobs_or_points():
    assert build_segments(_pipe("L1", None, None), []) == []
