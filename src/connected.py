from graph import Graph


def connected_graph(graph: Graph) -> bool:
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
