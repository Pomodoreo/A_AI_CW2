from model import predict_delay, time_to_minutes


STATION_FILE = "data/uk_railway_stations.txt"

ROUTE_STATIONS = [
    "WAT",  # London Waterloo
    "CLJ",  # Clapham Junction
    "WIM",  # Wimbledon
    "WOK",  # Woking
    "BSK",  # Basingstoke
    "WIN",  # Winchester
    "SOU",  # Southampton Central
    "BMH",  # Bournemouth
    "POO",  # Poole
    "WEY",  # Weymouth
]


def load_station_codes():
    stations = {}

    with open(STATION_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if "|" not in line:
                continue

            name, code = line.strip().split("|")
            name = name.strip().upper()
            code = code.strip().upper()

            if code != "N/A":
                stations[name] = code
                stations[code] = code

    stations["WATERLOO"] = "WAT"
    stations["LONDON WATERLOO"] = "WAT"
    stations["SOUTHAMPTON"] = "SOU"
    stations["SOUTHAMPTON CENTRAL"] = "SOU"
    stations["BOURNEMOUTH"] = "BMH"
    stations["POOLE"] = "POO"
    stations["WEYMOUTH"] = "WEY"

    return stations


def get_station_code(user_input, stations):
    user_input = user_input.strip().upper()
    return stations.get(user_input)


def get_route(start_code, destination_code):
    if start_code not in ROUTE_STATIONS:
        return None

    if destination_code not in ROUTE_STATIONS:
        return None

    start_index = ROUTE_STATIONS.index(start_code)
    destination_index = ROUTE_STATIONS.index(destination_code)

    if start_index == destination_index:
        return None

    if start_index < destination_index:
        return "WAT2WEY"

    return "WEY2WAT"


# Adds the predicted delay to the planned arrival time
def get_final_arrival_time(planned_arrival_time, predicted_delay):
    planned_minutes = time_to_minutes(planned_arrival_time)

    if planned_minutes is None:
        return None

    final_minutes = planned_minutes + round(predicted_delay)
    final_minutes = final_minutes % 1440

    hours = final_minutes // 60
    minutes = final_minutes % 60

    return f"{hours:02d}:{minutes:02d}"


def main():
    stations = load_station_codes()

    print("Train Delay Prediction")
    print("----------------------")
    print("Supported route: London Waterloo - Weymouth")
    print("You can enter full station names or station codes.\n")

    start_input = input("Current station: ")
    destination_input = input("Destination station: ")

    start_code = get_station_code(start_input, stations)
    destination_code = get_station_code(destination_input, stations)

    if start_code is None:
        print("Sorry, I could not recognise that current station.")
        return

    if destination_code is None:
        print("Sorry, I could not recognise that destination station.")
        return

    if start_code not in ROUTE_STATIONS:
        print("Sorry, delay prediction is not available for that current station.")
        return

    if destination_code not in ROUTE_STATIONS:
        print("Sorry, delay prediction is not available for that destination station.")
        return

    route = get_route(start_code, destination_code)

    if route is None:
        print("The current station and destination cannot be the same.")
        return

    planned_arrival_time = input("Planned arrival time at destination, e.g. 15:45: ")

    try:
        current_delay = float(input("Current delay in minutes: "))
    except ValueError:
        print("Please enter the delay as a number.")
        return

    predicted_delay = predict_delay(
        route,
        start_code,
        planned_arrival_time,
        current_delay
    )

    if predicted_delay is None:
        print("Sorry, I could not make a prediction with the information provided.")
        return

    final_arrival_time = get_final_arrival_time(
        planned_arrival_time,
        predicted_delay
    )

    if final_arrival_time is None:
        print("Sorry, the planned arrival time was not valid.")
        return

    print(
        "\nBased on the current delay, your train is expected to arrive at "
        + destination_input.strip()
        + " at approximately "
        + final_arrival_time
        + "."
    )


if __name__ == "__main__":
    main()