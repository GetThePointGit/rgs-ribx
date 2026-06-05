"""Build domain entities from parsed RIBX DataFrames.

Public entry point: :func:`build_from_ribx`. The intermediate
:func:`build_from_objects` works on the dicts/DataFrames returned by
``ribx_to_pandas`` so the plugin can reuse it for GeoPackage-sourced records.
"""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from rgs_ribx.model import field_maps as fm
from rgs_ribx.model.entities import Inspection, Manhole, Observation, Pipe
from rgs_ribx.model.geometry import (
    gml_pos_to_wkt_point,
    gml_poslist_to_wkt_linestring,
    pos_pair_to_wkt_linestring,
    wkt_linestring_length,
)
from rgs_ribx.model.inclination import build_inclination_profile
from rgs_ribx.model.raw import RawMeasurements
from rgs_ribx.parsing import ribx_to_pandas


@dataclass
class BuildResult:
    """Container for entities built from one RIBX file."""

    manholes: list
    pipes: list
    inspections: list
    errors: object  # pandas DataFrame from the parser
    measurements: dict = None  # {pipe_code: [MeasurementPoint]} from inclination
    raw_measurements: dict = None  # {pipe_code: RawMeasurements} (un-integrated)


def _first(*values):
    """Return the first value that is not None."""
    for value in values:
        if value is not None:
            return value
    return None


