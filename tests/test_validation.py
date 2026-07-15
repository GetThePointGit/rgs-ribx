import rgs_ribx
from rgs_ribx.model.validation import validate_network


def test_pipe_completeness_and_ranges():
    manholes = [rgs_ribx.Manhole(code="A"), rgs_ribx.Manhole(code="B")]
    pipes = [
        # ok pipe
        rgs_ribx.Pipe(code="L1", manhole1="A", manhole2="B", bob1=-2.0, bob2=-2.1,
                      diameter=0.3, length=30.0),
        # missing bob2, diameter out of range, manhole2 not present
        rgs_ribx.Pipe(code="L2", manhole1="A", manhole2="Z", bob1=-2.0, bob2=None,
                      diameter=5.0, length=30.0),
    ]
    result = validate_network(manholes, pipes)
    assert result["pipes"]["L1"] == []
    issues = " | ".join(result["pipes"]["L2"]).lower()
    assert "bob" in issues          # missing bob2
    assert "diameter" in issues     # 5.0 m -> 5000 mm > 3000
    assert "knoop" in issues or "manhole" in issues  # dangling manhole2


def test_measured_length_mismatch_flagged():
    manholes = [rgs_ribx.Manhole(code="A"), rgs_ribx.Manhole(code="B")]
    pipe = rgs_ribx.Pipe(code="L1", manhole1="A", manhole2="B", bob1=-2.0, bob2=-2.1,
                         diameter=0.3, length=30.0)
    # measured length 50 m vs geometry 30 m -> >20% mismatch
    result = validate_network(manholes, [pipe], measured_length={"L1": 50.0})
    assert any("lengte" in i.lower() for i in result["pipes"]["L1"])


def test_bob_at_or_above_ground_level_flagged():
    # RIBX exports gebruiken 0.00 als placeholder voor "BOB niet gemeten"; een BOB
    # op of boven het maaiveld van de aangrenzende put is fysiek onmogelijk.
    manholes = [rgs_ribx.Manhole(code="A", ground_level=-3.29),
                rgs_ribx.Manhole(code="B", ground_level=-3.21)]
    pipes = [
        rgs_ribx.Pipe(code="L1", manhole1="A", manhole2="B", bob1=0.0, bob2=0.0,
                      diameter=0.25, length=23.0),
        rgs_ribx.Pipe(code="L2", manhole1="A", manhole2="B", bob1=-5.93, bob2=-5.98,
                      diameter=0.25, length=14.5),
    ]
    result = validate_network(manholes, pipes)
    l1 = result["pipes"]["L1"]
    assert any("maaiveld" in i.lower() for i in l1)
    assert all(i.severity == "warning" for i in l1 if "maaiveld" in i.lower())
    assert result["pipes"]["L2"] == []


def test_bob_check_skipped_without_ground_level():
    # Maaiveld onbekend (of put onbekend): geen maaiveld-waarschuwing mogelijk.
    manholes = [rgs_ribx.Manhole(code="A"), rgs_ribx.Manhole(code="B")]
    pipes = [rgs_ribx.Pipe(code="L1", manhole1="A", manhole2="B", bob1=0.0, bob2=0.0,
                           diameter=0.25, length=23.0)]
    result = validate_network(manholes, pipes)
    assert not any("maaiveld" in i.lower() for i in result["pipes"]["L1"])


def test_issues_carry_severity():
    manholes = [rgs_ribx.Manhole(code="A", geometry_wkt="POINT (0 0)")]
    pipes = [
        rgs_ribx.Pipe(code="L1", manhole1="A", manhole2="Z", bob1=-2.0, bob2=None,
                      diameter=5.0, length=30.0),
    ]
    result = rgs_ribx.validate_network(manholes, pipes)
    issues = result["pipes"]["L1"]
    sev = {str(i): i.severity for i in issues}
    # missing bob2 + dangling manhole2 are errors; diameter out of range is a warning
    assert sev["BOB ontbreekt (begin of eind)"] == "error"
    assert any(s == "error" for k, s in sev.items() if "Knooppunt" in k)
    assert any(s == "warning" for k, s in sev.items() if "Diameter buiten bereik" in k)
    # still plain strings (backward compatible)
    assert "; ".join(issues)  # joinable
