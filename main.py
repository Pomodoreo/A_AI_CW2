# Don't edit anything in this file

import random                 # used to select random responses
import json                   # used to read JSON files
import spacy                  # NLP library for language processing
from date_spacy import find_dates
import requests               # used to download web pages
import warnings               # used to hide warning messages
import dateparser
from difflib import get_close_matches, SequenceMatcher   # used for fuzzy text matching
from bs4 import BeautifulSoup # used to extract data from web pages
from datetime import datetime # used to get current time and date
from random import choice     # used to randomly select a ticket type in tests
# from experta import *         # expert system library used for ticket rules
import re                     # used for regular expressions in ticket rules
import collections
import collections.abc
collections.Mapping = collections.abc.Mapping

from nlp import check_ticket, extract_date_info, extract_destination_info, extract_time_info
from reasoning import get_response

from experta import *         # expert system library used for ticket rules

# hide warning messages to keep the output clean
warnings.filterwarnings("ignore")

# Load the English language model from spaCy
nlp = spacy.load("en_core_web_sm")

nlp2 = spacy.blank('en')
nlp2.add_pipe('find_dates')

#JSON file that contains the intentions and their corresponding responses
intentions_path = r"data/intentions.json"
# text file that contains sentences for time/date detection
sentences_path = r"data/sentences.txt"

#
final_chatbot = False

# Load intentions from the JSON file
with open(intentions_path) as f:

    # load the JSON data into a Python dictionary
    intentions = json.load(f)

# Define a dictionary to store the user's journey information
journey = {
    "from": None,
    "to": None,
    "date": None,
    "return_date": None,
    "time": None,
    "return_time": None,
    "ticket_type": None
}

time_sentences = ''
date_sentences = ''
labels = []
sentences = []

# sentences_master is a dictionary that will store the sentences and their corresponding labels (time or date) in the format: {sentence: label}
sentences_master = {}
# read the sentences from the text file and separate them into time and date sentences
with open(sentences_path) as file:

    for line in file:

        # split each line using the separator " | "
        # parts[0] = label (time or date)
        # parts[1] = the sentence
        parts = line.split(' | ')

        # # if the sentence is labelled as time
        # if parts[0] == 'time':
        #     time_sentences = time_sentences + ' ' + parts[1].strip()

        # # if the sentence is labelled as date
        # elif parts[0] == 'date':
        #     date_sentences = date_sentences + ' ' + parts[1].strip()
        
        # store the sentence and its label in the sentences_master dictionary
        sentences_master[parts[1].lower().strip()] = parts[0]
        
labels = list(sentences_master.values())

#Grab the railway content from text file and store in a dictionary
railway_stations = {}
with open(r"data/uk_railway_stations.txt") as file:

    for line in file:

        # split each line using the separator " | "
        # parts[0] = train station name
        # parts[1] = stattion code
        parts = line.split(' | ')

        # store the stations and its code in the railway_stations dictionary
        railway_stations[parts[0].lower().strip()] = parts[1].strip()


# Function checks if any of the words in the user's sentence match the patterns defined in the intentions. 
# If a match is found, it returns the type of intention and prints a random response from that intention. 
# If the intention is a greeting and the chatbot is in its final state...
# ...it also provides a hint about what topics can be discussed. If no intention is matched, it returns None.
def check_intention_by_keyword(sentence):
    for word in sentence.split():
        for type_of_intention in intentions:
            if word.lower() in intentions[type_of_intention]["patterns"]:
                print("BOT: " + random.choice(intentions[type_of_intention]["responses"]))      
                if type_of_intention == 'greeting' and final_chatbot:
                    print("BOT: We can talk about the time, date, and train tickets.\n(Hint: What time is it?)")
                return type_of_intention
    return None

def lemmatize_and_clean(text):
    doc = nlp(text.lower())
    out = ""

    for token in doc:
        if not token.is_stop and not token.is_punct:
            out = out + token.lemma_ + " "
    return out.strip()