def _to_float(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_date(value) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _get(row, key):
    """Safe column access on a pandas row that may lack the column."""
    if key in row.index:
        v = row[key]
        if v is None:
            return None
        try:
            import math

            if isinstance(v, float) and math.isnan(v):
                return None
        except TypeError:
            pass
        return v
    return None


def _getd(row, key):
    """Safe column access on an observation row dict (missing key / NaN -> None).

    The dict counterpart of :func:`_get`, used on the records produced by
    :func:`_observation_groups` so the hot observation loops avoid pandas
    per-cell indexing entirely.
    """
    v = row.get(key)
    if v is None:
        return None
    if isinstance(v, float) and v != v:  # NaN
        return None
    return v


def _observation_groups(obs_df) -> dict:
    """Group an observations DataFrame by ``_object_idx`` into ``{idx: [row_dict, ...]}``.

    The observations frame can hold millions of rows. Previously every object
    re-filtered it (``obs_df[obs_df["_object_idx"] == idx]`` — an O(objects x rows)
    object-dtype scan) and iterated the result with ``DataFrame.iterrows`` (a fresh
    Series per row). Materialising the frame to plain dicts once with
    ``to_dict("records")`` and grouping turns the per-object work into a dict lookup
    plus a cheap Python-list iteration.

    Parameters
    ----------
    obs_df : pandas.DataFrame or None
        The observations frame for one object type (e.g. ``observations["A"]``).

    Returns
    -------
    dict
        ``{object_idx: [row_dict, ...]}``; empty when ``obs_df`` is None/empty.
        Rows without an ``_object_idx`` (orphans) are dropped.
    """
    if obs_df is None or len(obs_df) == 0:
        return {}
    groups: dict = {}
    for row in obs_df.to_dict("records"):
        idx = row.get("_object_idx")
        if idx is None or (isinstance(idx, float) and idx != idx):  # None / NaN
            continue
        groups.setdefault(idx, []).append(row)
    return groups


def build_from_objects(objects: dict, observations: dict,
                       progress=None) -> "tuple[list, list, list]":
    """Build (manholes, pipes, inspections) from parser output dicts.

    Parameters
    ----------
    objects, observations : dict
        Parser output (DataFrame per object type).
    progress : callable, optional
        ``progress(fraction)`` (0..1) called periodically while building pipes, so
        a caller can show import progress. Errors in the callback are ignored.
    """
    manholes: list = []
    pipes: list = []
    inspections: list = []

    seen_manholes: dict = {}
    measurements: dict = {}
    raw_measurements: dict = {}

    def _report(frac):
        if progress is not None:
            try:
                progress(frac)
            except Exception:  # progress feedback must never break the build
                pass

    # --- Pipes (ZB_A) ---
    # Group the (potentially millions of) A observations by object once, so each
    # pipe is a dict lookup instead of a full-frame scan + iterrows.
    obs_a_groups = _observation_groups(observations.get("A"))
    if "A" in objects:
        df = objects["A"]
        n_total = len(df) or 1
        for i, (idx, row) in enumerate(df.iterrows()):
            if i % 25 == 0:
                _report(i / n_total)
            code = _get(row, fm.REF_FIELDS["A"])
            if code is None:
                continue
            node1_pos = _get(row, fm.NODE1_GEOM_FIELDS["A"])
            node2_pos = _get(row, fm.NODE2_GEOM_FIELDS["A"])
            # Geometry: explicit AXY line, else the node1 -> node2 segment.
            geom_wkt = gml_poslist_to_wkt_linestring(_get(row, fm.PIPE_GEOM_FIELDS["A"]))
            if geom_wkt is None:
                geom_wkt = pos_pair_to_wkt_linestring(node1_pos, node2_pos)

            diameter_mm = _to_float(_get(row, fm.PIPE_DIAMETER_FIELD))
            width_mm = _to_float(_get(row, fm.PIPE_WIDTH_FIELD))
            pipe = Pipe(
                code=str(code),
                manhole1=str(_get(row, fm.NODE1_FIELDS["A"]) or ""),
                manhole2=str(_get(row, fm.NODE2_FIELDS["A"]) or ""),
                geometry_wkt=geom_wkt,
                shape=str(_get(row, fm.PIPE_SHAPE_FIELD) or "A"),
                diameter=(diameter_mm / 1000.0) if diameter_mm is not None else None,
                width=(width_mm / 1000.0) if width_mm is not None else None,
                bob1=_first(_to_float(_get(row, fm.PIPE_BOB1_FIELD)),
                            _to_float(_get(row, fm.PIPE_BOB1_ALT_FIELD))),
                bob2=_first(_to_float(_get(row, fm.PIPE_BOB2_FIELD)),
                            _to_float(_get(row, fm.PIPE_BOB2_ALT_FIELD))),
                length=wkt_linestring_length(geom_wkt),
                material=_opt_str(_get(row, fm.PIPE_MATERIAL_FIELD)),
                sewerage_type=_opt_str(_get(row, fm.PIPE_SEWERAGE_TYPE_FIELD)),
                inspection_date=_to_date(_get(row, fm.DATE_FIELDS["A"])),
                source_line=_to_int(_get(row, "_source_line")),
            )
            pipes.append(pipe)

            _register_endpoint(seen_manholes, pipe.manhole1, gml_pos_to_wkt_point(node1_pos))
            _register_endpoint(seen_manholes, pipe.manhole2, gml_pos_to_wkt_point(node2_pos))

            # Inspection ran from AAB; reverse if that is the second node.
            start_node = _opt_str(_get(row, fm.PIPE_START_NODE_FIELD))
            reverse = bool(start_node) and start_node == pipe.manhole2
            obs_rows = obs_a_groups.get(idx, [])
            profile = _build_inclination(obs_rows, pipe, reverse)
            if profile:
                measurements[pipe.code] = profile
            raw = _raw_inclination(obs_rows, pipe.code, reverse)
            if raw is not None:
                raw_measurements[pipe.code] = raw

            insp = Inspection(
                object_code=pipe.code,
                object_type="A",
                date=pipe.inspection_date,
                observations=_build_observations(obs_rows, pipe.code),
            )
            inspections.append(insp)

    # --- Manholes (ZB_C) — authoritative geometry overrides endpoint guesses ---
    if "C" in objects:
        df = objects["C"]
        for _idx, row in df.iterrows():
            code = _get(row, fm.REF_FIELDS["C"])
            if code is None:
                continue
            seen_manholes[str(code)] = Manhole(
                code=str(code),
                geometry_wkt=gml_pos_to_wkt_point(_get(row, fm.MANHOLE_GEOM_FIELDS["C"])),
                node_type=_opt_str(_get(row, fm.MANHOLE_NODE_TYPE_FIELD)),
                ground_level=_to_float(_get(row, fm.MANHOLE_GROUND_LEVEL_FIELD)),
                source_line=_to_int(_get(row, "_source_line")),
            )

    manholes = list(seen_manholes.values())
    return manholes, pipes, inspections, measurements, raw_measurements


def _build_inclination(rows, pipe, reverse):
    """Build the inclination (BXA) bob profile for one pipe, or [] if none.

    ``rows`` is the pre-grouped list of observation dicts for the pipe (see
    :func:`_observation_groups`); only the inclination (BXA) rows are used.
    """
    if not rows or pipe.bob1 is None or pipe.bob2 is None:
        return []
    measurement_type = None
    mrios = []
    for row in rows:
        if _getd(row, "A") != fm.INCLINATION_CODE:
            continue
        dist = _to_float(_getd(row, "I"))
        value = _to_float(_getd(row, "D"))
        if dist is None or value is None:
            continue
        if measurement_type is None:
            measurement_type = _opt_str(_getd(row, "B"))
        mrios.append({"distance": dist, "measurement": value})
    if not mrios:
        return []
    # The measurements run from the inspection start node. When that is the
    # pipe's manhole2 (reverse), integrate from bob2 (swap), matching the old
    # tool — otherwise the sag is built from the wrong end.
    start_bob, end_bob = (pipe.bob2, pipe.bob1) if reverse else (pipe.bob1, pipe.bob2)
    return build_inclination_profile(
        mrios,
        horizontal_distance=pipe.length or 0.0,
        bob1=start_bob,
        bob2=end_bob,
        measurement_type=measurement_type,
        diameter=pipe.diameter or 0.0,
        reverse=reverse,
    )


def _raw_inclination(rows, pipe_code, reverse):
    """Collect raw BXA points (dist, value) + type for one pipe, or None.

    Mirrors :func:`_build_inclination`'s row selection but keeps the points
    un-integrated so the enrich step can re-integrate against edited BOBs.
    ``rows`` is the pre-grouped observation-dict list for the pipe.
    """
    if not rows:
        return None
    measurement_type = None
    points = []
    for row in rows:
        if _getd(row, "A") != fm.INCLINATION_CODE:
            continue
        dist = _to_float(_getd(row, "I"))
        value = _to_float(_getd(row, "D"))
        if dist is None or value is None:
            continue
        if measurement_type is None:
            measurement_type = _opt_str(_getd(row, "B"))
        points.append({"dist": dist, "value": value})
    if not points:
        return None
    return RawMeasurements(pipe_code=pipe_code, measurement_type=measurement_type or "",
                           reverse=reverse, points=points)


def _register_endpoint(seen: dict, code: str, wkt) -> None:
    """Add a manhole stub from a pipe endpoint if we don't have it yet."""
    if not code:
        return
    if code not in seen:
        seen[code] = Manhole(code=code, geometry_wkt=wkt)


def _build_observations(rows, object_code: str) -> list:
    """Build the Observation list for one object from its grouped row dicts."""
    if not rows:
        return []
    result = []
    for row in rows:
        kwargs = {"object_code": object_code, "code": str(_getd(row, "A") or "")}
        for ribx_field, attr in fm.OBSERVATION_FIELD_MAP.items():
            if attr == "code":
                continue
            value = _getd(row, ribx_field)
            if attr == "distance":
                kwargs[attr] = _to_float(value)
            else:
                kwargs[attr] = _opt_str(value)
        result.append(Observation(**kwargs))
    return result


def _opt_str(value) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value)


