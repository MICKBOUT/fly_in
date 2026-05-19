from graph import Graph


def connected_graph(graph: Graph) -> bool:
    """Determine if a path exists from start_hub to end_hub in the graph.

    Uses depth-first search to traverse the graph from the start node,
    tracking visited nodes to avoid cycles and redundant exploration.

    Args:
        graph: A Graph object containing start_hub, end_hub, and a neighbor
            mapping that represents the graph structure.

    Returns:
        True if a path exists from start_hub to end_hub, False otherwise.
    """
    stack = [graph.start_hub]
    seen = set()

    while stack:
        node = stack.pop()
        if node == graph.end_hub:
            return True
        for neighbor in graph.neighbor[node].keys():
            if neighbor not in seen:
                stack.append(neighbor)
                seen.add(neighbor)

    return False
