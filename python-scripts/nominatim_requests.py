import requests


# params: any String like "Volkmarsdorf" or even zipcodes like "04277"
def request_search(params):
    # url from webservice
    #URL = "https://nominatim.openstreetmap.org/search?q=" + params + "+Leipzig+Stadt&format=json"
    
    # url from local service
    URL = "http://localhost:8080/search?q=" + params + "+Leipzig+Stadt&format=json"
    response = requests.get(URL)
    if response.status_code == 200:
        return response

#http://localhost:8080/search?format=geojson&q=Eisenbahnstr,leipzig&dedupe=0&addressdetails=1&extratags=1


def request_lookup(id_type, osm_id, params):
    #URL = "http://localhost:8080/lookup?format=json&osm_ids="+ id_type + str(osm_id) + params
    URL = "https://nominatim.openstreetmap.org/lookup?format=json&osm_ids="+ id_type + str(osm_id) + params
    #print(URL)
    response = requests.get(URL)
    if response.status_code == 200:
        return response