def response_to_input(user_input):
    cleaned_input = lemmatize_and_clean(user_input)
    
    if not cleaned_input:
        return False  # nothing useful to process
    
    doc_1 = nlp(cleaned_input)
    similarities = {}
    index = 0
    for sentence in list(sentences_master.keys()):
        cleaned_sentence = lemmatize_and_clean(sentence)
        doc_2 = nlp(cleaned_sentence)
        similarity = doc_1.similarity(doc_2)
        similarities[index] = similarity # store the similarity score in the similarities dictionary with the index as the key
        index += 1
    # find the index of the sentence with the highest similarity score
    best_match_index = max(similarities, key=similarities.get)
    best_match_sentence = list(sentences_master.keys())[best_match_index]
    best_match_label = sentences_master[best_match_sentence]
    
    min_similarity = 0.6
    
    if similarities[best_match_index] >= min_similarity:
        if best_match_label == 'time':
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"BOT: The current time is {current_time}.")
        elif best_match_label == 'date':
            current_date = datetime.now().strftime("%Y-%m-%d")
            print(f"BOT: Today's date is {current_date}.")
        return True  # a good match was found and a response was given
    else:
        return False  # no good match found
        
def get_best_match_station(user_input):
    user_input = user_input.lower().strip()
    station_list = list(railway_stations.keys())
    best_match = get_close_matches(user_input, station_list, n=1)
    if not best_match:
        return None
    
    sm = SequenceMatcher(None, user_input, best_match[0])
    score = sm.ratio()
    if score >= 0.6:
        return best_match[0]
    else:
        return None
    

# print("BOT: Hello! How can I assist you today?")

# while True:
#     user_input = input("YOU:")
#     if user_input.lower() in ["exit", "quit", "goodbye"]:
#         print("BOT: Goodbye! Have a great day!")
#         break

