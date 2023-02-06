import requests


# params: any String like "Volkmarsdorf" or even zipcodes like "04277"
def request_search(street, params):
    # url from webservice
    #URL = "https://nominatim.openstreetmap.org/search?q=" + params + "+Leipzig+Stadt&format=json"

    # url from local service
    request_url = "http://localhost:8080/search?q=" + street+ "+,Leipzig+Stadt&format=geojson"
                                                                                                                                                                                                                                                        
    if params:
        for key, value in params.items():
            request_url = request_url + '&' + str(key) + '=' + str(value)

    response = requests.get(request_url)
    if response.status_code == 200:
        return response.json()

#http://localhost:8080/search?format=geojson&q=Eisenbahnstr,leipzig&dedupe=0&addressdetails=1&extratags=1


def request_lookup(id_type, osm_id, params):
    #URL = "http://localhost:8080/lookup?format=json&osm_ids="+ id_type + str(osm_id) + params
    URL = "https://nominatim.openstreetmap.org/lookup?format=json&osm_ids="+ id_type + str(osm_id) + params
    #print(URL)
    response = requests.get(URL)
    if response.status_code == 200:
        return response

