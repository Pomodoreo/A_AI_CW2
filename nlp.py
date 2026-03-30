# Text input parsing

#Imports and resources
import spacy                  # NLP library for language processing
from date_spacy import find_dates
from difflib import get_close_matches, SequenceMatcher   # used for fuzzy text matching
from bs4 import BeautifulSoup # used to extract data from web pages
from datetime import datetime # used to get current time and date
import re                     # used for regular expressions in ticket rules
import collections
import collections.abc
collections.Mapping = collections.abc.Mapping
import datetime

from experta import *      
nlp2 = spacy.blank('en')
nlp2.add_pipe('find_dates') # nlp module for finding dates

# List of all possible railway stations
railway_stations = {}
with open(r"data/uk_railway_stations.txt") as file:

    for line in file:

        # split each line using the separator " | "
        # parts[0] = train station name
        # parts[1] = stattion code
        parts = line.split(' | ')

        # store the stations and its code in the railway_stations dictionary
        railway_stations[parts[0].lower().strip()] = parts[1].strip()


#//////////////////////////////////////////////////////////////////////////////
#Function to look for a ticket type in user input
def check_ticket(user_input):

    # convert user input to lowercase so matching is easier
    user_input = user_input.lower()

    # dictionary list of ticket types supported by the chatbot
    #ticket_list = ['one way', 'round', 'open ticket', 'open return']
    ticket_list = {
    'one way': ['one way', 'single'],
    'return': ['return', 'round trip', 'round-trip'],
    'open ticket': ['open ticket'],
    'open return': ['open return']
}


    # check whether any ticket type appears in the user's sentence
    for ticket_type, variations in ticket_list.items():
        for phrase in variations:
            if phrase in user_input:
                return ticket_type
    return None

# /////////////////////////////////////////////////////////////////////////
# Function to try and extract ticket dates from user input
def extract_date_info(user_input, journey):
    
    user_input = user_input.lower()
    
    # Remove any pesky words
    user_input = user_input.replace("the", "")
    user_input = user_input.replace("of", "")
    
    final_start_date = None
    final_end_date = None
    dates = []
    # variables store related terms for later comparison
    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    week_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    # extra_words = [" today", " tommorow", " now ", " now."]

    for month in months: #Capatalise months so they can be detected
        if month in user_input:
            user_input = user_input.replace(month, month.capitalize())
    doc = nlp2(user_input)
    for ent in doc.ents: #Dectects any "date" in input
        if ent.label_ == 'DATE':
            print(f'Text: {ent.text} -> Parsed Date: {ent._.date}')
            dates.append(ent._.date)       
            
    #Special cases
    if "today" in user_input:
        dates.append(datetime.datetime.today())
    if "tomorrow" in user_input:
        dates.append(datetime.datetime.today() + datetime.timedelta(days=1))    
    if (" now " in user_input) or (" now." in user_input):
        dates.append(datetime.datetime.now())
        
    # Dealing with the keyword "next" aka "next Friday"
    words = user_input.split()
    for i, word in enumerate(words):
        if word == "next" and i + 1 < len(words):
            next_word = words[i + 1]

            if next_word in week_days:
                weekday_index = week_days.index(next_word)
                today_index = datetime.datetime.now().weekday()

                days_delta = weekday_index - today_index
                if days_delta <= 0:
                    days_delta += 7

                result = datetime.datetime.now() + datetime.timedelta(days=days_delta)
                dates.append(result)
        
            
    #Decision alogorithm to guess the context of each date
    if len(dates) >= 2:
        dates.sort(key=lambda x: x)
        final_start_date = dates[0]
        final_end_date = dates[1]
    elif len(dates) == 1:
        if (journey["date"] and journey["return_date"]):
            if (dates[0] >= journey ["date"]) and (dates[0] < journey["return_date"]):
                final_start_date = dates[0]
            elif (dates[0] <= journey ["date"]) and (dates[0] < journey["return_date"]):
                final_end_date = dates[0]
            elif (dates[0] < journey["date"]) and (dates[0] <= journey["return date"]):
                final_end_date = dates[0]
            else:
                final_start_date = dates[0]
        elif (journey["date"]) and (dates[0] >= journey["date"]):
            final_end_date = dates[0]
        elif (journey["return_date"]) and (dates[0] >= journey["return_date"]):
            final_start_date = dates[0]
        else:
            final_start_date = dates[0]       
    else:
        pass
    #Returns a proposed start and end date if applicable
    return {
        "from": final_start_date,
        "to": final_end_date,
    }
    
 # //////////////////////////////////////////////////////////////////
 #Function to try and find possible destinations   
