import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


DATA_FOLDER = "data"
MODEL_FOLDER = "models"
MODEL_FILE = "models/delay_model.pkl"


# Converts 24-hour clock time into minutes
def time_to_minutes(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    if ":" in value:
        parts = value.split(":")

        try:
            hours = int(parts[0])
            minutes = int(parts[1])
        except ValueError:
            return None

        if hours >= 24:
            hours -= 24

        if minutes >= 60:
            return None

        return hours * 60 + minutes

    value = value.replace(":", "")

    if len(value) == 3:
        value = "0" + value

    if len(value) != 4 or not value.isdigit():
        return None

    hours = int(value[:2])
    minutes = int(value[2:])

    if hours >= 24:
        hours -= 24

    if minutes >= 60:
        return None

    return hours * 60 + minutes


# Calculates delay in minutes using planned and actual clock times
def calculate_delay(planned, actual):
    planned_minutes = time_to_minutes(planned)
    actual_minutes = time_to_minutes(actual)

    if planned_minutes is None or actual_minutes is None:
        return None

    delay = actual_minutes - planned_minutes

    if delay < -720:
        delay += 1440
    elif delay > 720:
        delay -= 1440

    return delay


# Loads all train files
def load_train_data():
    all_data = []

    files = [
        "2022_WEY2WAT.xlsx",
        "2023_WEY2WAT.xlsx",
        "2024_WEY2WAT.xlsx",
        "2025_WEY2WAT.xlsx",
        "2022_WAT2WEY.xlsx",
        "2023_WAT2WEY.xlsx",
        "2024_WAT2WEY.xlsx",
        "2025_WAT2WEY.xlsx",
    ]

    for file in files:
        path = Path(DATA_FOLDER) / file

        if not path.exists():
            print("Missing file:", file)
            continue
        
        print("Reading file...")
        df = pd.read_excel(path)
        print("Finished:", file)

        df.columns = [
            str(col).lower().strip().replace(" ", "_")
            for col in df.columns
        ]

        if "WEY2WAT" in file:
            df["route"] = "WEY2WAT"
        else:
            df["route"] = "WAT2WEY"

        all_data.append(df)

    if not all_data:
        raise FileNotFoundError("No train data files were found in the data folder.")

    return pd.concat(all_data, ignore_index=True)


# Gets delay from a row
def get_row_delay(row):
    delay = calculate_delay(
        row["planned_arrival_time"],
        row["actual_arrival_time"]
    )

    if delay is None:
        delay = calculate_delay(
            row["planned_departure_time"],
            row["actual_departure_time"]
        )

    return delay


# Prepares data for machine learning with current journey status
def prepare_training_data(df):
    rows = []

    for (rid, route), train in df.groupby(["rid", "route"]):

        if route == "WEY2WAT":
            destination_station = "WAT"
        else:
            destination_station = "WEY"

        destination_rows = train[train["location"] == destination_station]

        if destination_rows.empty:
            continue

        destination_row = destination_rows.iloc[-1]
        final_delay = get_row_delay(destination_row)

        if final_delay is None:
            continue

        planned_destination_arrival = time_to_minutes(
            destination_row["planned_arrival_time"]
        )

        if planned_destination_arrival is None:
            continue

        for _, row in train.iterrows():
            current_delay = get_row_delay(row)

            if current_delay is None:
                continue

            if row["location"] == destination_station:
                continue

            rows.append({
                "route": route,
                "location": str(row["location"]).upper(),
                "planned_arrival_minutes": planned_destination_arrival,
                "current_delay": current_delay,
                "final_delay": final_delay
            })

    clean_df = pd.DataFrame(rows)
    clean_df = clean_df.dropna()

    return clean_df


# This Trains, evaluates, retrains on all data and saves the model
def train_delay_model():
    Path(MODEL_FOLDER).mkdir(exist_ok=True)

    raw_data = load_train_data()
    train_data = prepare_training_data(raw_data)

    print("\nTraining rows:", len(train_data))
    print(train_data.head())

    if len(train_data) == 0:
        print("No training rows found.")
        return

    route_encoder = LabelEncoder()
    location_encoder = LabelEncoder()

    train_data["route_code"] = route_encoder.fit_transform(train_data["route"])
    train_data["location_code"] = location_encoder.fit_transform(train_data["location"])

    X = train_data[[
        "route_code",
        "location_code",
        "planned_arrival_minutes",
        "current_delay"
    ]]

    y = train_data["final_delay"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    error = mean_absolute_error(y_test, predictions)

    print("\nModel trained successfully")
    print("Average error in minutes:", round(error, 2))

    # Trains again on all available data before saving the final model
    model.fit(X, y)

    saved_data = {
        "model": model,
        "route_encoder": route_encoder,
        "location_encoder": location_encoder
    }

    with open(MODEL_FILE, "wb") as file:
        pickle.dump(saved_data, file)

    print("Final model trained on all data")
    print("Model saved to:", MODEL_FILE)


# Predicts final delay using general journey information
def predict_delay(route, location, planned_arrival_time, current_delay):
    with open(MODEL_FILE, "rb") as file:
        saved_data = pickle.load(file)

    model = saved_data["model"]
    route_encoder = saved_data["route_encoder"]
    location_encoder = saved_data["location_encoder"]

    route = route.upper()
    location = location.upper()

    if route not in route_encoder.classes_:
        return None

    if location not in location_encoder.classes_:
        return None

    planned_minutes = time_to_minutes(planned_arrival_time)

    if planned_minutes is None:
        return None

    route_code = route_encoder.transform([route])[0]
    location_code = location_encoder.transform([location])[0]

    test_data = pd.DataFrame([{
        "route_code": route_code,
        "location_code": location_code,
        "planned_arrival_minutes": planned_minutes,
        "current_delay": current_delay
    }])

    prediction = model.predict(test_data)[0]

    return round(prediction, 1)


if __name__ == "__main__":
    train_delay_model()