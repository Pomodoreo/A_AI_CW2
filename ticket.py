# This will be used for getting the ticket for the API

from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone

session = Session()
#session.auth = HTTPBasicAuth('etangka', '6Ci0#3')
session.auth = HTTPBasicAuth('wwang', '?i92S6')


settings = Settings(strict=False, xml_huge_tree=True)
wsdl_url = 'https://ojp.nationalrail.co.uk/webservices/jpservices.wsdl'
client = Client( wsdl_url, transport=Transport(session=session), settings=settings)

service = client.create_service(
    '{http://ojp.nationalrail.co.uk}jpservicesBinding',
    'https://ojp.nationalrail.co.uk/webservices/jpdlr.wsdl'
)
       
origin = 'WEH'
dest = 'UPM'
out_dt = datetime(2026, 5, 5, 15, 30, tzinfo=timezone.utc)
fare_class = 'STANDARD'
response = {
    'origin': {'stationCRS': origin},
    'destination': {'stationCRS': dest},
    'realtimeEnquiry': 'STANDARD',
    'outwardTime': {'departBy': out_dt},
    'fareRequestDetails': {
        'passengers': {'adult': 1, 'child': 0},
        'fareClass': fare_class
    },

    'directTrains': True,
}
response_print = client.service.RealtimeJourneyPlan(**response)
print(response_print)

def get_journeys(origin, dest, departure_dt):

    response = client.service.RealtimeJourneyPlan(
        origin={'stationCRS': origin},
        destination={'stationCRS': dest},
        realtimeEnquiry='STANDARD',
        outwardTime={'departBy': departure_dt},
        fareRequestDetails={
            'passengers': {'adult': 1, 'child': 0},
            'fareClass': 'STANDARD'
        },
        directTrains=True,
    )

    return response.outwardJourney

def parse_journeys(journeys, ticket_type):

    results = []

    for j in journeys:

        try:
            dep = j.timetable.scheduled.departure
            arr = j.timetable.scheduled.arrival
        except:
            continue  # skip broken entries

        price = None
        fare_name = None

        # fares may not exist or may be empty
        fares = getattr(j, "fare", [])

        if fares:

            if ticket_type in ["one way", "single"]:

                valid = [
                    f for f in fares
                    if getattr(f, "direction", None) == "OUTWARD"
                ]

            elif ticket_type in ["return", "round", "open return"]:

                valid = [
                    f for f in fares
                    if getattr(f, "direction", None) == "RETURN"
                ]

            else:
                valid = []

            if valid:
                cheapest = min(valid, key=lambda x: getattr(x, "totalPrice", float("inf")))

                raw_price = getattr(cheapest, "totalPrice", None)

                if raw_price is not None:
                    price = raw_price / 100
                    fare_name = getattr(cheapest, "description", "Unknown fare")

        results.append({
            "departure": dep,
            "arrival": arr,
            "price": price,
            "fare_type": fare_name
        })

    return results

def find_cheapest(journeys):

    # filter out journeys with no price
    priced = [j for j in journeys if j["price"] is not None]

    if priced:
        return min(priced, key=lambda x: x["price"])

    # fallback: choose earliest train
    return min(journeys, key=lambda x: x["departure"])