def extract_journey_info_old(user_input):
    
    final_start = ""
    final_end = ""
    
    possible_start = ""
    possible_end = ""
    
    if "from" in user_input.lower():
        possible_start = user_input.lower().split("from")[1].split()[0] #get the word immediately following "from" as a possible starting location
    if "to" in user_input.lower():
        possible_end = user_input.lower().split("to")[1].split()[0] #get the word immediately following "to" as a possible destination location
    
    
    
    doc = nlp(user_input)
    situation_1 = []
    situation_2_1 = []
    situation_2_2 = []

    # Extract locations (GPE)
    places = [ent.text for ent in doc.ents if ent.label_ == "GPE"] #
    
    if len(places) == 1: #Situation 1
        print(f"Extracted location: {places[0]}")
        for station in railway_stations.keys():
            if places[0].lower() in station:
                situation_1.append(station)
                # print(f"Exact match for '{place}': {station}")
        if len(situation_1) == 0:
            best_match = get_best_match_station(places[0])
            if best_match:
                print(f"Best match for '{places[0]}': {best_match}")
                if determine_to_or_from(best_match, user_input) == "from":
                    final_start = best_match
                elif determine_to_or_from(best_match, user_input) == "to":
                    final_end = best_match
                else:
                    print(f"Couldn't determine if '{best_match}' is a starting location or a destination based on the user input.")
            else:
                print(f"No good match found for '{places[0]}' in railway stations.")
        elif len(situation_1) == 1:
            print(f"There is an exact match for the location you mentioned: {situation_1[0]}")
            if determine_to_or_from(situation_1[0], user_input) == "from":
                final_start = situation_1[0]
            elif determine_to_or_from(situation_1[0], user_input) == "to":
                final_end = situation_1[0]
            else:
                print(f"Couldn't determine if '{situation_1[0]}' is a starting location or a destination based on the user input.")
        else:
            print(f"There are multiple matches for the location you mentioned. Please specify which one you meant: {', '.join(situation_1)}")
        
    elif len(places) == 2: #Situation 2
        print(f"Extracted locations: {', '.join(places)}")
        for station in railway_stations.keys():
            if places[0].lower() in station:
                situation_2_1.append(station)
            if places[1].lower() in station:
                situation_2_2.append(station)
        # print(f"Exact matches for '{places[0]}': {', '.join(situation_2_1)}")
        # print(f"Exact matches for '{places[1]}': {', '.join(situation_2_2)}")
        if len(situation_2_1) == 0:
            best_match_1 = get_best_match_station(places[0])
            if best_match_1:
                print(f"Best match for '{places[0]}': {best_match_1}")
                if determine_to_or_from(best_match_1, user_input) == "from":
                    final_start = best_match_1
                elif determine_to_or_from(best_match_1, user_input) == "to":
                    final_end = best_match_1
                else:
                    print(f"Couldn't determine if '{best_match_1}' is a starting location or a destination based on the user input.")

            else:
                print(f"No good match found for '{places[0]}' in railway stations.")
        elif len(situation_2_1) == 1:
            print(f"There is an exact match for the location you mentioned: {situation_2_1[0]}")
            if determine_to_or_from(situation_2_1[0], user_input) == "from":
                final_start = situation_2_1[0]
            elif determine_to_or_from(situation_2_1[0], user_input) == "to":
                final_end = situation_2_1[0]
            else:
                print(f"Couldn't determine if '{situation_2_1[0]}' is a starting location or a destination based on the user input.")
        else:
            print(f"There are multiple matches for the location you mentioned. Please specify which one you meant: {', '.join(situation_2_1)}")
        
        if len(situation_2_2) == 0:
            best_match_2 = get_best_match_station(places[1])
            if best_match_2:
                print(f"Best match for '{places[1]}': {best_match_2}")
                if determine_to_or_from(best_match_2, user_input) == "from":
                    final_start = best_match_2
                elif determine_to_or_from(best_match_2, user_input) == "to":
                    final_end = best_match_2
                else:
                    print(f"Couldn't determine if '{best_match_2}' is a starting location or a destination based on the user input.")
            else:
                print(f"No good match found for '{places[1]}' in railway stations.")
        elif len(situation_2_2) == 1:
            print(f"There is an exact match for the location you mentioned: {situation_2_2[0]}")
            if determine_to_or_from(situation_2_2[0], user_input) == "from":
                final_start = situation_2_2[0]
            elif determine_to_or_from(situation_2_2[0], user_input) == "to":
                final_end = situation_2_2[0]
            else:
                print(f"Couldn't determine if '{situation_2_2[0]}' is a starting location or a destination based on the user input.")
        else:
            print(f"There are multiple matches for the location you mentioned. Please specify which one you meant: {', '.join(situation_2_2)}")
        
    else: #Situation 3
        print("No locations extracted.")
        print(f"Possible starting location: {possible_start}")
        proposed_start = get_best_match_station(possible_start)
        if proposed_start:
            print(f"Best match for possible starting location '{possible_start}': {proposed_start}")
        print(f"Possible destination location: {possible_end}")
        proposed_end = get_best_match_station(possible_end)
        if proposed_end:
            print(f"Best match for possible destination location '{possible_end}': {proposed_end}")
    
    
    if final_start:
        print(f"Got it, you want to start from {final_start}")
        journey["from"] = final_start
    
    if final_end:
        print(f"Got it, you want to go to {final_end}")
        journey["to"] = final_end
    
    
def determine_to_or_from(station, user_input):  #if the station is mentioned in the user input, determine if it is a starting location (from) or a destination (to) based on the words surrounding the first word in the station name in the user input. If the station is mentioned after the word "from", it is likely a starting location, and if it is mentioned after the word "to", it is likely a destination. If neither is the case, return None.
    station_words = station.split()
    first_word = station_words[0]
    if first_word in user_input.lower().split():
        index = user_input.lower().split().index(first_word)
        if index > 0 and user_input.lower().split()[index - 1] == "from":
            return "from"
        elif index > 0 and user_input.lower().split()[index - 1] == "to":
            return "to"
    return None
    
    
    
    # if station in user_input.lower().split("from"):
    #     return "from"
    # elif station in user_input.lower().split("to"):
    #     return "to"
    # else:
    #     return None

    # dupes = []
    # for place in places:
    #     for station in railway_stations.keys():
    #         if place.lower() in station:
    #             dupes.append(station)
    #             # print(f"Exact match for '{place}': {station}")

    # if len(dupes) == 0: 
    #     for place in places:
    #         best_match = get_best_match_station(place)
    #         if best_match:
    #             print(f"Best match for '{place}': {best_match}")
    #         else:
    #             print(f"No good match found for '{place}' in railway stations.")
    # else:
    #     print(f"There are multiple matches for the location(s) you mentioned. Please specify which one you meant: {', '.join(dupes)}")
        
        # if place.lower() in railway_stations.keys():
        #     print(f"Exact match for '{place}': {place}")
        # else:
        #     best_match = get_best_match_station(place)
        #     if best_match:
        #         print(f"Best match for '{place}': {best_match}")
        #     else:
        #         print(f"No good match found for '{place}' in railway stations.")  
     


