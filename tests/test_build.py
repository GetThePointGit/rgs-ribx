from datetime import date

from rgs_ribx.model.build import build_from_ribx


def test_build_pipe_from_fixture(fixtures_dir):
    result = build_from_ribx(fixtures_dir / "minimal.ribx")
    pipes = {p.code: p for p in result.pipes}
    assert "L001" in pipes
    pipe = pipes["L001"]
    assert pipe.manhole1 == "P001"
    assert pipe.manhole2 == "P002"
    assert pipe.shape == "A"
    assert pipe.diameter == 0.300
    assert pipe.bob1 == -2.500
    assert pipe.bob2 == -2.600
    assert pipe.material == "PVC"
    assert pipe.geometry_wkt == "LINESTRING (100000 400000, 100030 400000)"
    assert pipe.length == 30.0
    assert pipe.inspection_date == date(2024, 6, 15)


def test_build_manhole_from_fixture(fixtures_dir):
    result = build_from_ribx(fixtures_dir / "minimal.ribx")
    manholes = {m.code: m for m in result.manholes}
    assert "P001" in manholes
    assert manholes["P001"].geometry_wkt == "POINT (100000 400000)"
    assert manholes["P001"].ground_level == 0.250
    assert manholes["P001"].node_type == "D-01"


def test_build_observations_from_fixture(fixtures_dir):
    result = build_from_ribx(fixtures_dir / "minimal.ribx")
    insp = {i.object_code: i for i in result.inspections}
    assert "L001" in insp
    codes = sorted(o.code for o in insp["L001"].observations)
    assert codes == ["BAF", "BCA"]
    bca = next(o for o in insp["L001"].observations if o.code == "BCA")
    assert bca.distance == 12.5
    assert bca.char1 == "A"
