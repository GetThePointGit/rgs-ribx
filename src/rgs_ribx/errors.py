"""Error/warning codes and the tabular collector used by the parser.

Codes mirror drainworks' import_new/error_codes.py so the ported parser
works unchanged. Only the XML-parsing codes are needed in this library.
"""

import pandas as pd

# --- XML parsing (ribx_to_pandas) ---
XML_FILE_NOT_FOUND = 1
XML_SYNTAX_ERROR = 2
XML_WRONG_ROOT = 3
XML_MISSING_ZA = 4
XML_UNKNOWN_OBJECT_TYPE = 5
XML_NO_OBJECTS = 6

ERROR_WARNING_COLUMNS = ["level", "line_nr", "value", "code", "message"]


def create_error_warning_df(errors: list[dict]) -> pd.DataFrame:
    """Build a DataFrame of errors/warnings with a fixed column order.

    Parameters
    ----------
    errors : list of dict
        Each dict has keys ``level, line_nr, value, code, message``.

    Returns
    -------
    pandas.DataFrame
        One row per error, columns in :data:`ERROR_WARNING_COLUMNS` order.
    """
    if not errors:
        return pd.DataFrame(columns=ERROR_WARNING_COLUMNS)
    return pd.DataFrame(errors, columns=ERROR_WARNING_COLUMNS)
