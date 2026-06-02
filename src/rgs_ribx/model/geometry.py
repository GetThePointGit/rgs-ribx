"""Convert RIBX/GML coordinate strings to WKT (X Y only, EPSG:28992).

RIBX geometry arrives as plain coordinate strings already extracted by the
parser: ``"x y[ z]"`` for points and ``"x1 y1 x2 y2 ..."`` for linestrings.
We emit 2D WKT and drop any Z value on points (the longitudinal profile uses
BOB fields, not geometry Z).
"""


def _fmt(value: float) -> str:
    """Format a coordinate without trailing zeros (100000.000 -> '100000')."""
    return f"{value:.6f}".rstrip("0").rstrip(".")


def gml_pos_to_wkt_point(pos: str | None) -> str | None:
    """Convert a GML ``pos`` string to a WKT POINT, or None if empty."""
    if not pos:
        return None
    parts = [float(p) for p in pos.split()]
    if len(parts) < 2:
        raise ValueError(f"Point needs at least 2 coordinates, got: {pos!r}")
    x, y = parts[0], parts[1]
    return f"POINT ({_fmt(x)} {_fmt(y)})"


def gml_poslist_to_wkt_linestring(poslist: str | None) -> str | None:
    """Convert a GML ``posList`` string to a WKT LINESTRING, or None if empty.

    RIBX-NL posLists are 2D (``x y`` pairs). We require an even coordinate
    count of at least 4 (i.e. >= 2 vertices); anything else is malformed.
    """
    if not poslist:
        return None
    coords = [float(p) for p in poslist.split()]
    if len(coords) % 2 != 0 or len(coords) < 4:
        raise ValueError(
            f"LINESTRING needs an even count of >= 4 coordinates "
            f"(>= 2 vertices), got: {poslist!r}"
        )
    vertices = []
    for i in range(0, len(coords), 2):
        vertices.append(f"{_fmt(coords[i])} {_fmt(coords[i + 1])}")
    return "LINESTRING (" + ", ".join(vertices) + ")"
