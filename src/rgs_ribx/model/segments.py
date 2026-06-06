"""Aggregate a pipe profile (or its BOB line) into segments.

Measured pipes: merge consecutive measurement points into segments of at least
``min_length``. Un-measured pipes: split the straight bob1->bob2 line into
``bob_length`` pieces. Each segment carries van/tot distance, start/end BOB,
highest BOB, mean slope, diameter, measurement count and source.
"""

from __future__ import annotations


def _segment(pipe, d0, d1, b_start, b_end, b_high, n, source):
    length = d1 - d0
    slope = ((b_end - b_start) / length) if length else 0.0
    return {
        "pipe_code": pipe.code,
        "dist_from": d0,
        "dist_to": d1,
        "length": length,
        "bob_start": b_start,
        "bob_end": b_end,
        "bob_highest": b_high,
        "slope_avg": slope,
        "diameter": pipe.diameter,
        "n_measurements": n,
        "source": source,
    }


def build_segments(pipe, profile_points, min_length=1.0, bob_length=5.0):
    """Return a list of segment dicts for one pipe."""
    pts = sorted(profile_points, key=lambda p: p.dist)
    if len(pts) >= 2:
        return _measured_segments(pipe, pts, min_length)
    if pipe.bob1 is not None and pipe.bob2 is not None and pipe.length:
        return _bob_segments(pipe, bob_length)
    return []


def _measured_segments(pipe, pts, min_length):
    segments = []
    start_i = 0
    for i in range(1, len(pts)):
        spanned = pts[i].dist - pts[start_i].dist
        is_last = i == len(pts) - 1
        if spanned >= min_length or is_last:
            window = pts[start_i:i + 1]
            bobs = [p.bob for p in window]
            segments.append(_segment(
                pipe, window[0].dist, window[-1].dist, window[0].bob, window[-1].bob,
                max(bobs), len(window), "measured"))
            start_i = i
    return segments


def _bob_segments(pipe, bob_length):
    segments = []
    length = pipe.length
    d = 0.0
    while d < length - 1e-9:
        d1 = min(d + bob_length, length)
        b0 = pipe.bob1 + (pipe.bob2 - pipe.bob1) * (d / length)
        b1 = pipe.bob1 + (pipe.bob2 - pipe.bob1) * (d1 / length)
        segments.append(_segment(pipe, d, d1, b0, b1, max(b0, b1), 0, "bob"))
        d = d1
    return segments
