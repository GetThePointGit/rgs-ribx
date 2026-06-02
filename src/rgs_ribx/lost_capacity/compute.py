"""Lost-capacity (verloren berging) computation.

Ported from lizard-progress src/sewer/lost_capacity.py, replacing networkx
with rgs_ribx.lost_capacity.graph.Graph and Django models with plain
entities + MeasurementPoint objects.
"""

from collections import defaultdict
from heapq import heappop, heappush
from itertools import chain

from rgs_ribx.lost_capacity.graph import Graph


def compute_lost_capacity(manholes: dict, pipes: dict, profiles: dict) -> None:
    """Annotate each MeasurementPoint in ``profiles`` with water_level + flooded_pct.

    Parameters
    ----------
    manholes : dict[str, Manhole]
    pipes : dict[str, Pipe]
    profiles : dict[str, list[MeasurementPoint]]
        Interior measurement points per pipe code (ordered or not).
    """
    graph, sink_node = create_graph(manholes, pipes, profiles)
    if graph is None:
        return
    compute_water_level(graph, sink_node)
    add_lost_capacity(profiles, pipes, graph)


def get_manhole_bobs(pipes: dict) -> dict:
    """Return {manhole_code: lowest connected bob}."""
    manhole_bobs = defaultdict(list)
    for pipe in pipes.values():
        if pipe.bob1 is not None:
            manhole_bobs[pipe.manhole1].append(pipe.bob1)
        if pipe.bob2 is not None:
            manhole_bobs[pipe.manhole2].append(pipe.bob2)
    return {code: min(bobs) for code, bobs in manhole_bobs.items() if bobs}


def create_graph(manholes: dict, pipes: dict, profiles: dict):
    """Build the graph of puts, pipe-ends, and measurement points."""
    graph = Graph()
    manhole_bobs = get_manhole_bobs(pipes)

    for pipe_code, pipe in pipes.items():
        if pipe.bob1 is None or pipe.bob2 is None:
            continue
        m1, m2 = pipe.manhole1, pipe.manhole2
        interior = sorted(profiles.get(pipe_code, []), key=lambda p: p.dist)

        previous = None
        for location, bob in chain(
            [(("put", m1), manhole_bobs.get(m1, pipe.bob1)),
             (("sewer_end", pipe_code, "1"), pipe.bob1)],
            ((("measurement", pipe_code, mp.dist), mp.bob) for mp in interior),
            [(("sewer_end", pipe_code, "2"), pipe.bob2),
             (("put", m2), manhole_bobs.get(m2, pipe.bob2))],
        ):
            graph.add_node(location, bob=bob, waterlevel=None)
            if previous is not None:
                graph.add_edge(previous, location)
            previous = location

    sink_ids = [code for code, m in manholes.items() if getattr(m, "is_sink", False)]
    sink_ids = [s for s in sink_ids if ("put", s) in graph]
    if not sink_ids:
        return None, None
    if len(sink_ids) == 1:
        sink_id = sink_ids[0]
    else:
        sink_id = min(sink_ids, key=lambda s: graph.nodes[("put", s)]["bob"])
        for higher in sink_ids:
            if higher == sink_id:
                continue
            graph.add_edge(("put", sink_id), ("put", higher))
    return graph, ("put", sink_id)


def compute_water_level(graph: Graph, sink_node) -> None:
    """Flood-fill water levels upward from the sink (Mario Frasca's algorithm)."""
    todo = []
    done = set()
    heappush(todo, (graph.nodes[sink_node]["bob"], sink_node))

    while todo:
        water_level, current_node = heappop(todo)

        def under_water_condition(parent, child):
            return graph.nodes[child]["bob"] < water_level

        under_water_list, shore_node_pairs = neighbouring_nodes_satisfying_condition(
            graph, current_node, done, under_water_condition
        )
        done = done.union(under_water_list)
        for node in under_water_list:
            graph.nodes[node]["waterlevel"] = water_level

        for _shore_from, shore_to in shore_node_pairs:
            def not_going_down_condition(parent, child):
                return graph.nodes[parent]["bob"] <= graph.nodes[child]["bob"]

            going_up_list, peak_node_pairs = neighbouring_nodes_satisfying_condition(
                graph, shore_to, done, not_going_down_condition
            )
            done = done.union(going_up_list)
            for node in going_up_list:
                graph.nodes[node]["waterlevel"] = graph.nodes[node]["bob"]
            for peak_from, peak_to in peak_node_pairs:
                graph.nodes[peak_from]["waterlevel"] = graph.nodes[peak_from]["bob"]
                heappush(todo, (graph.nodes[peak_from]["bob"], peak_to))


def neighbouring_nodes_satisfying_condition(graph: Graph, start, visited, condition):
    """DFS pre-order returning (satisfied_nodes, border_edges).

    Border edges are (parent, child) pairs where the condition failed and
    ``child`` is not otherwise satisfied.
    """
    visited = set(visited)
    satisfied = []
    border = []
    stack = [(start, iter([start]))]

    while stack:
        parent, children = stack.pop()
        for child in children:
            if child in visited:
                continue
            if condition(parent, child):
                visited.add(child)
                satisfied.append(child)
                stack.append((child, iter(sorted(graph[child]))))
            else:
                border.append((parent, child))
    satisfied_set = set(satisfied)
    return satisfied, [(p, c) for p, c in border if c not in satisfied_set]


def add_lost_capacity(profiles: dict, pipes: dict, graph: Graph) -> None:
    """Assign water levels + flooded_pct to each interior measurement point."""
    for pipe_code, measurements in profiles.items():
        pipe = pipes[pipe_code]
        for mp in measurements:
            node = ("measurement", pipe_code, mp.dist)
            if node in graph:
                mp.set_water_level(graph.nodes[node]["waterlevel"])
            else:
                mp.set_water_level(None)
            mp.compute_flooded_pct(is_rectangular=pipe.is_rectangular)
