_This project has been created as part of the 42 curriculum by mboutte._

# Fly-in

## Description

Fly-in is a Python simulation project about routing a fleet of drones from one
start hub to one end hub through a graph of connected zones.

The goal is to move every drone to the destination in as few simulation turns
as possible while respecting:

- zone capacities (`max_drones`)
- connection capacities (`max_link_capacity`)
- blocked zones
- restricted zones that cost 2 turns to enter
- priority zones that should be preferred when paths are equivalent

The project includes:

- a parser for map files
- an object-oriented routing engine
- a turn-by-turn simulation log
- a graphical interface built with `pygame`
- a map chooser to browse the provided test maps

## Features

- Parsing of the subject map format with metadata on hubs and connections
- Validation of duplicated connections and malformed inputs
- Routing with support for simultaneous drones, waiting, and zone/link
  occupancy constraints
- Priority-aware path selection
- Graphical visualization of the network, hubs, links, and drones
- Interactive map selection before launching a simulation

## Instructions

### Requirements

- Python 3.10 or later
- `uv` recommended for dependency management

### Installation

```bash
make install
```

### Run

```bash
make run
```

The program opens a map chooser, lets you select one of the maps in `maps/`,
prints the simulation log in the terminal, and opens the graphical view.

### Debug

```bash
make debug
```

### Lint

```bash
make lint
```

Optional stricter check:

```bash
make lint-strict
```

### Clean

```bash
make clean
```

## Project Structure

```text
src/
├── chose_map.py   # Graphical map chooser
├── display.py     # Pygame visualization
├── graph.py       # Routing and scheduling engine
├── main.py        # Program entrypoint
├── models.py      # Shared data models
└── parsing.py     # Map parser
maps/
assets/
```

## Algorithm Choices

### General strategy

The routing engine is implemented in `src/graph.py`.

The project uses a sequential reservation-based strategy:

1. Build the graph from the parsed map.
2. Route one drone at a time.
3. Reserve the hubs and links used by the computed path.
4. Route the next drone while taking already reserved turns into account.

This approach is simpler than solving the full multi-agent problem globally,
while still allowing good throughput on the provided maps.

### Pathfinding model

The pathfinder searches in a time-expanded state space:

- a state is `(node, turn)`
- moving to a normal or priority node costs `1`
- moving to a restricted node costs `2`
- waiting is allowed when it does not violate capacity rules

The search uses a priority queue based on:

1. total turn count
2. congestion score
3. priority-zone bonus

This means the algorithm first minimizes the arrival time, then prefers less
congested alternatives, and finally prefers routes that go through priority
zones when costs are otherwise equivalent.

### Capacity management

The engine keeps two reservation tables:

- one for node occupancy by turn
- one for link usage by turn

These tables are checked during path search to prevent invalid schedules.

### Why this design

This design was chosen because it gives a good balance between:

- correctness
- readability
- ease of debugging
- acceptable performance on the subject maps

It also makes it easy to explain the simulation during peer evaluation, because
the constraints are explicit in the reservation tables.

## Visual Representation

The visual interface is implemented with `pygame` in `src/display.py`.

It enhances the simulation by showing:

- the graph layout using the coordinates provided in the map files
- hub colors from metadata
- visible drone motion between hubs
- zoom and pan controls
- contextual hub information on hover
- slight separation of drones sharing the same hub so overlapping occupancy
  remains readable

### Controls

- `Left click + drag`: pan
- `Mouse wheel`: zoom in/out
- `Right arrow` or `Space`: advance one turn
- `Left arrow`: go back one turn
- `Escape`: quit

This display is useful during debugging because it makes bottlenecks,
restricted paths, branch usage, and drone accumulation much easier to see than
with terminal output alone.

## Output Format

The terminal output follows the subject format:

- one line per simulation turn
- each movement printed as `D<ID>-<zone>`
- drones that do not move during a turn are omitted

Example:

```text
D1-junction D2-junction
D1-path_a D2-path_b
D1-goal D2-goal
```

## Known Implementation Notes

- The project is fully object-oriented and type-checked with `mypy`.
- The main visualization is graphical rather than terminal-colored.
- The routing engine focuses on minimizing total turns with a reservation-based
  heuristic rather than a full global optimizer.

## Resources

### Technical references

- Python documentation: https://docs.python.org/3/
- `heapq` documentation:
  https://docs.python.org/3/library/heapq.html
- `pygame` documentation: https://www.pygame.org/docs/
- `mypy` documentation: https://mypy.readthedocs.io/
- `flake8` documentation: https://flake8.pycqa.org/

### Graph and pathfinding references

- Dijkstra’s algorithm:
  https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
- A* and informed search overview:
  https://en.wikipedia.org/wiki/A*_search_algorithm
- Multi-agent pathfinding background:
  https://en.wikipedia.org/wiki/Multi-agent_pathfinding

### AI usage

AI was used as a support tool during the project for:

- identifying typing and linting issues
- drafting and restructuring documentation

All generated suggestions were reviewed, tested, and adapted manually before
being kept in the project.
