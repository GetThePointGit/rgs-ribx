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
    wkt_linestring_length,
)
from rgs_ribx.parsing import ribx_to_pandas


@dataclass
class BuildResult:
    """Container for entities built from one RIBX file."""

    manholes: list
    pipes: list
    inspections: list
    errors: object  # pandas DataFrame from the parser


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

    # --- Pipes (ZB_A) ---
    if "A" in objects:
        df = objects["A"]
        for idx, row in df.iterrows():
            code = _get(row, fm.REF_FIELDS["A"])
            if code is None:
                continue
            geom_wkt = gml_poslist_to_wkt_linestring(_get(row, fm.PIPE_GEOM_FIELDS["A"]))
            pipe = Pipe(
                code=str(code),
                manhole1=str(_get(row, fm.NODE1_FIELDS["A"]) or ""),
                manhole2=str(_get(row, fm.NODE2_FIELDS["A"]) or ""),
                geometry_wkt=geom_wkt,
                shape=str(_get(row, fm.PIPE_SHAPE_FIELD) or "A"),
                diameter=_to_float(_get(row, fm.PIPE_DIAMETER_FIELD)),
                width=_to_float(_get(row, fm.PIPE_WIDTH_FIELD)),
                bob1=_to_float(_get(row, fm.PIPE_BOB1_FIELD)),
                bob2=_to_float(_get(row, fm.PIPE_BOB2_FIELD)),
                length=wkt_linestring_length(geom_wkt),
                material=_opt_str(_get(row, fm.PIPE_MATERIAL_FIELD)),
                sewerage_type=_opt_str(_get(row, fm.PIPE_SEWERAGE_TYPE_FIELD)),
                inspection_date=_to_date(_get(row, fm.DATE_FIELDS["A"])),
                source_line=_to_int(_get(row, "_source_line")),
            )
            pipes.append(pipe)

            _register_endpoint(seen_manholes, pipe.manhole1,
                               gml_pos_to_wkt_point(_get(row, fm.NODE1_GEOM_FIELDS["A"])))
            _register_endpoint(seen_manholes, pipe.manhole2,
                               gml_pos_to_wkt_point(_get(row, fm.NODE2_GEOM_FIELDS["A"])))

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
    return manholes, pipes, inspections


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
    manholes, pipes, inspections = build_from_objects(objects, observations)
    return BuildResult(manholes=manholes, pipes=pipes, inspections=inspections, errors=errors)
