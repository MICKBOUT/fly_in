from dataclasses import dataclass


@dataclass
class NodeData:
    name: str
    x: int
    y: int
    zone: str
    color: str | None
    max_drones: int