def _to_int(value) -> Optional[int]:
    f = _to_float(value)
    return int(f) if f is not None else None


def build_from_ribx(ribx_path: "Path | str", progress=None) -> BuildResult:
    """Parse a RIBX file and build the domain model.

    ``progress(fraction)`` (0..1), if given, is called periodically while building
    the pipes (after the XML parse) so callers can show import progress.
    """
    objects, observations, errors = ribx_to_pandas(ribx_path)
    manholes, pipes, inspections, measurements, raw_measurements = build_from_objects(
        objects, observations, progress=progress)
    return BuildResult(
        manholes=manholes,
        pipes=pipes,
        inspections=inspections,
        errors=errors,
        measurements=measurements,
        raw_measurements=raw_measurements,
    )


def build_from_sufrib(paths, progress=None) -> BuildResult:
    """Parse classic SUFRIB files (.rib + .hel/.rmb) and build the domain model.

    ``paths`` is one path or a list (network + measurement files, any order).
    ``progress`` is accepted for API symmetry with :func:`build_from_ribx` (the
    SUFRIB path is not sub-instrumented).
    """
    from rgs_ribx.parsing.sufrib import parse_coordinate, parse_sufrib

    puts, rioos, mrios = parse_sufrib(paths)

    manholes = []
    coords = {}
    put_codes = set()
    for row in puts:
        code = (row.get("CAA") or "").strip()
        if not code or code in put_codes:  # *PUT may repeat across .rib/.rmb
            continue
        put_codes.add(code)
        xy = parse_coordinate(row.get("CAB"))
        if xy:
            coords[code] = xy
        manholes.append(
            Manhole(
                code=code,
                geometry_wkt=(gml_pos_to_wkt_point(f"{xy[0]} {xy[1]}") if xy else None),
                node_type=None,
                ground_level=_to_float(row.get("CCU")),
                is_sink=(row.get("CAR") == "Xs"),
            )
        )

    pipes = []
    seen = {m.code for m in manholes}
    pipe_codes = set()
    for row in rioos:
        code = row.get("AAA")
        if not code or code in pipe_codes:  # *RIOO appears in both .rib and .rmb
            continue
        pipe_codes.add(code)
        m1, m2 = (row.get("AAD") or ""), (row.get("AAF") or "")
        p1 = parse_coordinate(row.get("AAE")) or coords.get(m1)
        p2 = parse_coordinate(row.get("AAG")) or coords.get(m2)
        geom = None
        if p1 and p2:
            geom = gml_poslist_to_wkt_linestring(f"{p1[0]} {p1[1]} {p2[0]} {p2[1]}")
        diameter_mm = _to_float(row.get("ACB"))
        width_mm = _to_float(row.get("ACC"))
        pipes.append(
            Pipe(
                code=str(code),
                manhole1=str(m1),
                manhole2=str(m2),
                geometry_wkt=geom,
                shape=("B" if row.get("ACA") == "2" else "A"),
                diameter=(diameter_mm / 1000.0) if diameter_mm is not None else None,
                width=(width_mm / 1000.0) if width_mm is not None else None,
                bob1=_to_float(row.get("ACR")),
                bob2=_to_float(row.get("ACS")),
                length=wkt_linestring_length(geom),
                inspection_date=_to_date(row.get("ABF")),
            )
        )
        # Register endpoint manholes that had no *PUT record.
        for c, xy in ((m1, p1), (m2, p2)):
            if c and c not in seen:
                seen.add(c)
                manholes.append(Manhole(code=c, geometry_wkt=(
                    gml_pos_to_wkt_point(f"{xy[0]} {xy[1]}") if xy else None)))

    pipes_by_code = {p.code: p for p in pipes}
    measurements = _build_sufrib_measurements(mrios, pipes_by_code)
    raw_measurements = _raw_sufrib_measurements(mrios, pipes_by_code)
    return BuildResult(manholes=manholes, pipes=pipes, inspections=[],
                       errors=None, measurements=measurements,
                       raw_measurements=raw_measurements)


