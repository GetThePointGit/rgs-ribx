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
from rgs_ribx.parsing import ribx_to_pandas


@dataclass
class BuildResult:
    """Container for entities built from one RIBX file."""

    manholes: list
    pipes: list
    inspections: list
    errors: object  # pandas DataFrame from the parser
    measurements: dict = None  # {pipe_code: [MeasurementPoint]} from inclination


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


def build_from_objects(objects: dict, observations: dict) -> "tuple[list, list, list]":
    """Build (manholes, pipes, inspections) from parser output dicts."""
    manholes: list = []
    pipes: list = []
    inspections: list = []

    seen_manholes: dict = {}
    measurements: dict = {}

    # --- Pipes (ZB_A) ---
    if "A" in objects:
        df = objects["A"]
        for idx, row in df.iterrows():
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
            profile = _build_inclination(observations.get("A"), idx, pipe, reverse)
            if profile:
                measurements[pipe.code] = profile

            insp = Inspection(
                object_code=pipe.code,
                object_type="A",
                date=pipe.inspection_date,
                observations=_build_observations(observations.get("A"), pipe.code, idx),
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
    return manholes, pipes, inspections, measurements


def _build_inclination(obs_df, object_idx, pipe, reverse):
    """Build the inclination (BXA) bob profile for one pipe, or [] if none."""
    if obs_df is None or len(obs_df) == 0 or pipe.bob1 is None or pipe.bob2 is None:
        return []
    subset = obs_df[
        (obs_df["_object_idx"] == object_idx) & (obs_df["A"] == fm.INCLINATION_CODE)
    ]
    if len(subset) == 0:
        return []
    measurement_type = None
    mrios = []
    for _i, row in subset.iterrows():
        dist = _to_float(_get(row, "I"))
        value = _to_float(_get(row, "D"))
        if dist is None or value is None:
            continue
        if measurement_type is None:
            measurement_type = _opt_str(_get(row, "B"))
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


def _register_endpoint(seen: dict, code: str, wkt) -> None:
    """Add a manhole stub from a pipe endpoint if we don't have it yet."""
    if not code:
        return
    if code not in seen:
        seen[code] = Manhole(code=code, geometry_wkt=wkt)


def _build_observations(obs_df, object_code: str, object_idx: int) -> list:
    if obs_df is None or len(obs_df) == 0:
        return []
    subset = obs_df[obs_df["_object_idx"] == object_idx]
    result = []
    for _i, row in subset.iterrows():
        kwargs = {"object_code": object_code, "code": str(_get(row, "A") or "")}
        for ribx_field, attr in fm.OBSERVATION_FIELD_MAP.items():
            if attr == "code":
                continue
            value = _get(row, ribx_field)
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


def build_from_ribx(ribx_path: "Path | str") -> BuildResult:
    """Parse a RIBX file and build the domain model."""
    objects, observations, errors = ribx_to_pandas(ribx_path)
    manholes, pipes, inspections, measurements = build_from_objects(objects, observations)
    return BuildResult(
        manholes=manholes,
        pipes=pipes,
        inspections=inspections,
        errors=errors,
        measurements=measurements,
    )
