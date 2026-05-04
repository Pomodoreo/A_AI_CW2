# This is for deciding what the chatbot is going to say
from experta import *
from ticket import get_journeys, parse_journeys, find_cheapest
from datetime import datetime

class Session(Fact):
    pass


class TrainBooker(KnowledgeEngine):

    def __init__(self):
        super().__init__()
        self.response = None

    # Clarification rules

    @Rule(Session(from_options=MATCH.opts & P(lambda x: x is not None and len(x) > 1)), salience=110)
    def clarify_start(self, opts):
        self.response = f"Did you mean: {', '.join(opts)}?"

    @Rule(Session(to_options=MATCH.opts), salience=105)
    def clarify_destination(self, opts):
        if opts and isinstance(opts, list):
            self.response = f"Which destination did you mean: {', '.join(opts)}?"

    # Rules for missing info
    @Rule(Session(start=None), salience=100)
    def ask_start(self):
        if self.response is None:
            self.response = "Where are you travelling from?"

    @Rule(Session(end=None), salience=90)
    def ask_destination(self):
        if self.response is None:
            self.response = "Where are you travelling to?"

    @Rule(Session(date=None), salience=80)
    def ask_date(self):
        if self.response is None:
            self.response = "When do you want to travel?"

    @Rule(Session(ticket=None), salience=70)
    def ask_ticket(self):
        if self.response is None:
            self.response = "Is this a one way or return ticket?"

    @Rule(Session(ticket='return', return_date=None), salience=60)
    def ask_return_date(self):
        if self.response is None:
            self.response = "When are you returning?"

    #Rule for getting ready to book

    @Rule(Session(
    start=MATCH.start & P(lambda x: x is not None),
    end=MATCH.end & P(lambda x: x is not None),
    date=MATCH.date & P(lambda x: x is not None),
    ticket=MATCH.ticket & P(lambda x: x is not None)
    ), salience=10)
    def ready(self, start, end, date, ticket):
        if self.response is None:
            self.response = f"Booking {ticket} ticket from {start} to {end} on {date}"
            
def is_ready(journey):
    # must always have these
    if not all([
        journey["from"],
        journey["to"],
        journey["date"],
        journey["ticket_type"]
    ]):
        return False

    # extra requirement for returns
    if journey["ticket_type"] == "return":
        return journey["return_date"] is not None

    return True

def get_response(journey): #Function to actually request response
    engine = TrainBooker()
    engine.reset()

    engine.declare(Session(
        start=journey["from"],
        end=journey["to"],
        from_options=journey.get("from_options"),
        to_options=journey.get("to_options"),
        date=journey["date"],
        return_date=journey["return_date"],
        ticket=journey["ticket_type"]
    ))

    engine.run()
    
    #Check if ready
    if is_ready(journey):

        try:
            return fetch_ticket(journey)
        except Exception as e:
            print("DEBUG ERROR:", e)
            return f"BOT: I found your journey but couldn't retrieve ticket data."

    return engine.response

def build_booking_link(origin, dest, journey, best_departure):
    out_dt = best_departure

    out_date = out_dt.strftime("%d%m%y")
    out_time = out_dt.strftime("%H%M")

    # BASE URL
    base = f"https://ojp.nationalrail.co.uk/service/timesandfares/{origin}/{dest}/{out_date}/{out_time}/dep"

    # HANDLE RETURN
    if journey["ticket_type"] == "return" and journey["return_date"]:
        ret_dt = journey["return_date"]

        # merge return time if exists
        if journey["return_time"]:
            hour = int(journey["return_time"][:2])
            minute = int(journey["return_time"][2:])
            ret_dt = ret_dt.replace(hour=hour, minute=minute)
        else:
            ret_dt = ret_dt.replace(hour=9, minute=0)

        ret_date = ret_dt.strftime("%d%m%y")
        ret_time = ret_dt.strftime("%H%M")

        return f"{base}/{ret_date}/{ret_time}/dep"

    return base

def fetch_ticket(journey):

    from main import railway_stations  # or wherever it's stored

    origin_code = railway_stations[journey["from"]]
    dest_code = railway_stations[journey["to"]]

    # basic date parsing
    departure_dt = journey["date"]

    # If time exists, merge it in
    if journey["time"]:
        hour = int(journey["time"][:2])
        minute = int(journey["time"][2:])
        departure_dt = departure_dt.replace(hour=hour, minute=minute)
    else:
        # fallback so you don’t send 00:00 trains like a psychopath
        departure_dt = departure_dt.replace(hour=9, minute=0)

    journeys = get_journeys(origin_code, dest_code, departure_dt)

    if not journeys:
        return "BOT: No journeys found."

    parsed = parse_journeys(journeys, journey["ticket_type"])

    # apply time filters (your coursework requirement)
    if journey.get("time") == "before":
        parsed = [j for j in parsed if j["departure"].hour < 10]

    if journey.get("return_time") == "after":
        parsed = [j for j in parsed if j["departure"].hour >= 14]

    if not parsed:
        return "BOT: No trains match your time preference."

    best = find_cheapest(parsed)
    link = build_booking_link(origin_code, dest_code, journey, best["departure"])
    
    return f"""
BOT: Here's the best option I found:

From: {journey['from'].title()} → {journey['to'].title()}
Departure: {best['departure'].strftime('%H:%M')}
Arrival: {best['arrival'].strftime('%H:%M')}

Ticket: {best['fare_type']}
Price: {"£" + str(best['price']) if best['price'] else "Check online"}

Book here:
<a href="{link}">Book this journey</a>

"""