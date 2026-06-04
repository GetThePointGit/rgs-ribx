from rgs_ribx.model.raw import RawMeasurements


def test_raw_measurements_holds_points_type_and_direction():
    raw = RawMeasurements(
        pipe_code="L1",
        measurement_type="J",
        reverse=False,
        points=[{"dist": 0.0, "value": -2.0}, {"dist": 10.0, "value": -5.0}],
    )
    assert raw.pipe_code == "L1"
    assert raw.measurement_type == "J"
    assert raw.reverse is False
    assert len(raw.points) == 2
    assert raw.points[0]["value"] == -2.0
