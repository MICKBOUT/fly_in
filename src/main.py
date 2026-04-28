from parsing import parsing_file


class Drone:
    ...


def main() -> None:
    try:
        parsing_file()
    except Exception as e:
        print(e)
        return


if __name__ == "__main__":
    print("=" * 20)
    main()
    print("=" * 20)
