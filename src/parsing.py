"""Parse Fly-In map files into typed routing data."""

import re
from typing import TypedDict

VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
NAME_PATTERN = r"[^\s\-\[\]]+"
METADATA_VALUE_PATTERN = r"[^\s\]]+"


class MetadataDict(TypedDict):
    """Metadata stored on a hub."""

    zone: str
    color: str | None
    max_drones: int


class HubDict(TypedDict):
    """Parsed hub definition."""

    name: str
    x: int
    y: int
    metadata: MetadataDict


class ConnectionDict(TypedDict):
    """Parsed connection definition."""

    left: str
    right: str
    max_link_capacity: int


class ParsedData(TypedDict):
    """Full parsed content of a map file."""

    nb_drones: int
    start_hub: str
    end_hub: str
    hubs: dict[str, HubDict]
    connections: list[ConnectionDict]


LineData = tuple[int, str]


class MapParser:
    """Stateful parser for one Fly-In map file."""

    NB_DRONES_PATTERN = re.compile(r"^nb_drones: (?P<nb_drones>\d+)$")
    HUB_PATTERN = re.compile(
        rf"^(?P<type>start_hub|end_hub|hub): (?P<name>{NAME_PATTERN}) "
        r"(?P<x>-?\d+) (?P<y>-?\d+)(?:\s+\[(?P<metadata>[^\]]*)\])?$"
    )
    CONNECTION_PATTERN = re.compile(
        rf"^connection: (?P<left>{NAME_PATTERN})-(?P<right>{NAME_PATTERN})"
        r"(?:\s+\[(?P<metadata>[^\]]*)\])?$"
    )
    NODE_METADATA_PATTERN = re.compile(
        r"^(?P<key>zone|color|max_drones)="
        rf"(?P<value>{METADATA_VALUE_PATTERN})$"
    )
    CONNECTION_METADATA_PATTERN = re.compile(
        r"^max_link_capacity=(?P<value>\d+)$"
    )

    def __init__(self, path: str) -> None:
        """Store parser state for the given map path."""
        self.path = path
        self.start_hub: str | None = None
        self.end_hub: str | None = None
        self.hubs: dict[str, HubDict] = {}
        self.connections: list[ConnectionDict] = []
        self.seen_connections: set[tuple[str, str]] = set()

    def parse(self) -> ParsedData:
        """Parse the whole map file and return typed map data."""
        lines = self.load_lines()
        nb_drones = self.parse_nb_drones(lines[0])

        for line_data in lines[1:]:
            self.parse_line(line_data)

        if self.start_hub is None:
            raise ValueError("start_hub not found in the file")
        if self.end_hub is None:
            raise ValueError("end_hub not found in the file")

        return {
            "nb_drones": nb_drones,
            "start_hub": self.start_hub,
            "end_hub": self.end_hub,
            "hubs": self.hubs,
            "connections": self.connections,
        }

    def load_lines(self) -> list[LineData]:
        """Load non-empty, non-comment lines while preserving numbers."""
        with open(self.path, encoding="utf-8") as file:
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
        return lines

    def parse_nb_drones(self, line_data: LineData) -> int:
        """Parse and validate the first `nb_drones` line."""
        line_number, line = line_data
        match = self.NB_DRONES_PATTERN.search(line)
        if match is None:
            raise self.parse_error(
                line_number,
                line,
                "expected nb_drones on the first line",
            )
        return int(match.group("nb_drones"))

    def parse_line(self, line_data: LineData) -> None:
        """Dispatch one map line to the matching parser."""
        line_number, line = line_data
        hub_match = self.HUB_PATTERN.search(line)
        if hub_match is not None:
            self.parse_hub(line_number, line, hub_match)
            return

        connection_match = self.CONNECTION_PATTERN.search(line)
        if connection_match is not None:
            self.parse_connection(line_number, line, connection_match)
            return

        raise self.parse_error(
            line_number,
            line,
            "line does not match the format",
        )

    def parse_hub(
        self,
        line_number: int,
        line: str,
        match: re.Match[str],
    ) -> None:
        """Parse a hub declaration and register it in parser state."""
        data = match.groupdict()
        hub_name = data["name"]
        if hub_name in self.hubs:
            raise self.parse_error(
                line_number,
                line,
                f"hub '{hub_name}' is defined more than once",
            )

        try:
            metadata = self.read_node_metadata(data["metadata"])
        except ValueError as error:
            raise self.parse_error(line_number, line, str(error)) from error

        self.hubs[hub_name] = {
            "name": hub_name,
            "x": int(data["x"]),
            "y": int(data["y"]),
            "metadata": metadata,
        }

        if data["type"] == "start_hub":
            if self.start_hub is not None:
                raise self.parse_error(
                    line_number,
                    line,
                    "start_hub defined twice in the file",
                )
            self.start_hub = hub_name
        elif data["type"] == "end_hub":
            if self.end_hub is not None:
                raise self.parse_error(
                    line_number,
                    line,
                    "end_hub defined twice in the file",
                )
            self.end_hub = hub_name

    def parse_connection(
        self,
        line_number: int,
        line: str,
        match: re.Match[str],
    ) -> None:
        """Parse a connection declaration and register it."""
        data = match.groupdict()
        left = data["left"]
        right = data["right"]
        if left not in self.hubs or right not in self.hubs:
            raise self.parse_error(
                line_number,
                line,
                "connection must link only previously defined hubs",
            )

        connection_key = (left, right) if left < right else (right, left)
        if connection_key in self.seen_connections:
            raise self.parse_error(
                line_number,
                line,
                f"connection '{left}-{right}' is duplicated",
            )
        self.seen_connections.add(connection_key)

        try:
            max_link_capacity = self.read_connection_metadata(
                data["metadata"]
            )
        except ValueError as error:
            raise self.parse_error(line_number, line, str(error)) from error

        self.connections.append(
            {
                "left": left,
                "right": right,
                "max_link_capacity": max_link_capacity,
            }
        )

    def read_connection_metadata(self, metadata_str: str | None) -> int:
        """Parse connection metadata and return its capacity."""
        if metadata_str is None:
            return 1

        metadata_tokens = metadata_str.split()
        if not metadata_tokens:
            return 1
        if len(metadata_tokens) != 1:
            raise ValueError("invalid connection metadata")

        match = self.CONNECTION_METADATA_PATTERN.fullmatch(metadata_tokens[0])
        if match is None:
            raise ValueError("invalid connection metadata")

        capacity = int(match.group("value"))
        if capacity <= 0:
            raise ValueError("max_link_capacity must be a positive integer")
        return capacity

    def read_node_metadata(self, metadata_str: str | None) -> MetadataDict:
        """Parse hub metadata and apply subject defaults."""
        result: MetadataDict = {
            "zone": "normal",
            "color": None,
            "max_drones": 1,
        }
        if metadata_str is None:
            return result

        seen_keys: set[str] = set()
        for token in metadata_str.split():
            match = self.NODE_METADATA_PATTERN.fullmatch(token)
            if match is None:
                raise ValueError("invalid hub metadata")

            key = match.group("key")
            value = match.group("value")
            if key in seen_keys:
                raise ValueError(f"duplicate metadata key '{key}'")
            seen_keys.add(key)

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

    def parse_error(
        self,
        line_number: int,
        line: str,
        message: str,
    ) -> ValueError:
        """Build a consistent parser error with line context."""
        return ValueError(f"line {line_number}: {message}: {line}")


def parsing_file(path: str = "maps/easy/01_linear_path.txt") -> ParsedData:
    """Parse one map file with the project-compatible helper API."""
    return MapParser(path).parse()
