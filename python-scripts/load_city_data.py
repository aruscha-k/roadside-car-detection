import json
import pandas as pd
from db_create_tables_load_data import load_data_into_tables
import handy_defs as hd
import folium

segments_file = './add-files/strassen_segmente_testgebiet.json'
vertice_file = './add-files/strassen_knoten_testgebiet.json'

# extract data from strassen_segmente_testgebiet.json - file the city sent us
def extract_segment_data(segments_json):
    #street_items = []
    #for feature in segments_json['features']:
    #    coords = feature['geometry']['coordinates']
    #    coords = [(item[1], item[0]) for item in coords]
    #    street_name = feature['properties']['str']
    #    obj_id = feature['properties']['objectid']
    #    from_street = feature['properties']['von_str']
    #    to_street = feature['properties']['bis_str']
    #    street_nr = feature['properties']['str_nr']
    #    street_type = feature['properties']['sstrgsname']
    #    length = feature['properties']['laenge_m']
    #    street_items.append({'street_nr': street_nr, 'street_name': street_name,'object_id': obj_id, 'street_type': street_type, 'from_str': from_street, 'to_street': to_street, 'coords': coords, 'length': length})
    #
    #street_df = pd.DataFrame.from_records(street_items)
    #return street_df

    #segment_ids = None # was sind die ids 
    #segment_street_ids
    #segment_street_types
    #segment_geometrys
    #segment_length_ms
    #street_ids
    #street_names
    #tag_ids
    #tag_keys
    #tag_values
    #tag_segment_ids

# extract data from strassen_knoten_testgebiet.json - file the city sent us
def extract_vertice_data(vertices_json):
    vertice_items = []
    for feature in vertices_json['features']:
        coords = feature['geometry']['coordinates']
        coords = (coords[1], coords[0])
        obj_id = feature['properties']['objectid']
        vertice_items.append({'obj_id': obj_id, 'coords': coords})
    vertice_df = pd.DataFrame.from_records(vertice_items)
    return vertice_df




segments_json = hd.load_json(segments_file, 'rb')
vertices_json = hd.load_json(vertice_file, 'rb')

#street_df = extract_segment_data(segments_json)

