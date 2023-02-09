from nominatim_requests import request_search
import pickle
import pandas as pd


def extract_information_from_response_item(item):  
        osm_t = item['properties']['osm_type']
        osm_id = item['properties']['osm_id']
        cat = item['properties']['category']
        tags = item['properties']['extratags']
        agg_info = {'osm_id': osm_id, 'osm_type':osm_t, 'category': cat}
        for key, val in tags.items():
            agg_info[key] = val

        return agg_info


# run a nominatim search for a street segment
# PARAMS:
#  street_name (string) name of the street 
#  segment_start_point/segment_end_point (float,float) of segment starting/ending point
#
def get_osm_data_for_segment(street_name, segment_start_point, segment_end_point):
    # for each street get all information from osm data
    street_items = []
    
    params = {'extratags': 1, 'addressdetails': 1, 'viewbox': str(segment_start_point[0])+","+str(segment_start_point[1])+","+str(segment_end_point[0])+","+str(segment_end_point[1])}
    response = request_search(street_name, params)

    for item in response['features']:
        agg_info = extract_information_from_response_item(item)
        street_items.append(agg_info)

    street_df = pd.DataFrame.from_records(street_items)
    print(street_df)
  


if __name__ == "__main__":
    get_osm_data_for_segment("Scharnhorststraße", (12.3784553167,51.319536207), (12.3817032626,51.319498311))