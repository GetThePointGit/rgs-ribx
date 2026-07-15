"""Completeness + range validation of the sewer network (per feature)."""

from __future__ import annotations

DIAMETER_MIN_MM = 50.0
DIAMETER_MAX_MM = 3000.0
LENGTH_TOLERANCE = 0.20  # measured vs geometry length


class Issue(str):
    """A validation message that also carries a severity.

    Subclasses ``str`` so existing callers that join/compare the messages keep
    working; ``severity`` is ``"error"`` (missing/unknown required data) or
    ``"warning"`` (a value outside its expected range).
    """

    def __new__(cls, message, severity="error"):
        obj = super().__new__(cls, message)
        obj.severity = severity
        return obj


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
    ground_levels = {m.code: m.ground_level for m in manholes
                     if m.ground_level is not None}

    pipe_issues = {}
    for p in pipes:
        issues = []
        if not p.code:
            issues.append(Issue("Leidingcode ontbreekt", "error"))
        if p.bob1 is None or p.bob2 is None:
            issues.append(Issue("BOB ontbreekt (begin of eind)", "error"))
        # Een BOB op of boven het maaiveld van de aangrenzende put is fysiek
        # onmogelijk; RIBX-exports gebruiken o.a. 0.00 als placeholder voor
        # "niet gemeten" en die valt hiermee door de mand.
        for bob, ref, label in ((p.bob1, p.manhole1, "begin"),
                                (p.bob2, p.manhole2, "eind")):
            gl = ground_levels.get(ref)
            if bob is not None and gl is not None and bob >= gl:
                issues.append(Issue(
                    f"BOB {label} op of boven maaiveld "
                    f"({bob:.2f} m t.o.v. maaiveld {gl:.2f} m)", "warning"))
        if p.diameter is None:
            issues.append(Issue("Diameter ontbreekt", "error"))
        else:
            d_mm = p.diameter * 1000.0
            if d_mm < DIAMETER_MIN_MM or d_mm > DIAMETER_MAX_MM:
                issues.append(Issue(f"Diameter buiten bereik ({d_mm:.0f} mm)", "warning"))
        for ref in (p.manhole1, p.manhole2):
            if not ref or ref not in manhole_codes:
                issues.append(Issue(f"Knooppunt ontbreekt of onbekend ({ref!r})", "error"))
        ml = measured_length.get(p.code)
        if ml is not None and p.length:
            if abs(ml - p.length) > LENGTH_TOLERANCE * p.length:
                issues.append(Issue(
                    f"Meetlengte wijkt af (gemeten {ml:.1f} m vs {p.length:.1f} m)", "warning"))
        pipe_issues[p.code] = issues

    manhole_issues = {}
    for m in manholes:
        issues = []
        if not m.code:
            issues.append(Issue("Putcode ontbreekt", "error"))
        if m.geometry_wkt is None:
            issues.append(Issue("Geometrie ontbreekt", "error"))
        manhole_issues[m.code] = issues

    return {"pipes": pipe_issues, "manholes": manhole_issues}
