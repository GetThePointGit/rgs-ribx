import pytest

import rgs_ribx
from rgs_ribx.parsing.sufrib import MRIO_FIELDS, PUT_FIELDS, RIOO_FIELDS


def _line(fields, rt, **vals):
    arr = [""] * len(fields)
    arr[0] = rt
    for name, value in vals.items():
        arr[fields.index(name)] = str(value)
    return "|".join(arr)


def _write_example(tmp_path):
    rib = tmp_path / "net.rib"
    rmb = tmp_path / "meas.rmb"
    rib.write_text("\n".join([
        _line(PUT_FIELDS, "*PUT", CAA="P1", CAB="155000.00/463000.00", CCU="0.00"),
        _line(PUT_FIELDS, "*PUT", CAA="P2", CAB="155030.00/463000.00", CAR="Xs"),
        _line(RIOO_FIELDS, "*RIOO", AAA="L1", AAD="P1", AAE="155000.00/463000.00",
              AAF="P2", AAG="155030.00/463000.00", ACA="1", ACB="300",
              ACR="-2.00", ACS="-2.00"),
    ]) + "\n", encoding="latin-1")
    # CB -> absolute-to-ideal-line metres (matches the old tool's mapping).
    rmb.write_text("\n".join([
        _line(MRIO_FIELDS, "*MRIO", ZYE="L1", ZYB="1", ZYR="C", ZYS="B", ZYA="0", ZYT="0.0"),
        _line(MRIO_FIELDS, "*MRIO", ZYE="L1", ZYB="1", ZYR="C", ZYS="B", ZYA="15", ZYT="-0.3"),
        _line(MRIO_FIELDS, "*MRIO", ZYE="L1", ZYB="1", ZYR="C", ZYS="B", ZYA="30", ZYT="0.0"),
    ]) + "\n", encoding="latin-1")
    return rib, rmb


def test_build_from_sufrib_network(tmp_path):
    rib, rmb = _write_example(tmp_path)
    res = rgs_ribx.build_from_sufrib([str(rib), str(rmb)])

    manholes = {m.code: m for m in res.manholes}
    assert set(manholes) == {"P1", "P2"}
    assert manholes["P1"].geometry_wkt == "POINT (155000 463000)"
    assert manholes["P1"].ground_level == 0.0
    assert manholes["P2"].is_sink is True

    pipe = {p.code: p for p in res.pipes}["L1"]
    assert pipe.manhole1 == "P1" and pipe.manhole2 == "P2"
    assert pipe.diameter == 0.3          # 300 mm -> 0.3 m
    assert pipe.bob1 == -2.0 and pipe.bob2 == -2.0
    assert pipe.geometry_wkt == "LINESTRING (155000 463000, 155030 463000)"
    assert pipe.length == 30.0


def test_build_from_sufrib_measurements(tmp_path):
    rib, rmb = _write_example(tmp_path)
    res = rgs_ribx.build_from_sufrib([str(rib), str(rmb)])
    pts = sorted(res.measurements["L1"], key=lambda m: m.dist)
    assert [round(p.dist, 1) for p in pts] == [0.0, 15.0, 30.0]
    # CB -> AA: bob = ideal(flat -2.0) + value
    assert [round(p.bob, 2) for p in pts] == [-2.0, -2.3, -2.0]
    assert pts[1].obb == pytest.approx(pts[1].bob + 0.3)
