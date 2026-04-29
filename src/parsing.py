import re
from typing import TypedDict


class MetadataDict(TypedDict):
    zone: str
    color: str | None
    max_drones: int


class HubDict(TypedDict):
    name: str
    x: int
    y: int
    metadata: MetadataDict


class ConnectionDict(TypedDict):
    left: str
    right: str
    max_link_capacity: int


class ParsedData(TypedDict):
    nb_drones: int
    start_hub: str
    end_hub: str
    hubs: dict[str, HubDict]
    connections: list[ConnectionDict]


def read_metadata_connection(metadata_str: str | None) -> int:
    metadata_pattern = re.compile(r"max_link_capacity=(?P<value>\d+)")
    if metadata_str is None:
        return 1

    match = metadata_pattern.search(metadata_str)
    return int(match.group("value")) if match else 1


def read_metadata_node(metadata_str: str | None) -> MetadataDict:
    metadata_pattern = re.compile(
        r"(?P<key>zone|color|max_drones)=(?P<value>\w+)"
    )
    result: MetadataDict = {
        "zone": "normal",
        "color": None,
        "max_drones": 1,
    }
    if metadata_str is None:
        return result

    for match in metadata_pattern.finditer(metadata_str):
        key = match.group("key")
        value = match.group("value")

        if key == "zone":
            result["zone"] = value
        elif key == "color":
            result["color"] = value
        else:
            result["max_drones"] = int(value)

    return result


def parsing_file(path: str = "maps/easy/01_linear_path.txt") -> ParsedData:
    nb_drones_pattern = re.compile(r"^nb_drones: (?P<nb_drones>\d+)")
    hub_pattern = re.compile(
        r"^(?P<type>start_hub|end_hub|hub): (?P<name>\w+) (?P<x>-?\d+) "
        r"(?P<y>-?\d+)(?:\s+\[(?P<metadata>[^\]]*)\])?"
    )
    connection_pattern = re.compile(
        r"^connection: (?P<left>\w+)-(?P<right>\w+)"
        r"(?:\s+\[(?P<metadata>[^\]]*)\])?"
    )

    start_hub: str | None = None
    end_hub: str | None = None
    hubs: dict[str, HubDict] = {}
    connections: list[ConnectionDict] = []

    with open(path, encoding="utf-8") as file:
        lines = [
            line
            for line in file.read().splitlines()
            if (not line.startswith("#")) and line.strip()
        ]

    if not lines:
        raise ValueError("File empty")

    match = nb_drones_pattern.search(lines[0])
    if match is None:
        raise ValueError("nb_drones not found at the first line of the file.")
    nb_drones = int(match.group("nb_drones"))

    for line in lines[1:]:
        if match := hub_pattern.search(line):
            data = match.groupdict()
            hub: HubDict = {
                "name": data["name"],
                "x": int(data["x"]),
                "y": int(data["y"]),
                "metadata": read_metadata_node(data["metadata"]),
            }
            hubs[data["name"]] = hub

            if data["type"] == "start_hub":
                if start_hub is not None:
                    raise ValueError("start_hub defined twice in the file")
                start_hub = data["name"]
            elif data["type"] == "end_hub":
                if end_hub is not None:
                    raise ValueError("end_hub defined twice in the file")
                end_hub = data["name"]
        elif match := connection_pattern.search(line):
            data = match.groupdict()
            connections.append(
                {
                    "left": data["left"],
                    "right": data["right"],
                    "max_link_capacity": read_metadata_connection(
                        data["metadata"]
                    ),
                }
            )
        else:
            raise ValueError(f"Line '{line}' not used")

    if start_hub is None:
        raise ValueError("start_hub not found in the file")
    if end_hub is None:
        raise ValueError("end_hub not found in the file")

    return {
        "nb_drones": nb_drones,
        "start_hub": start_hub,
        "end_hub": end_hub,
        "hubs": hubs,
        "connections": connections,
    }