def extract_destination_info(user_input, journey):
    
    user_input = user_input.lower()
    
    # Remove any pesky words
    user_input = user_input.replace("today", "")
    user_input = user_input.replace("tommorow", "")
    user_input = user_input.replace("now", "")
    user_input = user_input.replace("to book ", "")
    
    
    
    fillerwords = ["to buy", "to book", "to purchase", "to obtain", "to get", "to acquire", "to go", "to travel" "to recieve", "station", "railway", "rail", "train station", "underground", "tube"]
    fillerwords = sorted(fillerwords, key=len, reverse=True)
    
    #Removes any inconvinient "to" phrases
    for word in fillerwords:
        if word in user_input:
            user_input = user_input.replace(word, "")
            
    user_input = " ".join(user_input.split())
    
    user_input_lower = user_input.lower()
    
    start_raw = None
    end_raw = None

    # Regex Patterns 
    full_pattern = r"(?:from|leave|depart(?:ing|ure)?)\s*[:,-]?\s*(.*?)\s+(?:\bto\b|arrive|arriving|destination)\s*[:,-]?\s*(.*?)(?:$| on | next | this)"
    to_pattern = r"(?:\bto\b|arrive|arriving|destination)(?:\s+in|\s+at)?\s*[:,-]?\s*(.*?)(?:$| on | next | this )"
    from_pattern = r"(?:from|leave|depart(?:ing|ure)?)(?:\s+from)?\s*[:,-]?\s*(.*?)(?:$| on | next | this)"

    # Trying the full "from... to..." pattern
    match = re.search(full_pattern, user_input_lower)
    if match:
        start_raw = match.group(1).strip()
        end_raw = match.group(2).strip()
    else:
        # Just trying "to...."
        to_match = re.search(to_pattern, user_input_lower)
        if to_match:
            end_raw = to_match.group(1).strip()
            print(end_raw)

        # Just trying "from..."
        from_match = re.search(from_pattern, user_input_lower)
        if from_match:
            start_raw = from_match.group(1).strip()
            
        # Just guesses if unsure 
        if not start_raw and not end_raw:
            cleaned_input = user_input_lower.strip()
            if len(cleaned_input) > 2:
                if not journey.get("from"):
                    start_raw = cleaned_input
                elif not journey.get("to"):
                    end_raw = cleaned_input
                else:
                    end_raw = cleaned_input
    print(start_raw)
    print(end_raw)
    # helper functions
    def is_partial(query):
        return query and len(query.split()) <= 1

    def get_matches(query, stations_dict):
        if not query:
            return []

        query_clean = query.strip().lower()
        # detects if user has typed station code rather than full name
        code_to_station = {code.lower(): station for station, code in stations_dict.items()}
        if query_clean in code_to_station:
            return [code_to_station[query_clean]]

        scored = []

        for station in stations_dict.keys():
            station_lower = station.lower()
            #matching input similarity to existing names
            score = SequenceMatcher(None, query_clean, station_lower).ratio()

            if query_clean in station_lower and len(query_clean) > 3:
                score += 0.15 

            if is_partial(query_clean):
                score -= 0.1   # penalize vague input

            scored.append((station, score))

        if not scored:
            return []

        scored.sort(key=lambda x: x[1], reverse=True)

        best_station, best_score = scored[0]

        MIN_THRESHOLD = 0.70
        BEST_THRESHOLD = 0.85
        CLOSE_GAP = 0.05

        # Reject garbage
        if best_score < MIN_THRESHOLD:
            return []

        # High confidence
        if best_score >= BEST_THRESHOLD and not is_partial(query_clean):
            return [best_station]

        # Otherwise return the close matches
        return [
            s for s, score in scored
            if best_score - score <= CLOSE_GAP
        ]

    
    start_matches = get_matches(start_raw, railway_stations)
    end_matches = get_matches(end_raw, railway_stations)

    # resolves results
    def resolve(matches):
        if len(matches) == 1:
            return matches[0], None
        elif len(matches) > 1:
            return None, matches
        else:
            return None, None

    final_start, start_options = resolve(start_matches)
    final_end, end_options = resolve(end_matches)

    # returns guesses and possible matches if unsure-
    return {
        "from": final_start,
        "to": final_end,
        "from_options": start_options,
        "to_options": end_options
    }
    
# ///////////////////////////////////////////////////////////////////

def extract_time_info(user_input, journey):
    user_input = user_input.lower()

    key_words = {
        "morning": "0600",
        "afternoon": "1200",
        "evening": "1800",
        "night": "0000"
    }

    # Context keywords
    outbound_words = ["leave", "depart", "outbound", "going"]
    return_words = ["return", "back", "coming back"]

    def convert_to_24h(hour, minute="00", meridian=None): #Deals with pm and am
        hour = int(hour)
        minute = int(minute)

        if meridian:
            if meridian == "pm" and hour != 12:
                hour += 12
            if meridian == "am" and hour == 12:
                hour = 0

        return f"{hour:02d}{minute:02d}"

    found_times = []

    # Tries to find any of the key words
    for word, val in key_words.items():
        if word in user_input:
            found_times.append((val, user_input.index(word)))

    # Uses regex to find times using colons
    for m in re.finditer(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?", user_input):
        t = convert_to_24h(m.group(1), m.group(2), m.group(3))
        found_times.append((t, m.start()))

    # AM/PM matching
    for m in re.finditer(r"\b(\d{1,2})\s*(am|pm)\b", user_input):
        t = convert_to_24h(m.group(1), "00", m.group(2))
        found_times.append((t, m.start()))

    # Looks for raw numbers that look like times
    for m in re.finditer(r"\b(\d{3,4})\b", user_input):
        raw = m.group(1)
        if len(raw) == 3:
            raw = "0" + raw
        found_times.append((raw, m.start()))

    # Sort by position in sentence
    found_times.sort(key=lambda x: x[1])

    depart_time = None
    return_time = None

    for time_val, pos in found_times:
        window = user_input[max(0, pos-20):pos+20]

        # Check context
        if any(w in window for w in return_words):
            if not return_time:
                return_time = time_val
        elif any(w in window for w in outbound_words):
            if not depart_time:
                depart_time = time_val
        else:
            # fallback assignment
            if not depart_time:
                depart_time = time_val
            elif not return_time:
                return_time = time_val

    return {
        "time": depart_time,
        "return_time": return_time
    }
            
    


# ----------------------------------------------------------------------------

# journey = {
#     "from": None,
#     "to": None,
#     "date": None,
#     "return_date": None,
#     "time": None,
#     "return_time": None,
#     "ticket_type": None
# }

#output = extract_destination_info("i want to buy a ticket to upminster", journey)
#output = extract_date_info("5th August", journey)
# print(output)
# print(journey)

