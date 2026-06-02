"""Typed domain model for sewer inspection data.

All geometry is WKT in EPSG:28992 (RD). Field names follow the
lizard-progress / drainworks models where they overlap so the lost-capacity
algorithm can be ported with minimal change.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

SHAPE_CIRCLE = "A"
SHAPE_RECTANGULAR = "B"
SHAPE_OTHER = "Z"


@dataclass
class Manhole:
    """A sewer manhole (put)."""

    code: str
    geometry_wkt: Optional[str] = None
    node_type: Optional[str] = None       # CAR / JAR (Soort knooppunt)
    ground_level: Optional[float] = None  # CAS putdekselhoogte (m NAP)
    is_sink: bool = False
    source_line: Optional[int] = None


@dataclass
class Pipe:
    """A pipe (leiding/streng) connecting two manholes."""

    code: str
    manhole1: str
    manhole2: str
    geometry_wkt: Optional[str] = None
    shape: str = SHAPE_CIRCLE            # ACA: A circular, B rectangular, Z other
    diameter: Optional[float] = None     # ACB height/diameter (m)
    width: Optional[float] = None        # width for rectangular (m)
    bob1: Optional[float] = None         # ACR start invert level (m NAP)
    bob2: Optional[float] = None         # ACS end invert level (m NAP)
    length: Optional[float] = None       # geometry length (m)
    material: Optional[str] = None       # ACD
    sewerage_type: Optional[str] = None  # ACJ
    inspection_date: Optional[date] = None
    source_line: Optional[int] = None

    @property
    def is_rectangular(self) -> bool:
        """Return True if the pipe cross-section is rectangular (shape == 'B')."""
        return self.shape == SHAPE_RECTANGULAR


@dataclass
class Observation:
    """A single observation (waarneming, ZC row) within an inspection."""

    object_code: str
    code: str                            # field A (e.g. BCA)
    char1: Optional[str] = None          # B
    char2: Optional[str] = None          # C
    char3: Optional[str] = None          # O
    quant1: Optional[str] = None         # D
    quant2: Optional[str] = None         # E
    remarks: Optional[str] = None        # F
    clock1: Optional[str] = None         # G
    clock2: Optional[str] = None         # H
    distance: Optional[float] = None     # I (length-direction distance, m)
    traject_location: Optional[str] = None  # J
    photo_ref: Optional[str] = None      # M
    video_ref: Optional[str] = None      # N


@dataclass
class Inspection:
    """An inspection of one object (pipe or manhole) with its observations."""

    object_code: str
    object_type: str                     # 'A' pipe, 'C' manhole
    date: Optional[date] = None
    observations: list = field(default_factory=list)
