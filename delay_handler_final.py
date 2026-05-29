# delay_handler_final.py
# Professional delay prediction handler with exit commands and enhanced model integration
# Flexible, multi-parameter input without emojis

from predict_delay import load_station_codes, get_station_code, get_route, ROUTE_STATIONS
from model import predict_delay, time_to_minutes
from difflib import get_close_matches, SequenceMatcher
import re


# Exit commands the user can use to leave delay mode
EXIT_COMMANDS = {'exit', 'quit', 'done', 'back', 'cancel', 'stop', 'end', 'leave'}


class DelaySession:
    """Flexible session that tracks gathered parameters in any order"""
    
    def __init__(self):
        self.from_station = None
        self.from_station_code = None
        self.to_station = None
        self.to_station_code = None
        self.planned_arrival_time = None
        self.current_delay = None
        self.route = None
        self.stations = load_station_codes()
    
    def is_complete(self):
        """Check if all required info is gathered"""
        return all([
            self.from_station_code,
            self.to_station_code,
            self.planned_arrival_time,
            self.current_delay is not None
        ])
    
    def get_missing_info(self):
        """Return list of missing required fields"""
        missing = []
        if not self.from_station_code:
            missing.append("current station")
        if not self.to_station_code:
            missing.append("destination")
        if not self.planned_arrival_time:
            missing.append("planned arrival time")
        if self.current_delay is None:
            missing.append("current delay")
        return missing
    
    def reset(self):
        """Reset session"""
        self.__init__()


def check_exit_command(user_input):
    """Check if user wants to exit delay mode. Returns True if exit requested."""
    return user_input.strip().lower() in EXIT_COMMANDS


def find_station_fuzzy(user_input, stations, route_stations_only=False):
    """Fuzzy match user input to station name/code. Returns (station_name, station_code) or None."""
    user_input = user_input.strip().upper()
    
    # Direct exact match
    if user_input in stations:
        code = stations[user_input]
        if route_stations_only and code not in ROUTE_STATIONS:
            return None
        for name, code_check in stations.items():
            if code_check == code and len(name) > 3:
                return (name, code)
        return (user_input, code)
    
    # Fuzzy match
    station_names = list(stations.keys())
    matches = get_close_matches(user_input, station_names, n=3, cutoff=0.6)
    
    for match in matches:
        code = stations[match]
        if route_stations_only and code not in ROUTE_STATIONS:
            continue
        return (match, code)
    
    return None


def parse_time_flexible(text):
    """Extract time from text in various formats. Returns HHMM or None."""
    text = str(text).lower().strip()
    
    patterns = [
        (r'(\d{1,2}):(\d{2})\s*(am|pm)?', True),
        (r'(\d{1,2})\.(\d{2})', False),
        (r'\b(\d{1,2})(\d{2})\b', False),
    ]
    
    for pattern, has_meridiem in patterns:
        match = re.search(pattern, text)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            
            if has_meridiem and len(match.groups()) >= 3:
                meridiem = match.group(3)
                if meridiem == 'pm' and hours != 12:
                    hours += 12
                elif meridiem == 'am' and hours == 12:
                    hours = 0
            
            if 0 <= hours < 24 and 0 <= minutes < 60:
                return f"{hours:02d}{minutes:02d}"
    
    return None


def parse_duration_to_minutes(duration_text):
    """Convert a duration like '1:30' or '1 hour 30 minutes' into minutes."""
    duration_text = str(duration_text).lower().strip()

    # HH:MM duration
    match = re.match(r'^(\d{1,2}):(\d{2})$', duration_text)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours * 60 + minutes

    hours = 0
    minutes = 0

    hour_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b', duration_text)
    if hour_match:
        hours = float(hour_match.group(1))

    minute_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b', duration_text)
    if minute_match:
        minutes = float(minute_match.group(1))

    if hours or minutes:
        return int(hours * 60 + minutes)

    match = re.search(r'(\d+(?:\.\d+)?)', duration_text)
    if match:
        return int(float(match.group(1)))

    return None