#extract_journey_info("I want to travel from London Bridge to Manchester Airport on the 15th of August.")
    

#
# print(output)

doc = nlp2("""The event is scheduled for 25th August 2023.
          We also have a meeting on 10 September and another one on the twelfth of October and a
          final one on January fourth.""")
#dates = []
for ent in doc.ents:
    if ent.label_ == 'DATE':
        print(f'Text: {ent.text} -> Parsed Date: {ent._.date}')
        

    

        
        

#input = "The ticket is an open return for 25th August. I want to go from NRW to London Fenchurch Street."

# output = extract_journey_info(input)
# date_test = extract_date_info(input)
# ticket_test = check_ticket(input)
# print(output)
# print(date_test)
# print(ticket_test)

def run_chatbot():
    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        # -------------------------
        # CALL YOUR FUNCTIONS
        # -------------------------
        ticket = check_ticket(user_input)
        dest_info = extract_destination_info(user_input, journey)
        date_info = extract_date_info(user_input, journey)
        time_info = extract_time_info(user_input, journey)  # NEW

        # -------------------------
        # UPDATE STATE CAREFULLY
        # -------------------------

        # Ticket
        if ticket:
            journey["ticket_type"] = ticket

        # Destinations
        if dest_info["from"] is not None:
            journey["from"] = dest_info["from"]
            journey["from_options"] = None
        elif dest_info["from_options"]:
            journey["from_options"] = dest_info["from_options"]

        if dest_info["to"] is not None:
            journey["to"] = dest_info["to"]
            journey["to_options"] = None
        elif dest_info["to_options"]:
            journey["to_options"] = dest_info["to_options"]

        # Dates
        if date_info["from"] is not None:
            journey["date"] = date_info["from"]._.date

        if date_info["to"] is not None:
            journey["return_date"] = date_info["to"]._.date

        # -------------------------
        # TIMES (NEW SECTION)
        # -------------------------
        if time_info["time"] is not None:
            journey["time"] = time_info["time"]

        if time_info["return_time"] is not None:
            journey["return_time"] = time_info["return_time"]

        # -------------------------
        # GET RESPONSE
        # -------------------------
        print("DEBUG:", journey)
        response = get_response(journey)

        print("Bot:", response)


if __name__ == "__main__":
    run_chatbot()
    
def process_input(user_input, journey):
    from nlp import check_ticket, extract_date_info, extract_destination_info, extract_time_info
    from reasoning import get_response

    ticket = check_ticket(user_input)
    dest_info = extract_destination_info(user_input, journey)
    date_info = extract_date_info(user_input, journey)
    time_info = extract_time_info(user_input, journey)  # NEW

    if ticket:
        journey["ticket_type"] = ticket

    if dest_info["from"]:
        journey["from"] = dest_info["from"]
        journey["from_options"] = None
    elif dest_info["from_options"]:
        journey["from_options"] = dest_info["from_options"]

    if dest_info["to"]:
        journey["to"] = dest_info["to"]
        journey["to_options"] = None
    elif dest_info["to_options"]:
        journey["to_options"] = dest_info["to_options"]

    if date_info["from"] is not None:
        journey["date"] = date_info["from"]

    if date_info["to"] is not None:
        journey["return_date"] = date_info["to"]

    if time_info["time"] is not None:
        journey["time"] = time_info["time"]

    if time_info["return_time"] is not None:
        journey["return_time"] = time_info["return_time"]

    return get_response(journey)