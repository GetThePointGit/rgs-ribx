import pandas as pd

from rgs_ribx.errors import (
    XML_FILE_NOT_FOUND,
    XML_SYNTAX_ERROR,
    create_error_warning_df,
)


def test_error_codes_are_distinct_ints():
    assert isinstance(XML_FILE_NOT_FOUND, int)
    assert XML_FILE_NOT_FOUND != XML_SYNTAX_ERROR


def test_create_error_warning_df_has_expected_columns():
    df = create_error_warning_df(
        [{"level": "error", "line_nr": 3, "value": "x", "code": XML_SYNTAX_ERROR, "message": "boom"}]
    )
    assert list(df.columns) == ["level", "line_nr", "value", "code", "message"]
    assert len(df) == 1
    assert df.iloc[0]["code"] == XML_SYNTAX_ERROR


def test_create_error_warning_df_empty():
    df = create_error_warning_df([])
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["level", "line_nr", "value", "code", "message"]
    assert len(df) == 0
