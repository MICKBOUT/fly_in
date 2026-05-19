"""Shared data models used across the project."""

from dataclasses import dataclass


@dataclass
class NodeData:
    """
    Runtime representation of one hub.

    Attributes:
        name (str): The name of the hub.
        x (int): The x-coordinate of the hub's position.
        y (int): The y-coordinate of the hub's position.
        zone (str): The zone classification of the hub.
        color (str | None): The color of the hub, or None if no color is
            assigned.
        max_drones (int): The maximum number of drones that can be handled by
            the hub.
    """

    name: str
    x: int
    y: int
    zone: str
    color: str | None
    max_drones: int
