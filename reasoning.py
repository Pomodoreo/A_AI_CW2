# This is for deciding what the chatbot is going to say
from experta import *

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

    return engine.response