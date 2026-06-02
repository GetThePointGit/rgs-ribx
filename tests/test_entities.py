from rgs_ribx.model.entities import Manhole, Observation, Pipe, Inspection


def test_manhole_defaults():
    m = Manhole(code="P001", geometry_wkt="POINT (1 2)")
    assert m.code == "P001"
    assert m.is_sink is False
    assert m.ground_level is None


def test_pipe_is_rectangular():
    circ = Pipe(code="L001", manhole1="P001", manhole2="P002", shape="A")
    rect = Pipe(code="L002", manhole1="P001", manhole2="P002", shape="B")
    assert circ.is_rectangular is False
    assert rect.is_rectangular is True


def test_inspection_holds_observations():
    obs = Observation(object_code="L001", code="BCA", distance=12.5)
    insp = Inspection(object_code="L001", object_type="A", observations=[obs])
    assert insp.observations[0].code == "BCA"
    assert insp.observations[0].distance == 12.5
