"""Convert RIBX/GML coordinate strings to WKT (X Y only, EPSG:28992).

RIBX geometry arrives as plain coordinate strings already extracted by the
parser: ``"x y[ z]"`` for points and ``"x1 y1 x2 y2 ..."`` for linestrings.
We emit 2D WKT and drop any Z value on points (the longitudinal profile uses
BOB fields, not geometry Z).
"""

from __future__ import annotations

import math


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


def wkt_linestring_length(wkt: str | None) -> "float | None":
    """Planar 2D length (metres, EPSG:28992) of a WKT LINESTRING.

    Returns None if ``wkt`` is empty or not a parseable LINESTRING. Used to
    populate ``Pipe.length`` so trajectory routing and the side-view profile
    have a real distance to work with.
    """
    if not wkt or "LINESTRING" not in wkt.upper():
        return None
    try:
        inside = wkt[wkt.index("(") + 1: wkt.rindex(")")]
    except ValueError:
        return None
    points = []
    for part in inside.split(","):
        coords = part.split()
        if len(coords) >= 2:
            points.append((float(coords[0]), float(coords[1])))
    if len(points) < 2:
        return None
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        total += math.hypot(x2 - x1, y2 - y1)
    return total
