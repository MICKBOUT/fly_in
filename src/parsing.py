import re

def read_metadata_connection(metadata_str: str) -> int:
    metadata_pattern = re.compile(r"max_link_capacity=(?P<value>\d+)")

    if metadata_str is None:
        return 1

    match = metadata_pattern.search(metadata_str)
    return int(match.group("value")) if match else 1

def read_metadata_node(metadata_str: str) -> dict:
    metadata_pattern = re.compile(r"(?P<key>zone|color|max_drones)=(?P<value>\w+)")

    result = {
        "zone": "normal",
        "color": None,
        "max_drones": 1,
    }

    result
    if metadata_str is None:
        return result
    
    for match in metadata_pattern.finditer(metadata_str):
        key = match.group("key")
        value = match.group("value")
        result[key] = value
    
    result["max_drones"] = int(result["max_drones"])
    return result

def parsing_file(path: str = "maps/easy/01_linear_path.txt"):
    import json
    result = {
        "nb_drones": None,
        "start_hub": None,
        "end_hub": None,
        "hubs": {},
        "connections": [],
    }
    nb_drones_pattern = re.compile(r"^nb_drones: (?P<nb_drones>\d+)")
    hub_pattern = re.compile(r"^(?P<type>start_hub|end_hub|hub): (?P<name>\w+) (?P<x>-?\d+) (?P<y>-?\d+)(?:\s+\[(?P<metadata>[^\]]*)\])?")
    connection_pattern = re.compile(r"^connection: (?P<left>\w+)-(?P<right>\w+)(?:\s+\[(?P<metadata>[^\]]*)\])?")

    # path="maps/hard/03_ultimate_challenge.txt"
    with open(path) as file:
        lines = [line for line in file.read().splitlines() if (not line.startswith("#")) and (line.strip())]

        if not lines:
            raise ValueError("File empty")
        elif match := nb_drones_pattern.search(lines[0]):
            result["nb_drones"] = int(match.group("nb_drones"))
        else:
            raise ValueError("nb_drones not found at the first line of the file.")

        for line in lines[1:]:
            if match := hub_pattern.search(line):
                data = match.groupdict()
                hub = {
                    "name": data["name"],
                    "x": int(data["x"]),
                    "y": int(data["y"]),
                    "metadata": read_metadata_node(data["metadata"]),
                }
                result["hubs"][data["name"]] = hub

                if data["type"] == "start_hub":
                    if result["start_hub"] is not None:
                        raise ValueError("start_hub defined twice in the file")
                    result["start_hub"] = data["name"]

                elif data["type"] == "end_hub":
                    if result["end_hub"] is not None:
                        raise ValueError("end_hub defined twice in the file")
                    result["end_hub"] = data["name"]

            elif match := connection_pattern.search(line):
                data = match.groupdict()
                result["connections"].append({
                    "left": data["left"],
                    "right": data["right"],
                    "max_link_capacity": read_metadata_connection(data["metadata"]),
                })
            else:
                raise ValueError(f"Line '{line}' not used")

        with open("file.txt", "w") as f:
            json.dump(result, f, indent=4)

        print("data:")
        for k, v in result.items():
            print(f"{k}: {v}")