def parse_delay_flexible(text):
    """Extract delay value from text. Returns float or None."""
    text = str(text).lower()

    if not re.search(r'\b(delay|delayed|late|behind|mins?|minutes?|hours?|hrs?)\b', text):
        return None

    patterns = [
        r'\b(?:delayed?|delay|behind)\b[^0-9]*(\d{1,2}:\d{2})',
        r'\b(?:delayed?|delay|behind)\b[^0-9]*(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b',
        r'\b(?:delayed?|delay|behind)\b[^0-9]*(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b',
        r'(\d{1,2}:\d{2})\s*(?:delay|late)\b',
        r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b',
        r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            delay = parse_duration_to_minutes(match.group(1))
            if delay is not None and delay >= 0:
                return delay

    return None


def collect_route_station_mentions(text, stations, route_stations_only=True):
    """Find route station names in user input in order of appearance."""
    text = text.lower()
    candidates = []
    seen_codes = set()

    for name, code in stations.items():
        if len(name) == 3 and name.isalpha():
            continue
        if route_stations_only and code not in ROUTE_STATIONS:
            continue
        name_lower = name.lower()
        if name_lower in text and code not in seen_codes:
            position = text.find(name_lower)
            if position >= 0:
                candidates.append((position, name, code))
                seen_codes.add(code)

    candidates.sort(key=lambda item: item[0])
    return [(name, code) for _, name, code in candidates]


def extract_multiple_params(user_input, session):
    """Extract multiple parameters from a single input."""
    extracted = {
        'from_station': None,
        'to_station': None,
        'time': None,
        'delay': None
    }
    
    user_lower = user_input.lower()
    
    # Look for "from X to Y" pattern and capture destination before time/delay text
    from_match = re.search(
        r'\bfrom\s+([a-z\s]+?)\s+to\s+(.+?)(?=\s+(?:at|delayed?|delay|late|behind|due|\d|$))',
        user_lower
    )
    if from_match:
        from_text = from_match.group(1).strip()
        to_text = from_match.group(2).strip()
        
        from_result = find_station_fuzzy(from_text, session.stations, route_stations_only=True)
        to_result = find_station_fuzzy(to_text, session.stations, route_stations_only=True)
        
        if from_result:
            extracted['from_station'] = from_result
        if to_result:
            extracted['to_station'] = to_result
    
    # Look for time
    time_val = parse_time_flexible(user_input)
    if time_val:
        extracted['time'] = time_val
    
    # Look for delay
    delay_val = parse_delay_flexible(user_input)
    if delay_val is not None:
        extracted['delay'] = delay_val

    # Attempt to extract station names in order when explicit from/to is missing
    station_mentions = collect_route_station_mentions(user_input, session.stations, route_stations_only=True)
    if station_mentions:
        if not extracted['from_station'] and not extracted['to_station']:
            if len(station_mentions) >= 2:
                extracted['from_station'] = station_mentions[0]
                extracted['to_station'] = station_mentions[1]
            elif len(station_mentions) == 1:
                station_name, station_code = station_mentions[0]
                if re.search(r'\bfrom\s+' + re.escape(station_name.lower()) + r'\b', user_lower):
                    extracted['from_station'] = station_mentions[0]
                elif re.search(r'\bto\s+' + re.escape(station_name.lower()) + r'\b', user_lower):
                    extracted['to_station'] = station_mentions[0]
        else:
            for station_name, station_code in station_mentions:
                if not extracted['from_station'] and session.to_station_code != station_code:
                    extracted['from_station'] = (station_name, station_code)
                elif not extracted['to_station'] and session.from_station_code != station_code:
                    if extracted['from_station'] and station_code == extracted['from_station'][1]:
                        continue
                    extracted['to_station'] = (station_name, station_code)
    
    # If no from/to found, try individual station
    if not extracted['from_station'] and not session.from_station_code:
        station_result = find_station_fuzzy(user_input, session.stations, route_stations_only=True)
        if station_result:
            extracted['from_station'] = station_result
    
    if not extracted['to_station'] and session.from_station_code and not session.to_station_code:
        station_result = find_station_fuzzy(user_input, session.stations, route_stations_only=True)
        if station_result and station_result[1] != session.from_station_code:
            extracted['to_station'] = station_result
    
    return extracted


def update_session_from_extracted(session, extracted):
    """Update session with extracted parameters"""
    if extracted['from_station']:
        name, code = extracted['from_station']
        session.from_station = name
        session.from_station_code = code
    
    if extracted['to_station']:
        name, code = extracted['to_station']
        session.to_station = name
        session.to_station_code = code
        
        if session.from_station_code and session.to_station_code:
            route = get_route(session.from_station_code, session.to_station_code)
            if route:
                session.route = route
    
    if extracted['time']:
        session.planned_arrival_time = extracted['time']
    
    if extracted['delay'] is not None:
        session.current_delay = extracted['delay']


def handle_delay_input(user_input, session):
    """Flexible handler that extracts whatever info user provides."""
    user_input = user_input.strip()
    
    # Check for exit command
    if check_exit_command(user_input):
        return ("EXIT_DELAY_MODE", "Exiting delay prediction mode. You can continue booking or start over.")
    
    if not user_input:
        return ("CONTINUE", "I didn't catch that. Tell me something about your journey?\n(e.g., 'from Southampton to London', a station name, or time)")
    
    # Extract whatever parameters user provided
    extracted = extract_multiple_params(user_input, session)
    update_session_from_extracted(session, extracted)
    
    # Validate route if both stations are set
    if session.from_station_code and session.to_station_code:
        if session.from_station_code == session.to_station_code:
            session.to_station_code = None
            session.to_station = None
            return ("CONTINUE", f"Error: Your current station and destination cannot be the same.\n\nWhere would you like to go instead?")
        
        route = get_route(session.from_station_code, session.to_station_code)
        if route is None:
            session.to_station_code = None
            session.to_station = None
            return (
                "CONTINUE",
                f"Error: The route from {session.from_station} to {user_input.strip()} is not supported.\n\n"
                f"Supported stations: Weymouth, Poole, Bournemouth, Southampton, Winchester, "
                f"Basingstoke, Woking, Wimbledon, Clapham Junction, London Waterloo\n\n"
                f"Where else can I help you go?"
            )
        session.route = route
    
    # Check if ready to predict
    if session.is_complete():
        return ("PREDICTION", make_prediction(session))
    
    # Not ready - ask for missing info
    missing = session.get_missing_info()
    return ("CONTINUE", build_guidance_prompt(session, missing))


def build_guidance_prompt(session, missing):
    """Build helpful prompt asking for missing info."""
    responses = []
    
    # Acknowledge what we got
    if session.from_station or session.to_station or session.planned_arrival_time or session.current_delay is not None:
        if session.from_station:
            responses.append(f"Current station: {session.from_station}\n")
        if session.to_station:
            responses.append(f"Destination: {session.to_station}\n")
        if session.planned_arrival_time:
            responses.append(f"Planned arrival: {format_time_display(session.planned_arrival_time)}\n")
        if session.current_delay is not None:
            responses.append(f"Current delay: {session.current_delay} min\n")
        responses.append("")
    
    # Ask for first missing item
    if "current station" in missing:
        responses.append("Q: Which station are you currently at?")
        responses.append("   (e.g., Southampton, Waterloo, Poole, Bournemouth)")
    elif "destination" in missing:
        responses.append(f"Q: Where are you heading from {session.from_station}?")
        responses.append("   (e.g., London Waterloo, Weymouth, Bournemouth)")
    elif "planned arrival time" in missing:
        responses.append(f"Q: What time should you arrive at {session.to_station}?")
        responses.append("   (e.g., 15:45, 3:45pm, 1545)")
    elif "current delay" in missing:
        responses.append(f"Q: How many minutes is your train currently delayed?")
        responses.append("   (e.g., 12, 15.5, or 'delayed 20 minutes')")
    
    # Encourage flexibility
    if len(missing) < 4:
        responses.append("\nHint: You can update any answer, e.g., 'actually from Bournemouth'")
    
    responses.append("\nType 'exit', 'quit', or 'done' to leave delay mode.")
    
    return "\n".join(responses)


def make_prediction(session):
    """Call ML model and return prediction with station-by-station times."""
    try:
        predicted_delay = predict_delay(
            session.route,
            session.from_station_code,
            session.planned_arrival_time,
            session.current_delay
        )
    except Exception as e:
        return f"Error during prediction: {str(e)}\n\nLet's try /delay again"
    
    if predicted_delay is None:
        return (
            f"Warning: Could not make a prediction for this combination.\n"
            f"There might be insufficient historical data for that station.\n\n"
            f"Try /delay again with different parameters."
        )
    
    from predict_delay import get_final_arrival_time
    final_arrival_time = get_final_arrival_time(
        session.planned_arrival_time,
        predicted_delay
    )
    
    if final_arrival_time is None:
        return f"Error: Could not calculate final arrival time. Check your inputs."
    
    # Build station-by-station times
    station_times = build_station_times(
        session.from_station_code,
        session.to_station_code,
        session.planned_arrival_time,
        session.current_delay,
        predicted_delay
    )
    
    response = (
        f"DELAY PREDICTION RESULT\n"
        f"{'='*50}\n"
        f"Route: {session.from_station} -> {session.to_station}\n"
        f"Planned arrival: {format_time_display(session.planned_arrival_time)}\n"
        f"Current delay: +{session.current_delay} min\n"
        f"Predicted additional delay: +{predicted_delay} min\n"
        f"{'='*50}\n"
        f"EXPECTED ARRIVAL: {final_arrival_time}\n"
        f"{'='*50}\n\n"
        f"Station-by-station times:\n"
        f"{station_times}\n\n"
        f"Book a ticket or type 'exit' to leave delay mode."
    )
    
    return response


def build_station_times(from_code, to_code, planned_arrival, current_delay, predicted_delay):
    """Build readable station-by-station timing information."""
    from_idx = ROUTE_STATIONS.index(from_code)
    to_idx = ROUTE_STATIONS.index(to_code)
    
    if from_idx < to_idx:
        # Going from Waterloo towards Weymouth (southbound)
        stations_on_route = ROUTE_STATIONS[from_idx:to_idx+1]
    else:
        # Going from Weymouth towards Waterloo (northbound)
        stations_on_route = ROUTE_STATIONS[to_idx:from_idx+1][::-1]
    
    # Map station codes to readable names
    station_names = {
        'WAT': 'London Waterloo',
        'CLJ': 'Clapham Junction',
        'WIM': 'Wimbledon',
        'WOK': 'Woking',
        'BSK': 'Basingstoke',
        'WIN': 'Winchester',
        'SOU': 'Southampton Central',
        'BMH': 'Bournemouth',
        'POO': 'Poole',
        'WEY': 'Weymouth'
    }
    
    lines = []
    planned_min = time_to_minutes(planned_arrival)
    
    for i, code in enumerate(stations_on_route):
        if code == from_code:
            lines.append(f"  [START] {station_names.get(code, code)}: NOW")
        elif code == to_code:
            final_min = planned_min + round(predicted_delay)
            final_time = minutes_to_time(final_min)
            lines.append(f"  [DEST]  {station_names.get(code, code)}: {final_time} (delayed by {round(predicted_delay)} min)")
        else:
            # Intermediate stations - estimate based on position
            progress = i / (len(stations_on_route) - 1) if len(stations_on_route) > 1 else 0
            intermediate_delay = current_delay + (predicted_delay * progress)
            intermediate_min = planned_min + round(intermediate_delay)
            intermediate_time = minutes_to_time(intermediate_min)
            lines.append(f"         {station_names.get(code, code)}: {intermediate_time} (est. delay: {round(intermediate_delay)} min)")
    
    return "\n".join(lines)


def minutes_to_time(total_minutes):
    """Convert total minutes since midnight to HH:MM format, handling day boundaries."""
    # Handle day boundary wrapping
    total_minutes = total_minutes % 1440  # 1440 minutes in a day
    
    hours = int(total_minutes) // 60
    minutes = int(total_minutes) % 60
    
    return f"{hours:02d}:{minutes:02d}"


def format_time_display(time_str):
    """Convert HHMM format to HH:MM for display"""
    if not time_str:
        return None
    time_str = str(time_str).replace(':', '').strip()
    if len(time_str) == 4 and time_str.isdigit():
        return f"{time_str[:2]}:{time_str[2:]}"
    return time_str


def start_delay_prediction():
    """Return initial greeting."""
    return (
        "I'll predict your train's arrival time based on current delays.\n"
        "This service supports the Weymouth-London Waterloo line.\n\n"
        "Example: 'from Southampton to London at 15:45, delayed 12 minutes'\n\n"
        "\n"
        "Q: What is your starting station?\n"
        "   (Type 'exit' or 'quit' to leave delay mode)"
    )
