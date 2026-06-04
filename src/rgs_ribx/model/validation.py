"""Completeness + range validation of the sewer network (per feature)."""

from __future__ import annotations

DIAMETER_MIN_MM = 50.0
DIAMETER_MAX_MM = 3000.0
LENGTH_TOLERANCE = 0.20  # measured vs geometry length


def validate_network(manholes, pipes, measured_length=None):
    """Return {'pipes': {code: [issues]}, 'manholes': {code: [issues]}}.

    Parameters
    ----------
    manholes : list of rgs_ribx.Manhole
        Manholes (putten) in the network.
    pipes : list of rgs_ribx.Pipe
        Pipes (leidingen/strengen) in the network.
    measured_length : dict, optional
        Mapping of pipe code to measured length in metres. When provided,
        a pipe is flagged if its measured length deviates more than
        ``LENGTH_TOLERANCE`` from the geometry length.

    Returns
    -------
    dict
        ``{'pipes': {code: [issue, ...]}, 'manholes': {code: [issue, ...]}}``
        where each issue is a short Dutch string describing a problem.
    """
    measured_length = measured_length or {}
    manhole_codes = {m.code for m in manholes}

    pipe_issues = {}
    for p in pipes:
        issues = []
        if not p.code:
            issues.append("Leidingcode ontbreekt")
        if p.bob1 is None or p.bob2 is None:
            issues.append("BOB ontbreekt (begin of eind)")
        if p.diameter is None:
            issues.append("Diameter ontbreekt")
        else:
            d_mm = p.diameter * 1000.0
            if d_mm < DIAMETER_MIN_MM or d_mm > DIAMETER_MAX_MM:
                issues.append(f"Diameter buiten bereik ({d_mm:.0f} mm)")
        for ref in (p.manhole1, p.manhole2):
            if not ref or ref not in manhole_codes:
                issues.append(f"Knooppunt ontbreekt of onbekend ({ref!r})")
        ml = measured_length.get(p.code)
        if ml is not None and p.length:
            if abs(ml - p.length) > LENGTH_TOLERANCE * p.length:
                issues.append(
                    f"Meetlengte wijkt af (gemeten {ml:.1f} m vs {p.length:.1f} m)"
                )
        pipe_issues[p.code] = issues

    manhole_issues = {}
    for m in manholes:
        issues = []
        if not m.code:
            issues.append("Putcode ontbreekt")
        if m.geometry_wkt is None:
            issues.append("Geometrie ontbreekt")
        manhole_issues[m.code] = issues

    return {"pipes": pipe_issues, "manholes": manhole_issues}
