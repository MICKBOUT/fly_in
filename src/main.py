import heapq

from parsing import ParsedData, parsing_file
from display import Display
from models import NodeData

PathStep = tuple[str, int]
RouteData = tuple[int, list[PathStep]]
RoutedPath = list[PathStep]
State = tuple[str, int]
LinkKey = tuple[str, str]
QueueItem = tuple[int, int, str]


class Graph:
    def __init__(self, data: ParsedData) -> None:
        self.nb_drones: int = data["nb_drones"]
        self.start_hub: str = data["start_hub"]
        self.end_hub: str = data["end_hub"]
        self.nodes: dict[str, NodeData] = {
            key: NodeData(
                key,
                value["x"],
                value["y"],
                value["metadata"]["zone"],
                value["metadata"].get("color", ""),
                value["metadata"]["max_drones"]
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
                    right in blocked_connections[left]
                    or left in blocked_connections[right]
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
        if left < right:
            return left, right
        return right, left

    def move_cost(self, destination: str) -> int:
        if self.nodes[destination].zone == "restricted":
            return 2
        return 1

    def priority_bonus(self, node: str) -> int:
        if self.nodes[node].zone == "priority":
            return 1
        return 0

    def link_is_available(self, left: str, right: str, turn: int) -> bool:
        link_key = self.link_key(left, right)
        capacity = self.neighbor[left][right]
        current_count = self.link_reservation_table.get((link_key, turn), 0)
        return current_count + 1 <= capacity

    def find_path(self) -> RouteData | None:
        start_state = (self.start_hub, 0)
        visited: set[State] = set()
        start_priority = self.priority_bonus(self.start_hub)
        queue: list[QueueItem] = [(0, -start_priority, self.start_hub)]
        best_priority: dict[State, int] = {
            start_state: start_priority
        }
        parent: dict[State, State | None] = {
            start_state: None
        }

        while queue:
            turn, negative_priority, pos = heapq.heappop(queue)
            priority_count = -negative_priority
            current_state = (pos, turn)

            if priority_count < best_priority.get(current_state, -1):
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

            # option move to a neighbor
            for next_node in self.neighbor[pos]:

                move_cost = self.move_cost(next_node)
                next_turn = turn + move_cost
                link_turn = turn + 1
                destination_count = self.reservation_table.get(
                    (next_node, next_turn), 0
                )
                if (
                    destination_count + 1
                    > self.nodes[next_node].max_drones
                ):
                    continue
                if not self.link_is_available(pos, next_node, link_turn):
                    continue
                state = (next_node, next_turn)
                next_priority = (
                    priority_count + self.priority_bonus(next_node)
                )
                known_priority = best_priority.get(state, -1)

                if next_priority <= known_priority:
                    continue

                best_priority[state] = next_priority
                parent[state] = current_state
                heapq.heappush(queue, (next_turn, -next_priority, next_node))

            # wait on the current node
            wait_state = (pos, turn + 1)
            wait_count = self.reservation_table.get(wait_state, 0)
            if wait_count + 1 <= self.nodes[pos].max_drones:
                known_priority = best_priority.get(wait_state, -1)
                if priority_count > known_priority:
                    best_priority[wait_state] = priority_count
                    parent[wait_state] = current_state
                    heapq.heappush(queue, (turn + 1, -priority_count, pos))

        return None

    def reserve_path(self, path: RoutedPath) -> None:

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
        # change -1 -1 -1 to max (paths[x][-1][1])
        turns: list[list[str]] = [[] for _ in range(paths[-1][-1][1])]

        for drone_id, path_data in enumerate(paths):
            pos = self.start_hub
            pos_turn = 0
            for node_data in path_data:
                node, turn = node_data
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
            s = " ".join(turn_list)
            if s:
                print(s)
        nb_turn = len(turns)
        print(f"all drone(s) found the exit in {nb_turn} turn(s)")
        return nb_turn


def main() -> None:
    try:
        data = parsing_file("maps/challenger/01_the_impossible_dream.txt")
        # data = parsing_file("maps/hard/03_ultimate_challenge.txt")
        # data = parsing_file()
    except Exception as error:
        print("Error:", error)
        return

    graph = Graph(data)
    paths = graph.routing()
    nb_turn = graph.print_log(paths)

    display = Display(
        graph.nodes, data["connections"], paths, graph.start_hub, nb_turn)
    display.main()


if __name__ == "__main__":
    print("=" * 20)
    main()
    print("=" * 20)
