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
    """Build the routing graph and compute drone paths."""

    def __init__(self, data: ParsedData) -> None:
        """Create the graph from parsed map data."""
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

    def link_key(self, left: str, right: str) -> LinkKey:
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
        """Score a move so waiting beats useless detours on equal turns."""
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
        """Find one path while respecting current reservations."""
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
                detour_score > best_detour or
                (
                    detour_score == best_detour and
                    (
                        congestion_score > best_congestion or
                        (
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
                    next_detour > known_detour or
                    (
                        next_detour == known_detour and
                        (
                            next_congestion > known_congestion or
                            (
                                next_congestion == known_congestion and
                                next_priority <= known_priority
                            )
                        )
                    )
                ):
                    continue

                best_score[state] = (
                    next_detour,
                    next_congestion,
                    next_priority,
                )
                parent[state] = current_state
                heapq.heappush(
                    queue,
                    (
                        next_turn,
                        next_detour,
                        next_congestion,
                        -next_priority,
                        next_node,
                    ),
                )

            wait_state = (pos, turn + 1)
            wait_count = self.reservation_table.get(wait_state, 0)
            if wait_count + 1 <= self.nodes[pos].max_drones:
                wait_congestion = (
                    congestion_score +
                    (
                        self.reservation_table.get(wait_state, 0) /
                        max(self.nodes[pos].max_drones, 1)
                    )
                )
                (
                    known_detour,
                    known_congestion,
                    known_priority,
                ) = best_score.get(wait_state, (10**9, float("inf"), -1))
                if (
                    detour_score < known_detour or
                    (
                        detour_score == known_detour and
                        (
                            wait_congestion < known_congestion or
                            (
                                wait_congestion == known_congestion and
                                priority_count > known_priority
                            )
                        )
                    )
                ):
                    best_score[wait_state] = (
                        detour_score,
                        wait_congestion,
                        priority_count,
                    )
                    parent[wait_state] = current_state
                    heapq.heappush(
                        queue,
                        (
                            turn + 1,
                            detour_score,
                            wait_congestion,
                            -priority_count,
                            pos,
                        ),
                    )

        return None

    def reserve_path(self, path: RoutedPath) -> None:
        """Reserve nodes and links used by a computed path."""
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
        """Print the per-turn movement log and return its length."""
        turns: list[list[str]] = [[] for _ in range(paths[-1][-1][1])]

        for drone_id, path_data in enumerate(paths):
            pos = self.start_hub
            pos_turn = 0
            for node, turn in path_data:
                if node == pos:
                    pos_turn = turn
                    continue
                if self.move_cost(node) == 2:
                    connection = f"{pos}-{node}"
                    turns[pos_turn].append(f"D{drone_id + 1}-{connection}")
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
