import pytest

from rgs_ribx.model.geometry import (
    gml_pos_to_wkt_point,
    gml_poslist_to_wkt_linestring,
    wkt_linestring_length,
)


def test_linestring_length_straight():
    assert wkt_linestring_length("LINESTRING (100000 400000, 100030 400000)") == 30.0


def test_linestring_length_multi_segment():
    # legs 30 then 40 -> 70
    assert wkt_linestring_length("LINESTRING (0 0, 30 0, 30 40)") == 70.0


def test_linestring_length_invalid_returns_none():
    assert wkt_linestring_length(None) is None
    assert wkt_linestring_length("POINT (1 2)") is None


def test_point_two_coords():
    assert gml_pos_to_wkt_point("100000.000 400000.000") == "POINT (100000 400000)"


def test_point_with_z_drops_z():
    # 3D coordinate: keep X Y only (QGIS pipe/manhole layers are 2D here)
    assert gml_pos_to_wkt_point("100000 400000 -2.5") == "POINT (100000 400000)"


def test_linestring():
    wkt = gml_poslist_to_wkt_linestring("100000 400000 100030 400000")
    assert wkt == "LINESTRING (100000 400000, 100030 400000)"


def test_none_input_returns_none():
    assert gml_pos_to_wkt_point(None) is None
    assert gml_poslist_to_wkt_linestring("") is None


def test_odd_coordinate_count_raises():
    with pytest.raises(ValueError):
        gml_poslist_to_wkt_linestring("100000 400000 100030")
