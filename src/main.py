from argparse import ArgumentParser

from chose_map import Display_Chooser, get_folder
from display import Display
from graph import Graph
from parsing import parsing_file
from connected import connected_graph


def main() -> None:
    """Run the map chooser, parser, router, and display loop.

    This function orchestrates the main workflow of the application:
    1. Retrieves the maps dictionary from the 'maps' folder
    2. Displays a chooser interface for the user to select a map
    3. Parses the selected map file
    4. Creates a graph from the parsed data and validates connectivity
    5. Computes routing paths through the graph
    6. Displays the results with the computed paths

        Returns:
        None

    Raises:
        Prints error messages and returns early if:
        - The 'maps' folder is not found (FileNotFoundError)
        - The maps path is not a directory (NotADirectoryError)
        - Any other error occurs during folder retrieval, file parsing,
            or graph validation
        - The entry and exit nodes are not connected in the graph
    """
    Error_tag = "\033[31mError\033[0m:"

    parser = ArgumentParser(description="fly-in")
    parser.add_argument(
        "--maps_folder",
        type=str,
        default="maps",
        help="Path to the folder where the maps difficulty are located"
    )

    args = parser.parse_args()

    try:
        maps_dict = get_folder(args.maps_folder)
    except FileNotFoundError:
        print(f"{Error_tag} folder '{args.maps_folder}' not found")
        return
    except NotADirectoryError:
        print(f"{Error_tag} The path is not a directory")
        return
    except (ValueError, Exception) as error:
        print(Error_tag, error)
        return

    chooser = Display_Chooser(maps_dict)
    map_path = chooser.main()
    if map_path is None:
        return

    try:
        data = parsing_file(map_path)
    except Exception as error:
        print(Error_tag, error)
        return

    graph = Graph(data)
    if not connected_graph(graph):
        print(f"{Error_tag} entry and exit not connected")
        return

    paths = graph.routing()
    nb_turn = graph.print_log(paths)

    display = Display(
        graph.nodes,
        data["connections"],
        paths,
        graph.start_hub,
        nb_turn,
    )
    display.main()


if __name__ == "__main__":
    print("=" * 20)
    main()
    print("=" * 20)
