# rgs-ribx

Read RIBX (NEN 13508-2) sewer inspection files into a typed Python data model and compute "verloren berging" (lost storage capacity). Pure Python — no Django, no QGIS, no networkx.

## Install

    pip install -e ".[dev]"

## Usage

    import rgs_ribx

    result = rgs_ribx.build_from_ribx("inspection.ribx")
    print(len(result.pipes), "pipes", len(result.manholes), "manholes")

    # Lost capacity: build {pipe_code: [MeasurementPoint, ...]} profiles first,
    # then annotate them in place.
    manholes = {m.code: m for m in result.manholes}
    pipes = {p.code: p for p in result.pipes}
    profiles = {}  # build from inclination observations; see plugin
    rgs_ribx.compute_lost_capacity(manholes, pipes, profiles)

## Layout

- `rgs_ribx.parsing` — RIBX XML -> pandas DataFrames + header definitions
- `rgs_ribx.model` — entities + builder + geometry (WKT, EPSG:28992)
- `rgs_ribx.lost_capacity` — flooded-area math + flood-fill water levels
