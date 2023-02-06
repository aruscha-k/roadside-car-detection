from nominatim_requests import request_search
import pickle
import pandas as pd


# load all streets from streetnames
streetnames_file = '../add-files/leipzig_streetnames_short.pkl'
with open(streetnames_file, 'rb') as file:
    streetnames = pickle.load(file)

def extract_information_from_response(item):  
        osm_t = item['properties']['osm_type']
        osm_id = item['properties']['osm_id']
        cat = item['properties']['category']
        tags = item['properties']['extratags']
        geom_type = item['geometry']['type']
        geom_coords = item['geometry']['coordinates']
        agg_info = [{'osm_type':osm_t, 'osm_id': osm_id, 'category': cat, 'extratags': tags, 'geometry_type':geom_type, 'geom_coordinates': geom_coords}]
        return agg_info

  
# for each street get all information from osm data
for street in streetnames:
    street_info = dict()
    print("--------------"+street+"-----------")
    params = {'extratags': 1, 'addressdetails': 1}
    response = request_search(street, params)
    #print(response)
    for item in response['features']:
        street_items = []
        agg_info = extract_information_from_response(item)
        street_items.append(agg_info)
    street_info[street] = street_info

    street_df = pd.DataFrame.from_dict(agg_info)
print(street_df)

with open('../add-files/street_df.pkl', 'wb') as file:
    pickle.dump(street, file)

    
