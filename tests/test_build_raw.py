import rgs_ribx


def test_build_from_ribx_exposes_raw_measurements(fixtures_dir):
    result = rgs_ribx.build_from_ribx(fixtures_dir / "inclined.ribx")
    raw = result.raw_measurements
    assert "L001" in raw
    rm = raw["L001"]
    assert rm.measurement_type == "J"
    assert rm.reverse is False
    dists = sorted(p["dist"] for p in rm.points)
    assert dists == [0.0, 15.0, 30.0]
    assert any(p["value"] == -1.0 for p in rm.points)
