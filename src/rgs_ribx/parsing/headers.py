"""Load the per-object-type RIBX field definitions from bundled CSVs."""

import csv
from functools import lru_cache
from importlib import resources

# Maps the one-letter object prefix to its header CSV filename.
_HEADER_FILES = {
    "A": "A_inspectie_leiding.csv",
    "C": "C_inspectie_put.csv",
    "E": "E_inspectie_reiniging_kolk.csv",
    "G": "G_reiniging_leiding.csv",
    "J": "J_reiniging_put.csv",
    "L": "L_stortbon_reiniging.csv",
    "M": "M_calamiteit_reiniging.csv",
    "N": "N_stagnatie_reiniging.csv",
    "Q": "Q_reiniging_drainageleiding.csv",
    "S": "S_reiniging_drainageput.csv",
}


@lru_cache(maxsize=None)
def load_header(object_prefix: str) -> dict:
    """Return the field definitions for an object type.

    Parameters
    ----------
    object_prefix : str
        One-letter object type, e.g. ``"A"`` (pipe inspection).

    Returns
    -------
    dict
        Maps field code (e.g. ``"AAA"``) to a dict of column values
        (``naam``, ``waarde_type``, ``heen``, ``terug``, ``min_waarde``,
        ``max_waarde``, ...).

    Raises
    ------
    KeyError
        If ``object_prefix`` has no header file.
    """
    filename = _HEADER_FILES[object_prefix]
    package = "rgs_ribx.parsing.object_headers"
    text = resources.files(package).joinpath(filename).read_text(encoding="utf-8")
    reader = csv.DictReader(text.splitlines())
    return {row["code"]: row for row in reader if row.get("code")}


def header_label(object_prefix: str, field_code: str) -> str | None:
    """Return the human label (``naam``) for a field, or None if unknown.

    Parameters
    ----------
    object_prefix : str
        One-letter object type, e.g. ``"A"``.
    field_code : str
        Field code to look up, e.g. ``"AAA"``.

    Returns
    -------
    str or None
        The ``naam`` value from the header CSV, or ``None`` if the field
        code is not present in the header.
    """
    header = load_header(object_prefix)
    row = header.get(field_code)
    return row["naam"] if row else None
