import rgs_ribx
from rgs_ribx.model.enrich import integrate_profiles
from rgs_ribx.model.raw import RawMeasurements


def _pipe(code, bob1, bob2, length=30.0, diameter=0.3):
    return rgs_ribx.Pipe(code=code, manhole1="A", manhole2="B",
                         bob1=bob1, bob2=bob2, length=length, diameter=diameter, shape="A")


def test_integrate_absolute_type_b_profile():
    pipes = {"L1": _pipe("L1", -2.0, -2.0)}
    raw = {"L1": RawMeasurements("L1", "AA", reverse=False, points=[
        {"dist": 0.0, "value": 0.0},
        {"dist": 15.0, "value": -0.3},
        {"dist": 30.0, "value": 0.0},
    ])}
    profiles = integrate_profiles(pipes, raw, correct_bob=False)
    pts = sorted(profiles["L1"], key=lambda p: p.dist)
    assert [round(p.dist, 1) for p in pts] == [0.0, 15.0, 30.0]
    # AA = bob1 + (bob2-bob1)*pct + value ; flat bobs -> -2.0 + value
    assert [round(p.bob, 2) for p in pts] == [-2.0, -2.3, -2.0]


def test_integrate_applies_bob_correction_per_pipe():
    # Linear drift below a flat ideal -> de-trended to the ideal at all points.
    pipes = {"L1": _pipe("L1", -2.0, -2.0)}
    raw = {"L1": RawMeasurements("L1", "AA", reverse=False, points=[
        {"dist": 0.0, "value": -0.5},
        {"dist": 15.0, "value": -0.6},
        {"dist": 30.0, "value": -0.7},
    ])}
    profiles = integrate_profiles(pipes, raw, correct_bob=True)
    pts = sorted(profiles["L1"], key=lambda p: p.dist)
    assert [round(p.bob, 2) for p in pts] == [-2.0, -2.0, -2.0]


def test_integrate_skips_pipe_without_bobs():
    pipes = {"L1": _pipe("L1", None, None)}
    raw = {"L1": RawMeasurements("L1", "J", points=[{"dist": 0.0, "value": 0.0}])}
    assert integrate_profiles(pipes, raw, correct_bob=True) == {}