def _build_sufrib_measurements(mrios, pipes_by_code) -> dict:
    """Group *MRIO rows by sewer and integrate into per-pipe MeasurementPoints."""
    by_sewer = {}
    for row in mrios:
        sewer = (row.get("ZYE") or "").strip()
        if sewer:
            by_sewer.setdefault(sewer, []).append(row)

    result = {}
    for sewer, rows in by_sewer.items():
        pipe = pipes_by_code.get(sewer)
        if pipe is None or pipe.bob1 is None or pipe.bob2 is None:
            continue
        zyr = (rows[0].get("ZYR") or "").upper()
        zys = (rows[0].get("ZYS") or "").upper()
        mtype = {"AE": "J", "AF": "K", "CB": "AA"}.get(zyr + zys, "AA")
        reverse = rows[0].get("ZYB") == "2"
        mrios_clean = []
        for row in rows:
            dist = _to_float(row.get("ZYA"))
            value = _to_float(row.get("ZYT"))
            if dist is None or value is None:
                continue
            exp = _to_int(row.get("ZYU"))
            if exp is not None:
                value *= 10 ** exp
            mrios_clean.append({"distance": dist, "measurement": value})
        if not mrios_clean:
            continue
        # Reversed: integrate from the other end (swap BOBs), matching the old tool.
        start_bob, end_bob = (pipe.bob2, pipe.bob1) if reverse else (pipe.bob1, pipe.bob2)
        profile = build_inclination_profile(
            mrios_clean, horizontal_distance=pipe.length or 0.0,
            bob1=start_bob, bob2=end_bob, measurement_type=mtype,
            diameter=pipe.diameter or 0.0, reverse=reverse,
        )
        if profile:
            result[sewer] = profile
    return result


def _raw_sufrib_measurements(mrios, pipes_by_code) -> dict:
    """Group *MRIO rows into RawMeasurements per pipe (un-integrated)."""
    by_sewer = {}
    for row in mrios:
        sewer = (row.get("ZYE") or "").strip()
        if sewer:
            by_sewer.setdefault(sewer, []).append(row)
    result = {}
    for sewer, rows in by_sewer.items():
        if sewer not in pipes_by_code:
            continue
        zyr = (rows[0].get("ZYR") or "").upper()
        zys = (rows[0].get("ZYS") or "").upper()
        mtype = {"AE": "J", "AF": "K", "CB": "AA"}.get(zyr + zys, "AA")
        reverse = rows[0].get("ZYB") == "2"
        points = []
        for row in rows:
            dist = _to_float(row.get("ZYA"))
            value = _to_float(row.get("ZYT"))
            if dist is None or value is None:
                continue
            exp = _to_int(row.get("ZYU"))
            if exp is not None:
                value *= 10 ** exp
            points.append({"dist": dist, "value": value})
        if points:
            result[sewer] = RawMeasurements(pipe_code=sewer, measurement_type=mtype,
                                            reverse=reverse, points=points)
    return result
