"""Parse classic SUFRIB 2.1 text files (.rib / .hel / .rmb).

Pipe-delimited, one record per line; the first field is the record type. The
network lives in ``*PUT`` (manholes) and ``*RIOO`` (pipes); the longitudinal
height/inclination measurements live in ``*MRIO``. Dispatch is by record type
(content), not file extension, so .rib + .hel or .rib + .rmb both work and may
even be combined in one file.

Field order mirrors lizard-progress' sufriblib; values are stripped, empty ->
None. Coordinates are RD (EPSG:28992) as ``x/y``.
"""

from __future__ import annotations

# Field order per record (from SUFRIB 2.1 / lizard sufriblib).
PUT_FIELDS = [
    "record_type", "CAA", "CAB", "CAJ", "CAL", "CAO", "CAP", "CAQ", "CAR", "CAS",
    "CBC", "CBD", "CBF", "CBG", "CBK", "CBL", "CBM", "CBN", "CBO", "CCA", "CCB",
    "CCC", "CCD", "CCG", "CCK", "CCL", "CCM", "CCN", "CCO", "CCP", "CCQ", "CCR",
    "CCS", "CCT", "CDA", "CDB", "CDC", "CDD", "CDE", "CCU",
]
RIOO_FIELDS = [
    "record_type", "AAA", "AAB", "AAC", "AAD", "AAE", "AAF", "AAG", "AAH", "AAI",
    "AAJ", "AAK", "AAL", "AAO", "AAP", "AAQ", "AAS", "ABC", "ABF", "ABG", "ABK",
    "ABL", "ABM", "ABN", "ABO", "ABQ", "ACA", "ACB", "ACC", "ACD", "ACE", "ACF",
    "ACG", "ACH", "ACI", "ACJ", "ACK", "ACL", "ACM", "ACN", "ACO", "ACP", "ACQ",
    "ADA", "ADB", "ADC", "ADE", "ACR", "ACS",
]
MRIO_FIELDS = [
    "record_type", "ZYA", "ZYB", "ZYE", "ZYK", "ZYL", "ZYM", "ZYN", "ZYO", "ZYP",
    "ZYQ", "ZYR", "ZYS", "ZYT", "ZYU", "ZYV", "ZYW", "ZYX", "ZYY", "ZYZ",
]

_RECORDS = {"*PUT": PUT_FIELDS, "*RIOO": RIOO_FIELDS, "*MRIO": MRIO_FIELDS}


def _row(line, names):
    parts = line.rstrip("\r\n").split("|")
    row = {}
    for i, name in enumerate(names):
        value = parts[i].strip() if i < len(parts) else ""
        row[name] = value or None
    return row


def parse_sufrib(paths):
    """Read one or more SUFRIB files -> (puts, rioos, mrios) lists of field dicts."""
    if isinstance(paths, (str, bytes)):
        paths = [paths]
    puts, rioos, mrios = [], [], []
    bucket = {"*PUT": puts, "*RIOO": rioos, "*MRIO": mrios}
    for path in paths:
        if not path:
            continue
        with open(path, encoding="latin-1") as handle:
            for line in handle:
                record_type = line.split("|", 1)[0].strip()
                names = _RECORDS.get(record_type)
                if names is not None:
                    bucket[record_type].append(_row(line, names))
    return puts, rioos, mrios


def parse_coordinate(value):
    """Parse a SUFRIB ``x/y`` RD coordinate to (x, y) floats, or None."""
    if not value or "/" not in value:
        return None
    x, y = value.split("/", 1)
    try:
        return float(x), float(y)
    except ValueError:
        return None
