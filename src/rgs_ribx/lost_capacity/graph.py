"""A tiny undirected graph with per-node attributes.

Only the operations used by the lost-capacity flood-fill are implemented,
so we avoid a networkx dependency (not bundled with QGIS). API mirrors the
networkx subset used: ``add_node(node, **attrs)``, ``add_edge(a, b)``,
``g.nodes[node]`` (attribute dict), ``g[node]`` (neighbor set).
"""


class Graph:
    """Undirected graph keyed by hashable node ids (e.g. tuples)."""

    def __init__(self) -> None:
        self.nodes: dict = {}       # node -> attribute dict
        self._adj: dict = {}        # node -> set of neighbor nodes

    def add_node(self, node, **attrs) -> None:
        """Add a node (or update its attributes if it already exists)."""
        if node not in self.nodes:
            self.nodes[node] = {}
            self._adj[node] = set()
        self.nodes[node].update(attrs)

    def add_edge(self, a, b) -> None:
        """Add an undirected edge between two existing nodes."""
        if a not in self.nodes:
            raise KeyError(a)
        if b not in self.nodes:
            raise KeyError(b)
        self._adj[a].add(b)
        self._adj[b].add(a)

    def __getitem__(self, node):
        """Return the set of neighbors of ``node`` (mirrors networkx ``G[node]``)."""
        return self._adj[node]

    def neighbors(self, node):
        return self._adj[node]

    def __contains__(self, node) -> bool:
        return node in self.nodes
