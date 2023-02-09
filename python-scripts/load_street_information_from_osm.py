from nominatim_requests import request_search
import pickle
import pandas as pd


def extract_information_from_response_item(street, item):  
        osm_t = item['properties']['osm_type']
        osm_id = item['properties']['osm_id']
        cat = item['properties']['category']
        tags = item['properties']['extratags']
        geom_type = item['geometry']['type']
        geom_coords = item['geometry']['coordinates']
        agg_info = {'street': street, 'osm_id': osm_id, 'osm_type':osm_t, 'category': cat, 'extratags': tags, 'geometry_type':geom_type, 'geom_coordinates': geom_coords}
        return agg_info


def get_osm_data_for_streets(streetnames_list):
    # for each street get all information from osm data
    street_items = []
    for street in streetnames_list:
        print("--------------"+street+"-----------")
        params = {'extratags': 1, 'addressdetails': 1}
        response = request_search(street, params)
        #print(response)
        for item in response['features']:
            agg_info = extract_information_from_response_item(street, item)
            street_items.append(agg_info)

    street_df = pd.DataFrame.from_records(street_items)
    return street_df

# load all streets from streetnames
streetnames_file = '../add-files/leipzig_streetnames_short.pkl'
with open(streetnames_file, 'rb') as file:
    streetnames = pickle.load(file)

street_df = get_osm_data_for_streets(streetnames)
print(street_df)

street_df.to_csv('../add-files/street_df.csv')

with open('../add-files/street_df.pkl', 'wb') as file:
    pickle.dump(street_df, file)



#https://nominatim.openstreetmap.org/search?q=Scharnhorststraße&viewbox=12.3784553167,51.319536207,12.3817032626,51.319498311