"""Interactive command-line interface for the railway simulator."""

from src.parse import load_data, simulate_events
from prompt_toolkit import HTML
from prompt_toolkit import print_formatted_text, prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style


def main():
    trains_by_number, stations_by_code = load_data("data/data_reorged.csv")

    style = Style.from_dict(
        {
            "output": "ansigreen",
        }
    )

    bindings = KeyBindings()

    @bindings.add("c-q")
    def exit_(event):
        event.app.exit()

    def list_trains(trains, page, page_size=100):
        start_index = page * page_size
        end_index = start_index + page_size
        train_numbers = list(trains.keys())
        for i in range(start_index, min(end_index, len(train_numbers))):
            train_no = train_numbers[i]
            print_formatted_text(
                HTML(
                    f"<ansigreen>{train_no}</ansigreen>: "
                    f"{trains[train_no].train_name}"
                )
            )

        if end_index < len(train_numbers):
            print_formatted_text(
                HTML("<ansiwhite>Type 'next' to see more trains.</ansiwhite>")
            )
        if start_index > 0:
            print_formatted_text(
                HTML("<ansiwhite>Type 'prev' to see previous trains.</ansiwhite>")
            )

    current_page = 0

    while True:
        command = prompt("> ", style=style, key_bindings=bindings)
        if command in ["exit", "quit"]:
            break
        elif command == "list trains":
            current_page = 0
            list_trains(trains_by_number, current_page)
        elif command == "next":
            current_page += 1
            list_trains(trains_by_number, current_page)
        elif command == "prev" and current_page > 0:
            current_page -= 1
            list_trains(trains_by_number, current_page)
        elif command.startswith("show train"):
            train_no = command.split()[-1]
            if not train_no.isdigit():
                print_formatted_text(HTML("<ansired>Invalid train number.</ansired>"))
                continue
            train_no = int(train_no)
            if train_no in trains_by_number:
                simulate_events(trains_by_number[train_no].events, 60.0)
            else:
                print_formatted_text(HTML("<ansired>Invalid train number.</ansired>"))
        elif command == "list stations":
            for station_code in stations_by_code:
                print_formatted_text(
                    HTML(
                        f"<ansigreen>{station_code}</ansigreen>: "
                        f"{stations_by_code[station_code].station_name}"
                    )
                )
        elif command.startswith("show station"):
            station_code = command.split()[-1]
            if station_code in stations_by_code:
                simulate_events(
                    stations_by_code[station_code].events,
                    60.0,
                    use_day_offsets=False,
                )
            else:
                print_formatted_text(HTML("<ansired>Invalid station code.</ansired>"))
        else:
            print_formatted_text(HTML("<ansired>Unknown command.</ansired>"))


if __name__ == "__main__":
    main()
