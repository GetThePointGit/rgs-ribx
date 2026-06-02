from rgs_ribx.parsing.headers import load_header, header_label


def test_load_header_for_pipe_inspection():
    header = load_header("A")
    assert "AAA" in header
    assert header["AAA"]["naam"] == "Strengreferentie"


def test_header_label_lookup():
    assert header_label("A", "ACB") is not None  # diameter field exists
    assert header_label("C", "CAA") == "Knooppuntreferentie"


def test_unknown_object_type_raises():
    import pytest

    with pytest.raises(KeyError):
        load_header("ZZZ")
