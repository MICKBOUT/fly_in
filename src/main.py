import heapq
from typing import TypedDict

from parsing import ParsedData, parsing_file


class Drone:
    def __init__(self, start: str, drone_id: int) -> None:
        self.id: int = drone_id
        self.pos: str = start


class NodeData(TypedDict):
    name: str
    x: int
    y: int
    zone: str
    color: str | None
    max_drones: float
    drone_count: int


class LinkData(TypedDict):
    capacity: int
    drone_count: int


Movement = tuple[str, str]
RouteData = tuple[int, list[str]]


class Graph:
    def __init__(self, data: ParsedData) -> None:
        self.nb_drones: int = data["nb_drones"]
        self.start_hub: str = data["start_hub"]
        self.end_hub: str = data["end_hub"]
        self.nodes: dict[str, NodeData] = {
            key: {
                "name": key,
                "x": value["x"],
                "y": value["y"],
                "zone": value["metadata"]["zone"],
                "color": value["metadata"]["color"],
                "max_drones": float(value["metadata"]["max_drones"]),
                "drone_count": 0}
            for key, value in data["hubs"].items()
        }
        self.neighbor: dict[str, dict[str, LinkData]] = {
            key: {} for key in self.nodes
        }
        self.block_conection: dict[str, set[str]] = {
            key: set() for key in self.nodes
        }
        self.movments: list[Movement] = []

        self.nodes[self.start_hub]["max_drones"] = float("inf")
        self.nodes[self.end_hub]["max_drones"] = float("inf")
        self.nodes[self.start_hub]["drone_count"] = self.nb_drones

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
                self.nodes[left]["zone"] == "blocked" or
                self.nodes[right]["zone"] == "blocked"
            ):
                if (
                    right in self.block_conection[left]
                    or left in self.block_conection[right]
                ):
                    raise ValueError(
                        f"connection '{left}-{right}' "
                        "present multiple time in file"
                    )
                self.block_conection[left].add(right)
                self.block_conection[right].add(left)
                continue

            if right in self.neighbor[left] or left in self.neighbor[right]:
                raise ValueError(
                    f"Connection '{left}-{right}' "
                    "present multiple time in file"
                )

            self.neighbor[left][right] = {
                "capacity": capacity, "drone_count": 0}
            self.neighbor[right][left] = {
                "capacity": capacity, "drone_count": 0}

        self.drones: list[Drone] = [
            Drone(self.start_hub, index + 1) for index in range(self.nb_drones)
        ]

    def can_access_node(self, next_node: str) -> bool:
        drone_data = self.nodes[next_node]
        return drone_data["drone_count"] + 1 <= drone_data["max_drones"]

    def can_access_link(self, walking: Movement) -> bool:
        node_start, node_end = walking
        drone_data = self.neighbor[node_start][node_end]
        return drone_data["drone_count"] + 1 <= drone_data["capacity"]

    def simulate_drone(self, drone: Drone) -> str:
        queue: list[tuple[int, str]] = [(0, drone.pos)]
        routing: dict[str, RouteData] = {drone.pos: (0, [])}

        while queue:
            distance, pos = heapq.heappop(queue)
            next_distance = distance + 1

            for next_node in self.neighbor[pos]:
                current_route = routing.get(next_node)
                _, current_path = routing[pos]

                if current_route is None or next_distance < current_route[0]:
                    routing[next_node] = (
                        next_distance,
                        current_path + [next_node]
                    )
                    heapq.heappush(queue, (next_distance, next_node))

        path_to_end = routing.get(self.end_hub)
        if path_to_end is None or not path_to_end[1]:
            return ""

        next_node = path_to_end[1][0]
        walking: Movement = (drone.pos, next_node)
        if self.can_access_node(next_node) and self.can_access_link(walking):
            self.nodes[drone.pos]["drone_count"] -= 1
            self.nodes[next_node]["drone_count"] += 1
            self.neighbor[drone.pos][next_node]["drone_count"] += 1
            self.neighbor[next_node][drone.pos]["drone_count"] += 1
            self.movments.append(walking)
            drone.pos = next_node
            return f"D{drone.id}-{drone.pos}"

        return ""

    def simulate_drones(self) -> None:
        turn = [move for drone in self.drones
                if (move := self.simulate_drone(drone))]
        self.drones = [
            drone for drone in self.drones if drone.pos != self.end_hub
        ]
        output = " ".join(turn)
        if output:
            print(output)

    def move_drone(self) -> None:
        for node_1, node_2 in self.movments:
            self.neighbor[node_1][node_2]["drone_count"] -= 1
            self.neighbor[node_2][node_1]["drone_count"] -= 1
        self.movments.clear()


def main() -> None:
    try:
        data = parsing_file()
    except Exception as error:
        print("Error:", error)
        return

    graph = Graph(data)
    while graph.drones:
        graph.simulate_drones()
        graph.move_drone()


if __name__ == "__main__":
    print("=" * 20)
    main()
    print("=" * 20)
