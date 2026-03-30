from bs4 import BeautifulSoup
import requests

url = "https://en.wikipedia.org/wiki/UK_railway_stations_%E2%80%93_"
alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

headers = requests.utils.default_headers()
headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
})

for letter in alphabet:
    response = requests.get(url + letter, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    # find all tr tags that have a "vcard" class
    station_list = soup.find_all('tr', {'class': 'vcard'})
    for station in station_list:
        # find the first span tag that has a "fn n org" class
        station_name = station.find('span', {'class': 'fn n org'})
        station_code = station.find('span', {'class': 'nickname'})
        if station_name:
            #print(station_name.text.strip(), station_code.text.strip() if station_code else "N/A")
            #Store in a text file with the format "station name | station code"
            with open('uk_railway_stations.txt', 'a') as file:
                file.write(station_name.text.strip() + ' | ' + (station_code.text.strip() if station_code else "N/A") + '\n')
    