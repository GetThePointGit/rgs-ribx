from rgs_ribx.parsing import ribx_to_pandas


def test_parses_pipe_and_manhole(fixtures_dir):
    objects, observations, errors = ribx_to_pandas(fixtures_dir / "minimal.ribx")

    assert set(objects.keys()) == {"A", "C"}
    assert objects["A"].iloc[0]["AAA"] == "L001"
    assert objects["A"].iloc[0]["ACB"] == "300"
    assert objects["C"].iloc[0]["CAA"] == "P001"
    assert (errors["level"] == "error").sum() == 0


def test_geometry_extracted_as_text(fixtures_dir):
    objects, _observations, _errors = ribx_to_pandas(fixtures_dir / "minimal.ribx")
    assert objects["A"].iloc[0]["AAE"] == "100000.000 400000.000"
    assert objects["A"].iloc[0]["AXY"] == "100000.000 400000.000 100030.000 400000.000"


def test_observations_linked_to_object(fixtures_dir):
    _objects, observations, _errors = ribx_to_pandas(fixtures_dir / "minimal.ribx")
    obs_a = observations["A"]
    assert len(obs_a) == 2
    assert set(obs_a["_object_code"]) == {"L001"}
    assert sorted(obs_a["A"]) == ["BAF", "BCA"]


def test_missing_file_returns_error():
    objects, observations, errors = ribx_to_pandas("/no/such/file.ribx")
    assert objects == {}
    assert (errors["level"] == "error").sum() == 1
