from chose_map import Display_Chooser, get_folder
from display import Display
from graph import Graph
from parsing import parsing_file
from connected import connected_graph


def main() -> None:
    """Run the map chooser, parser, router, and display loop."""
    try:
        maps_dict = get_folder()
    except FileNotFoundError:
        print("Error: folder 'maps' not found")
        return
    except NotADirectoryError:
        print("Error: The path is not a directory")
        return
    except (ValueError, Exception) as error:
        print("Error", error)
        return

    chooser = Display_Chooser(maps_dict)
    map_path = chooser.main()
    if map_path is None:
        return

    try:
        data = parsing_file(map_path)
    except Exception as error:
        print("Error:", error)
        return

    graph = Graph(data)
    if not connected_graph(graph):
        print("Error: entry and exit not connected")
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
