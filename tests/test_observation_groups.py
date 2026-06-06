"""Grouping observations per object (the per-pipe perf refactor in build.py)."""

import pandas as pd

from rgs_ribx.model.build import _getd, _observation_groups


def test_groups_rows_by_object_idx():
    df = pd.DataFrame([
        {"_object_idx": 0, "A": "BXA", "I": 0.0},
        {"_object_idx": 0, "A": "BXA", "I": 1.0},
        {"_object_idx": 1, "A": "BCA", "I": 2.0},
        {"_object_idx": 2, "A": "BXA", "I": 3.0},
    ])
    groups = _observation_groups(df)
    assert set(groups) == {0, 1, 2}
    assert len(groups[0]) == 2 and len(groups[1]) == 1 and len(groups[2]) == 1
    # rows are plain dicts, retrievable via _getd
    assert _getd(groups[1][0], "A") == "BCA"
    # an object with no observations simply isn't a key
    assert groups.get(5) is None


def test_int_lookup_matches_float_object_idx_key():
    # If the column is float64 (e.g. due to NaNs elsewhere), an int lookup must still hit.
    df = pd.DataFrame([{"_object_idx": 0.0, "A": "BXA"}, {"_object_idx": 1.0, "A": "BXA"}])
    groups = _observation_groups(df)
    assert groups.get(0) is not None and groups.get(1) is not None


def test_drops_rows_without_object_idx():
    df = pd.DataFrame([
        {"_object_idx": 0, "A": "BXA"},
        {"_object_idx": None, "A": "BXA"},
    ])
    groups = _observation_groups(df)
    assert set(groups) == {0}


def test_empty_or_none_frame():
    assert _observation_groups(None) == {}
    assert _observation_groups(pd.DataFrame()) == {}
