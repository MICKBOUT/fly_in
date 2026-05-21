"""Graph building and routing logic for the Fly-In simulation."""

import heapq

from models import NodeData
from parsing import ParsedData

PathStep = tuple[str, int]
RouteData = tuple[int, list[PathStep]]
RoutedPath = list[PathStep]
State = tuple[str, int]
LinkKey = tuple[str, str]
PathScore = tuple[int, float, int]
QueueItem = tuple[int, int, float, int, str]


class Graph:
    """Initialize a Graph instance from parsed map data.

    Constructs the routing graph by creating nodes from hub data and
    initializing neighbor connections. Validates all hubs and connections,
    ensuring no self-loops, duplicate connections, or references to
    undefined hubs. Handles blocked zones by tracking them separately.

    Args:
        data: Parsed map data containing drone count, start/end hubs,
            hub definitions with coordinates and metadata, and connection
            specifications with capacities.

    Raises:
        ValueError: If a connection references an undefined hub, creates
            a self-loop, is duplicated, or involves blocked zones.
    """

    def __init__(self, data: ParsedData) -> None:
        """Initialize a graph from parsed map data.

        Creates a graph representation of hubs and their connections from
        parsed map data. Sets up nodes with their metadata and validates all
        connections.

        Args:
            data: ParsedData dictionary containing:
                - nb_drones (int): Number of drones
                - start_hub (str): Starting hub identifier
                - end_hub (str): Ending hub identifier
                - hubs (dict): Hub definitions with metadata
                - connections (list): Connection definitions between hubs

        Raises:
            ValueError: If a node in a connection is not defined as a hub, if a
                hub is connected to itself, if a connection is defined multiple
                times, or if a connection involves a blocked zone hub.
        """
        self.nb_drones = data["nb_drones"]
        self.start_hub = data["start_hub"]
        self.end_hub = data["end_hub"]
        self.nodes: dict[str, NodeData] = {
            key: NodeData(
                key,
                value["x"],
                value["y"],
                value["metadata"]["zone"],
                value["metadata"]["color"],
                value["metadata"]["max_drones"],
            )
            for key, value in data["hubs"].items()
        }
        self.neighbor: dict[str, dict[str, int]] = {
            key: {} for key in self.nodes
        }
        blocked_connections: dict[str, set[str]] = {
            key: set() for key in self.nodes
        }

        self.nodes[self.start_hub].max_drones = self.nb_drones
        self.nodes[self.end_hub].max_drones = self.nb_drones

        for connection in data["connections"]:
            left = connection["left"]
            right = connection["right"]
            capacity = connection["max_link_capacity"]

            if left not in self.nodes:
                raise ValueError(f"node '{left}' is not define as hub")
            if right not in self.nodes:
                raise ValueError(f"node '{right}' is not define as hub")
            if left == right:
                raise ValueError(f"'{left}' hub is connected to itself")

            if (
                self.nodes[left].zone == "blocked" or
                self.nodes[right].zone == "blocked"
            ):
                if (
                    right in blocked_connections[left] or
                    left in blocked_connections[right]
                ):
                    raise ValueError(
                        f"connection '{left}-{right}' "
                        "present multiple time in file"
                    )
                blocked_connections[left].add(right)
                blocked_connections[right].add(left)
                continue

            if right in self.neighbor[left] or left in self.neighbor[right]:
                raise ValueError(
                    f"Connection '{left}-{right}' "
                    "present multiple time in file"
                )

            self.neighbor[left][right] = capacity
            self.neighbor[right][left] = capacity

        self.restricted_connections = {}
        for name, node_data in self.nodes.items():
            if node_data.zone == "restricted":
                for neighbor in self.neighbor[name].keys():
                    self.restricted_connections[
                        (name, neighbor)] = self.neighbor[name][neighbor]

    @staticmethod
    def link_key(left: str, right: str) -> LinkKey:
        """Return the normalized key for an undirected link."""
        if left < right:
            return left, right
        return right, left

    def move_cost(self, destination: str) -> int:
        """Return the number of turns needed to enter a node."""
        if self.nodes[destination].zone == "restricted":
            return 2
        return 1

    def priority_bonus(self, node: str) -> int:
        """Return the path bonus granted by a priority node."""
        if self.nodes[node].zone == "priority":
            return 1
        return 0

    def link_is_available(self, left: str, right: str, turn: int) -> bool:
        """Check whether a link still has room on a given turn."""
        link_key = self.link_key(left, right)
        capacity = self.neighbor[left][right]
        current_count = self.link_reservation_table.get((link_key, turn), 0)
        return current_count + 1 <= capacity

    def congestion_cost(self, left: str, right: str, next_turn: int) -> float:
        """Estimate congestion added by using one move."""
        link_key = self.link_key(left, right)
        link_turn = next_turn - self.move_cost(right) + 1
        node_capacity = max(self.nodes[right].max_drones, 1)
        link_capacity = max(self.neighbor[left][right], 1)

        node_load = self.reservation_table.get((right, next_turn), 0)
        link_load = self.link_reservation_table.get((link_key, link_turn), 0)
        return (node_load / node_capacity) + (link_load / link_capacity)

    def movement_penalty(
        self,
        current_state: State,
        parent: dict[State, State | None],
        next_node: str,
    ) -> int:
        """Calculate movement penalty to prefer waiting over useless detours.

        Applies penalties to moves that revisit recent nodes or create cycles,
        encouraging the pathfinding algorithm to wait rather than make wasteful
        detours when the number of turns is equal.

        Args:
            current_state: The current state in the search path.
            parent: A mapping of each state to its parent state in the search
                tree.
            next_node: The identifier of the node to move to.

        Returns:
            An integer penalty score. Returns 0 if current_state has no parent.
            Adds 2 if next_node is the immediately previous node, and adds 1
            if next_node appears anywhere in the ancestor chain.
        """
        previous_state = parent[current_state]
        if previous_state is None:
            return 0

        penalty = 0
        previous_node, _ = previous_state
        if next_node == previous_node:
            penalty += 2

        ancestor: State | None = previous_state
        while ancestor is not None:
            ancestor_node, _ = ancestor
            if ancestor_node == next_node:
                penalty += 1
                break
            ancestor = parent[ancestor]

        return penalty

    def find_path(self) -> RouteData | None:
        """Find one path while respecting current reservations.

        Uses a priority queue-based search algorithm to find an optimal path
        from start_hub to end_hub. The search respects drone capacity
        constraints at nodes and link availability constraints between nodes.

        The algorithm optimizes for multiple criteria in order of preference:
        1. Minimum detour score (path efficiency penalty)
        2. Minimum congestion score (based on reservation density)
        3. Maximum priority bonus (preference for higher priority nodes)

        The search maintains:
        - A visited set to avoid revisiting states
        - A best_score dict to track the best known score for each state
        - A parent dict to reconstruct the path upon reaching the destination

        Returns:
            RouteData | None: A tuple of (turn, path) where turn is the number
                of turns to reach the destination and path is the list of
                states (excluding the start node), or None if no valid path
                exists.
        """
        start_state = (self.start_hub, 0)
        visited: set[State] = set()
        start_priority = self.priority_bonus(self.start_hub)
        queue: list[QueueItem] = [
            (0, 0, 0.0, -start_priority, self.start_hub)
        ]
        best_score: dict[State, PathScore] = {
            start_state: (0, 0.0, start_priority)
        }
        parent: dict[State, State | None] = {
            start_state: None
        }

        while queue:
            (
                turn,
                detour_score,
                congestion_score,
                negative_priority,
                pos,
            ) = heapq.heappop(queue)
            priority_count = -negative_priority
            current_state = (pos, turn)

            best_detour, best_congestion, best_priority = best_score.get(
                current_state,
                (10**9, float("inf"), -1),
            )
            if (
                detour_score > best_detour or (
                    detour_score == best_detour and (
                        congestion_score > best_congestion or (
                            congestion_score == best_congestion and
                            priority_count < best_priority
                        )
                    )
                )
            ):
                continue
            if current_state in visited:
                continue
            visited.add(current_state)

            if pos == self.end_hub:
                path = []
                state: State | None = current_state
                while state is not None:
                    path.append(state)
                    state = parent[state]
                path.reverse()
                return turn, path[1:]

            for next_node in self.neighbor[pos]:
                move_cost = self.move_cost(next_node)
                next_turn = turn + move_cost
                link_turn = turn + 1
                destination_count = self.reservation_table.get(
                    (next_node, next_turn), 0
                )
                if destination_count + 1 > self.nodes[next_node].max_drones:
                    continue
                if not self.link_is_available(pos, next_node, link_turn):
                    continue

                state = (next_node, next_turn)
                next_detour = (
                    detour_score +
                    self.movement_penalty(current_state, parent, next_node)
                )
                next_congestion = (
                    congestion_score +
                    self.congestion_cost(pos, next_node, next_turn)
                )
                next_priority = priority_count + self.priority_bonus(next_node)
                (
                    known_detour,
                    known_congestion,
                    known_priority,
                ) = best_score.get(state, (10**9, float("inf"), -1))
                if (
                    next_detour > known_detour or (
                        next_detour == known_detour and (
                            next_congestion > known_congestion or (
                                next_congestion == known_congestion and
                                next_priority <= known_priority
                            )
                        )
                    )
                ):
                    continue

                best_score[state] = (
                    next_detour, next_congestion, next_priority)
                parent[state] = current_state
                heapq.heappush(queue, (
                    next_turn, next_detour,
                    next_congestion, -next_priority, next_node,
                ),)

            wait_state = (pos, turn + 1)
            wait_count = self.reservation_table.get(wait_state, 0)
            if wait_count + 1 <= self.nodes[pos].max_drones:
                wait_congestion = (congestion_score + (
                        self.reservation_table.get(wait_state, 0) /
                        max(self.nodes[pos].max_drones, 1)
                    )
                )
                (known_detour, known_congestion, known_priority
                 ) = best_score.get(wait_state, (10**9, float("inf"), -1))
                if (
                    detour_score < known_detour or (
                        detour_score == known_detour and (
                            wait_congestion < known_congestion or (
                                wait_congestion == known_congestion and
                                priority_count > known_priority
                            )
                        )
                    )
                ):
                    best_score[wait_state] = (
                        detour_score, wait_congestion, priority_count,
                    )
                    parent[wait_state] = current_state
                    heapq.heappush(queue, (
                        turn + 1, detour_score, wait_congestion,
                        -priority_count, pos,),
                    )

        return None

    def reserve_path(self, path: RoutedPath) -> None:
        """Reserve nodes and links used by a computed path.

        Args:
            path (RoutedPath): The computed path containing a sequence of
                (node, turn) tuples to be reserved in the network.

        Returns:
            None

        Raises:
            None

        Note:
            This method updates two reservation tables:
            - reservation_table: Tracks reservation count for each node state
            - link_reservation_table: Tracks reservation count for each link
                state

            The path is processed starting from self.start_hub, and consecutive
                state pairs are used to identify links between nodes.
        """
        states = [(self.start_hub, 0)] + path

        for state in states:
            self.reservation_table[state] = (
                self.reservation_table.get(state, 0) + 1
            )

        for (left, left_turn), (right, _) in zip(states, states[1:]):
            if left == right:
                continue
            link_key = self.link_key(left, right)
            link_turn = left_turn + 1
            link_state = (link_key, link_turn)
            self.link_reservation_table[link_state] = (
                self.link_reservation_table.get(link_state, 0) + 1
            )

    def routing(self) -> list[RoutedPath]:
        """Compute paths for every drone in the simulation."""
        self.reservation_table: dict[tuple[str, int], int] = {}
        self.link_reservation_table: dict[tuple[LinkKey, int], int] = {}
        paths: list[RoutedPath] = []

        for _ in range(self.nb_drones):
            path = self.find_path()
            if path is None:
                raise Exception("No solution Found")
            self.reserve_path(path[1])
            paths.append(path[1])

        return paths

    def print_log(self, paths: list[RoutedPath]) -> int:
        """
        Print the per-turn movement log of drones and return the total number
            of turns.

        This method processes the movement paths of drones, logs their
            movements per turn, and prints the results. It also tracks the
            number of drones connected to each node at each turn.

        Args:
            paths (list[RoutedPath]): A list of paths for each drone, where
                each path is a list of tuples containing a node and the
                corresponding turn.

        Returns:
            int: The total number of turns taken for all drones to reach the
                exit.

        Raises:
            ValueError: If the paths list is empty or if the turns are invalid.
        """
        turns: list[list[str]] = [[] for _ in range(paths[-1][-1][1])]
        hub_connection: dict[tuple[str, int] | tuple[str, str, int], int] = {
            (self.start_hub, 0): self.nb_drones}

        for drone_id, path_data in enumerate(paths):
            pos = self.start_hub
            pos_turn = 0
            for node, turn in path_data:
                print((pos, node, turn))
                hub_connection[(node, turn)] = hub_connection.get(
                    (node, turn), 0) + 1
                if node == pos:  # no move
                    pos_turn = turn
                    continue
                if self.move_cost(node) == 2:
                    turns[pos_turn].append(f"D{drone_id + 1}-{pos}-{node}")
                    n1, n2 = self.link_key(pos, node)
                    hub_connection[(n1, n2, turn - 1)] = hub_connection.get(
                        (n1, n2, turn - 1), 0) + 1
                pos = node
                pos_turn = turn
                turns[turn - 1].append(f"D{drone_id + 1}-{pos}")

        for turn_list in turns:
            joined_turn = " ".join(turn_list)
            if joined_turn:
                print(joined_turn)

        nb_turn = len(turns)
        print(f"all drone(s) found the exit in {nb_turn} turn(s)")

        return nb_turn
