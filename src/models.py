class NodeData:
    def __init__(self, name: str, x: int, y: int, zone: str,
                 color: str | None, max_drones: int):
        self.name = name
        self.x = x
        self.y = y
        self.zone = zone
        self.color = color
        self.max_drones = max_drones
