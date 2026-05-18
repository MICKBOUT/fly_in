"""Shared data models used across the project."""

from dataclasses import dataclass


@dataclass
class NodeData:
    """Runtime representation of one hub."""

    name: str
    x: int
    y: int
    zone: str
    color: str | None
    max_drones: int
