# This will be used for getting the ticket for the API

from zeep import Client

client = Client('jpservices.wsdl.xml')

#result = client.service.SomeMethod()
print(client.wsdl.dump())
