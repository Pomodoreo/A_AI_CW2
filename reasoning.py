# reasoning.py
# Reasoning Engine here is the Expert System rule base for the Train Ticket Chatbot
# Implements the chaining forward rule engine using the experta library
# Rules are evaluated by salience (which is priority); for only the rules with the highest matching
# This helps produce a response per turn and is enforced via the `if self.response is None` guard

from experta import *
import datetime


class Session(Fact):
    """
    This holds the current state of the booking conversation as a single Fact.
    All fields are passed in from the journey dictionary each turn.
    """
    pass


class TrainBooker(KnowledgeEngine):

    def __init__(self):
        super().__init__()
        self.response = None

    # The greeting (salience 200)
    # It fires exactly once, when every journey field is still empty
    # is_first is injected by get_response() rather than NLP, so it won't accidentally retrigger once any field has been populated

    @Rule(Session(is_first=True), salience=200)
    def greet(self):
        if self.response is None:
            self.response = (
                "Hello, welcome to the Train Ticket Chatbot.\n"
                "I can help you find the cheapest available train tickets across the UK.\n\n"
                "To get started, where would you like to travel from?"
            )

    # Clarification Rules (salience 130–120)
    # This fires when NLP found multiple possible station matches so the user can disambiguate before moving move on

    @Rule(
        Session(from_options=MATCH.opts & P(lambda x: x is not None and isinstance(x, list) and len(x) > 1)),
        salience=130
    )
    def clarify_start(self, opts):
        if self.response is None:
            # There is a cap at 6 to avoid wall of text
            listed = "\n  - ".join(opts[:6])
            self.response = (
                "I found several stations that could be your departure point. "
                "Which one did you mean?\n  - " + listed + "\n\n"
                "(Just type the name or its station code.)"
            )

    @Rule(
        Session(
            to_options=MATCH.opts & P(lambda x: x is not None and isinstance(x, list) and len(x) > 1)),
        salience=120
    )
    def clarify_destination(self, opts):
        if self.response is None:
            listed = "\n  - ".join(opts[:6])
            self.response = (
            "I found several stations that could be your destination. "
            "Which one did you mean?\n  - " + listed + "\n\n"
            "(Just type the name or its station code.)"
        )

    # Missing Info Rules (salience 100–50)
    # Each rule only fires when earlier steps are complete
    # It's now required that no ambiguous options list is pending

    # Departure station
    @Rule(
        Session(
            start=None,
            from_options=P(
                lambda x: x is None or (isinstance(x, list) and len(x) <= 1)
            )
        ),
        salience=100
    )
    def ask_start(self):
        if self.response is None:
            self.response = "Where would you like to travel from?"

    # Destination station
    @Rule(
        Session(
            start=MATCH.start & P(lambda x: x is not None),
            end=None,
            to_options=P(lambda x: x is None or (isinstance(x, list) and len(x) <= 1))
        ),
        salience=90
    )
    def ask_destination(self, start):
        if self.response is None:
            self.response = (
                "Got it, departing from " + start.title() + ".\n"
                "Where would you like to travel to?"
            )

    # Ticket type
    @Rule(
        Session(
            start=MATCH.s & P(lambda x: x is not None),
            end=MATCH.e & P(lambda x: x is not None),
            ticket=None
        ),
        salience=80
    )
    def ask_ticket(self, s, e):
        if self.response is None:
            self.response = (
            "Is this a one-way or return journey from "
            + s.title() + " to " + e.title() + "?\n"
            "  - one way\n  - return\n  - open return"
        )

    # Outbound date
    @Rule(
        Session(
            start=MATCH.s & P(lambda x: x is not None),
            end=MATCH.e & P(lambda x: x is not None),
            ticket=MATCH.t & P(lambda x: x is not None),
            date=None
        ),
        salience=70
    )
    def ask_date(self):
        if self.response is None:
            self.response = (
                "What date would you like to travel?\n"
                "(e.g. '15th July', 'tomorrow', 'next Monday')"
            )

    # Outbound time
    # Test case example: "hoping to depart before 10am"
    # Asking for it explicitly covers this particular scenario
    @Rule(
        Session(
            start=MATCH.s & P(lambda x: x is not None),
            end=MATCH.e & P(lambda x: x is not None),
            ticket=MATCH.t & P(lambda x: x is not None),
            date=MATCH.d & P(lambda x: x is not None),
            time=None
        ),
        salience=60
    )
    def ask_time(self):
        if self.response is None:
            self.response = (
                "What time would you like to depart?\n"
                "(e.g. '08:30', 'before 10am', 'morning', or say 'any' for no preference)"
            )

    # Return date (such as return / open return tickets only)
    @Rule(
        Session(
            ticket=MATCH.t & P(lambda x: x in ['return', 'open return']),
            return_date=None
        ),
        salience=55
    )
    def ask_return_date(self):
        if self.response is None:
            self.response = (
                "What date would you like to return?\n"
                "(e.g. '17th July', 'two days later', 'next Friday')"
            )

    # Return time (return / open return tickets only)
    # Test case example: "come back from Oxford in the afternoon"
    @Rule(
        Session(
            ticket=MATCH.t & P(lambda x: x in ['return', 'open return']),
            return_date=MATCH.rd & P(lambda x: x is not None),
            return_time=None
        ),
        salience=50
    )
    def ask_return_time(self):
        if self.response is None:
            self.response = (
                "What time would you like to return?\n"
                "(e.g. '14:00', 'after 2pm', 'afternoon', or say 'any' for no preference)"
            )

    # Ready Rules (salience 15)
    # Separating rules for one-way and return so that the conditions are precise

    @Rule(
        Session(
            start=MATCH.start   & P(lambda x: x is not None),
            end=MATCH.end       & P(lambda x: x is not None),
            date=MATCH.date     & P(lambda x: x is not None),
            ticket=MATCH.ticket & P(lambda x: x in ['one way', 'open ticket']),
            time=MATCH.time     & P(lambda x: x is not None),
            from_options=P(lambda x: x is None),
            to_options=P(lambda x: x is None)
        ),
        salience=15
    )
    def ready_one_way(self, start, end, date, ticket, time):
        if self.response is None:
            time_fmt = _fmt_time(time)
            date_fmt = _fmt_date(date)
            self.response = (
            "Great, I have everything I need. Here is your journey summary:\n\n"
            "Ticket type: " + ticket.title() + "\n"
            "From: " + start.title() + "\n"
            "To: " + end.title() + "\n"
            "Date: " + date_fmt + "\n"
            "Depart: " + time_fmt + "\n\n"
            "Searching for the cheapest available ticket..."
        )

    @Rule(
        Session(
            start=MATCH.start           & P(lambda x: x is not None),
            end=MATCH.end               & P(lambda x: x is not None),
            date=MATCH.date             & P(lambda x: x is not None),
            ticket=MATCH.ticket         & P(lambda x: x in ['return', 'open return']),
            time=MATCH.time             & P(lambda x: x is not None),
            return_date=MATCH.ret_date  & P(lambda x: x is not None),
            return_time=MATCH.ret_time  & P(lambda x: x is not None),
            from_options=P(lambda x: x is None),
            to_options=P(lambda x: x is None)
        ),
        salience=15
    )
    def ready_return(self, start, end, date, ticket, time, ret_date, ret_time):
        if self.response is None:
            dep_fmt = _fmt_time(time)
            ret_fmt = _fmt_time(ret_time)
            date_fmt = _fmt_date(date)
            ret_date_fmt = _fmt_date(ret_date)
            self.response = (
                "Great, I have everything I need. Here is your journey summary:\n\n"
                "Ticket type: " + ticket.title() + "\n"
                "From: " + start.title() + "\n"
                "To: " + end.title() + "\n"
                "Outbound: " + date_fmt + " at " + dep_fmt + "\n"
                "Return: " + ret_date_fmt + " at " + ret_fmt + "\n\n"
                "Searching for the cheapest available ticket..."
            )




    # Fallback Rule  (salience 0)
    # This fires last, only if no higher-priority rule produced a response.

    @Rule(AS.f << Session(), salience=0)
    def fallback(self, f):
        if self.response is None:
            self.response = (
                "Sorry, I didn't quite understand that. "
                "Could you rephrase, or try giving me a station name, date, or ticket type? "
                "I'm here to help you find the cheapest UK train tickets."
            )



