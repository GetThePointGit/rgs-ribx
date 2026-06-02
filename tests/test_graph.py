import pytest

from rgs_ribx.lost_capacity.graph import Graph


def test_add_node_stores_attributes():
    g = Graph()
    g.add_node("a", bob=-2.0, waterlevel=None)
    assert g.nodes["a"]["bob"] == -2.0
    assert g.nodes["a"]["waterlevel"] is None


def test_add_edge_is_undirected():
    g = Graph()
    g.add_node("a")
    g.add_node("b")
    g.add_edge("a", "b")
    assert "b" in g["a"]
    assert "a" in g["b"]


def test_neighbors_sorted_access():
    g = Graph()
    for n in ("a", "b", "c"):
        g.add_node(n)
    g.add_edge("a", "c")
    g.add_edge("a", "b")
    assert sorted(g["a"]) == ["b", "c"]


def test_add_edge_unknown_node_raises():
    g = Graph()
    g.add_node("a")
    with pytest.raises(KeyError):
        g.add_edge("a", "missing")
