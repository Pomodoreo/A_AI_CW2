# This will be used for getting the ticket for the API

from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone

session = Session()
#session.auth = HTTPBasicAuth('etangka', '6Ci0#3')
session.auth = HTTPBasicAuth('wwang', '?i92S6')

# session.headers.update({
#     'SOAPAction': 'RealtimeJourneyPlan'
# })


# client = Client(
#     'jpservices.wsdl',
#     transport=Transport(session=session)
# )

settings = Settings(strict=False, xml_huge_tree=True)
wsdl_url = 'https://ojp.nationalrail.co.uk/webservices/jpservices.wsdl'
client = Client( wsdl_url, transport=Transport(session=session), settings=settings)

service = client.create_service(
    '{http://ojp.nationalrail.co.uk}jpservicesBinding',
    'https://ojp.nationalrail.co.uk/webservices/jpdlr.wsdl'
)


# response = client.service.RealtimeJourneyPlan(
#     'origin':{'stationCRS': 'NRW'},
#     'destination':{'stationCRS': 'LST'},
#     'realtimeEnquiry':'STANDARD',
#     'outwardTime':{'departBy': datetime(2026, 5, 1, 10, 30, tzinfo=timezone.utc)},
#     'directTrains':True,
# )

       # Build base request
       
origin = 'NRW'
dest = 'LST'
out_dt = datetime(2026, 5, 3, 10, 30, tzinfo=timezone.utc)
fare_class = 'STANDARD'

response = {

    'origin': {'stationCRS': origin},

    'destination': {'stationCRS': dest},

    'realtimeEnquiry': 'STANDARD',

    'outwardTime': {'departBy': out_dt},

    # 'fareRequestDetails': {

    #     'passengers': {'adult': 1, 'child': 0},

    #     'fareClass': fare_class

    # },

    'directTrains': True,

}

response_print = client.service.RealtimeJourneyPlan(**response)
 

print(response_print)


# print(client.wsdl.services)
# print(client.service._operations)












#result = client.service.SomeMethod()
#print(client.wsdl.dump())