# Helper formatters (module-level)

def _fmt_time(time_val):
    """Convert '1000' to '10:00', pass through 'any' or other strings."""
    if not time_val:
        return "any"
    if isinstance(time_val, str) and len(time_val) == 4 and time_val.isdigit():
        return time_val[:2] + ":" + time_val[2:]
    return str(time_val)


def _fmt_date(date_val):
    """Format a datetime object or string for display."""
    if not date_val:
        return "not set"
    if isinstance(date_val, datetime.datetime):
        return date_val.strftime("%A %d %B %Y")
    return str(date_val)


# Public interface

def get_response(journey):
    engine = TrainBooker()
    engine.reset()

    # Detect the very first turn where nothing has been collected yet
    all_fields = ["from", "to", "date", "return_date", "time", "return_time", "ticket_type"]
    is_first = (
        all(journey.get(k) is None for k in all_fields)
        and journey.get("from_options") is None
        and journey.get("to_options") is None
    )

    engine.declare(Session(
        # Core journey fields
        start=journey.get("from"),
        end=journey.get("to"),
        date=journey.get("date"),
        return_date=journey.get("return_date"),
        ticket=journey.get("ticket_type"),
        time=journey.get("time"),
        return_time=journey.get("return_time"),
        from_options=journey.get("from_options"),
        to_options=journey.get("to_options"),
        is_first=is_first
    ))

    engine.run()

    # A safety net, if the engine somehow produced nothing, a fallback text is given
    if engine.response is None:
        engine.response = (
            "Sorry, I didn't quite understand that. Could you rephrase? "
            "I can help you find the cheapest UK train tickets."
        )

    return engine.response
