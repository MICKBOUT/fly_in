import re
from typing import TypedDict

VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
NAME_PATTERN = r"[^\s\-\[\]]+"
METADATA_VALUE_PATTERN = r"[^\s\]]+"


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


def parse_error(line_number: int, line: str, message: str) -> ValueError:
    return ValueError(f"line {line_number}: {message}: {line}")


def read_metadata_connection(metadata_str: str | None) -> int:
    metadata_pattern = re.compile(r"max_link_capacity=(?P<value>\d+)")
    if metadata_str is None:
        return 1

    match = metadata_pattern.search(metadata_str)
    if match is None:
        return 1

    capacity = int(match.group("value"))
    if capacity <= 0:
        raise ValueError("max_link_capacity must be a positive integer")
    return capacity


def read_metadata_node(metadata_str: str | None) -> MetadataDict:
    metadata_pattern = re.compile(
        r"(?P<key>zone|color|max_drones)="
        rf"(?P<value>{METADATA_VALUE_PATTERN})"
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
            if value not in VALID_ZONE_TYPES:
                raise ValueError(f"invalid zone type '{value}'")
            result["zone"] = value
        elif key == "color":
            result["color"] = value
        else:
            max_drones = int(value)
            if max_drones <= 0:
                raise ValueError("max_drones must be a positive integer")
            result["max_drones"] = max_drones

    return result


def parsing_file(path: str = "maps/easy/01_linear_path.txt") -> ParsedData:
    nb_drones_pattern = re.compile(r"^nb_drones: (?P<nb_drones>\d+)$")
    hub_pattern = re.compile(
        rf"^(?P<type>start_hub|end_hub|hub): (?P<name>{NAME_PATTERN}) "
        r"(?P<x>-?\d+) (?P<y>-?\d+)(?:\s+\[(?P<metadata>[^\]]*)\])?$"
    )
    connection_pattern = re.compile(
        rf"^connection: (?P<left>{NAME_PATTERN})-(?P<right>{NAME_PATTERN})"
        r"(?:\s+\[(?P<metadata>[^\]]*)\])?$"
    )

    start_hub: str | None = None
    end_hub: str | None = None
    hubs: dict[str, HubDict] = {}
    connections: list[ConnectionDict] = []
    seen_connections: set[tuple[str, str]] = set()

    with open(path, encoding="utf-8") as file:
        lines = [
            (line_number, line.strip())
            for line_number, line in enumerate(
                file.read().splitlines(),
                start=1,
            )
            if (not line.startswith("#")) and line.strip()
        ]

    if not lines:
        raise ValueError("file is empty")

    first_line_number, first_line = lines[0]
    match = nb_drones_pattern.search(first_line)
    if match is None:
        raise parse_error(
            first_line_number,
            first_line,
            "expected nb_drones on the first line",
        )
    nb_drones = int(match.group("nb_drones"))

    for line_number, line in lines[1:]:
        if match := hub_pattern.search(line):
            data = match.groupdict()
            hub_name = data["name"]
            if hub_name in hubs:
                raise parse_error(
                    line_number,
                    line,
                    f"hub '{hub_name}' is defined more than once",
                )

            try:
                metadata = read_metadata_node(data["metadata"])
            except ValueError as error:
                raise parse_error(line_number, line, str(error)) from error

            hub: HubDict = {
                "name": hub_name,
                "x": int(data["x"]),
                "y": int(data["y"]),
                "metadata": metadata,
            }
            hubs[hub_name] = hub

            if data["type"] == "start_hub":
                if start_hub is not None:
                    raise parse_error(
                        line_number,
                        line,
                        "start_hub defined twice in the file",
                    )
                start_hub = hub_name
            elif data["type"] == "end_hub":
                if end_hub is not None:
                    raise parse_error(
                        line_number,
                        line,
                        "end_hub defined twice in the file",
                    )
                end_hub = hub_name
            continue

        if match := connection_pattern.search(line):
            data = match.groupdict()
            left = data["left"]
            right = data["right"]
            if left not in hubs or right not in hubs:
                raise parse_error(
                    line_number,
                    line,
                    "connection must link only previously defined hubs",
                )

            connection_key = (left, right) if left < right else (right, left)
            if connection_key in seen_connections:
                raise parse_error(
                    line_number,
                    line,
                    f"connection '{left}-{right}' is duplicated",
                )
            seen_connections.add(connection_key)

            try:
                max_link_capacity = read_metadata_connection(data["metadata"])
            except ValueError as error:
                raise parse_error(line_number, line, str(error)) from error

            connections.append(
                {
                    "left": left,
                    "right": right,
                    "max_link_capacity": max_link_capacity,
                }
            )
            continue

        raise parse_error(line_number, line, "line does not match the format")

    if start_hub is None:
        raise ValueError("start_hub not found in the file")
    if end_hub is None:
        raise ValueError("end_hub not found in the file")

    result: ParsedData = {
        "nb_drones": nb_drones,
        "start_hub": start_hub,
        "end_hub": end_hub,
        "hubs": hubs,
        "connections": connections,
    }

    return result
