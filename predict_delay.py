from datetime import datetime, timedelta
from pathlib import Path

from model import predict_delay


# Loads station names and station codes
def load_station_codes():
    stations = {}

    file_path = Path("data/uk_railway_stations.txt")

    with open(file_path) as file:
        for line in file:
            parts = line.strip().split(" | ")

            if len(parts) == 2:
                station_name = parts[0].lower()
                station_code = parts[1].upper()

                stations[station_name] = station_code
                stations[station_code.lower()] = station_code

    return stations


# full station name or code into station code
def get_station_code(user_station, stations):
    user_station = user_station.lower().strip()

    if user_station in stations:
        return stations[user_station]

    for station_name, station_code in stations.items():
        if user_station in station_name:
            return station_code

    return None


# Adds delay to planned arrival time
def add_delay_to_time(time_text, delay):
    time_text = time_text.strip().replace(":", "")

    if len(time_text) == 3:
        time_text = "0" + time_text

    original_time = datetime.strptime(time_text, "%H%M")
    new_time = original_time + timedelta(minutes=delay)

    return new_time.strftime("%H:%M")

#---------
def get_delay_prediction(delay_info):
    stations = load_station_codes()

    route = delay_info["route"]
    current_station = delay_info["current_station"]
    current_delay = delay_info["current_delay"]
    planned_arrival = delay_info["planned_arrival"]

    location_code = get_station_code(current_station, stations)

    if location_code is None:
        return {
            "success": False,
            "message": "Station not recognised."
        }

    predicted_delay = predict_delay(
        route,
        location_code,
        planned_arrival,
        current_delay
    )

    if predicted_delay is None:
        return {
            "success": False,
            "message": "Prediction could not be made. Please check the route, station or time."
        }

    expected_arrival = add_delay_to_time(planned_arrival, predicted_delay)

    return {
        "success": True,
        "route": route,
        "current_station": current_station,
        "station_code": location_code,
        "current_delay": current_delay,
        "predicted_delay": predicted_delay,
        "planned_arrival": planned_arrival,
        "expected_arrival": expected_arrival
    }


# Manual Test
if __name__ == "__main__":

    delay_info = {
        "route": input("Route WEY2WAT or WAT2WEY: "),
        "current_station": input("Current station name or code: "),
        "current_delay": float(input("Current delay in minutes: ")),
        "planned_arrival": input("Planned arrival time at destination, example 1435 or 14:35: ")
    }

    result = get_delay_prediction(delay_info)

    if not result["success"]:
        print("\n" + result["message"])
    else:
        print("\nCurrent station:", result["current_station"])
        print("Station code:", result["station_code"])
        print("Current delay:", result["current_delay"], "minutes")
        print("Predicted final delay:", result["predicted_delay"], "minutes")
        print("Expected arrival time:", result["expected_arrival"])