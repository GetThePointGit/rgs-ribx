import rgs_ribx


def test_enrich_pipeline_from_ribx(fixtures_dir):
    res = rgs_ribx.build_from_ribx(fixtures_dir / "inclined.ribx")
    pipes = {p.code: p for p in res.pipes}

    profiles = rgs_ribx.integrate_profiles(pipes, res.raw_measurements, correct_bob=True)
    assert "L001" in profiles and len(profiles["L001"]) >= 2

    segs = rgs_ribx.build_segments(pipes["L001"], profiles["L001"], min_length=1.0)
    assert segs and all(s["source"] == "measured" for s in segs)

    issues = rgs_ribx.validate_network(res.manholes, res.pipes)
    assert "L001" in issues["pipes"]


def test_enrich_is_rerunnable_after_bob_change(fixtures_dir):
    res = rgs_ribx.build_from_ribx(fixtures_dir / "inclined.ribx")
    pipes = {p.code: p for p in res.pipes}
    first = rgs_ribx.integrate_profiles(pipes, res.raw_measurements, correct_bob=True)
    first_end = sorted(first["L001"], key=lambda p: p.dist)[-1].bob

    pipes["L001"].bob2 = pipes["L001"].bob2 - 1.0  # edit a BOB
    second = rgs_ribx.integrate_profiles(pipes, res.raw_measurements, correct_bob=True)
    second_end = sorted(second["L001"], key=lambda p: p.dist)[-1].bob
    assert round(second_end - first_end, 2) == -1.0  # end follows the edited BOB
