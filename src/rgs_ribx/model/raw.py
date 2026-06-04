"""Raw (un-integrated) inclination/height measurements for one pipe."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawMeasurements:
    """The measurements of one pipe before height integration.

    ``measurement_type`` is the integration type (``J`` degrees, ``K`` percent,
    ``A``/``AA`` relative, ``B``/absolute). ``reverse`` is True when the survey
    ran from the pipe's manhole2. ``points`` are ``{"dist": float, "value": float}``.
    """

    pipe_code: str
    measurement_type: str
    reverse: bool = False
    points: list = field(default_factory=list)
