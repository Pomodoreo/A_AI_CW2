# This will be used for getting the ticket for the API

from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
from datetime import datetime

session = Session()
session.auth = HTTPBasicAuth('etangka', '6Ci0#3')

# session.headers.update({
#     'SOAPAction': 'RealtimeJourneyPlan'
# })


client = Client(
    'jpservices.wsdl.xml',
    transport=Transport(session=session)
)

service = client.create_service(
    '{http://ojp.nationalrail.co.uk}jpservicesBinding',
    'https://ojp.nationalrail.co.uk/webservices/jpdlr'
)


response = client.service.RealtimeJourneyPlan(
    origin={'stationCRS': 'NRW'},
    destination={'stationCRS': 'LST'},
    realtimeEnquiry='STANDARD',
    outwardTime={'departBy': datetime(2026, 4, 27, 10, 30)},
    directTrains=False
)

print(response)


# print(client.wsdl.services)
# print(client.service._operations)












#result = client.service.SomeMethod()
#print(client.wsdl.dump())
