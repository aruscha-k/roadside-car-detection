import json
import pandas as pd
from db_create_tables_load_data import load_data_into_tables

import folium

segments_file = './add-files/strassen_segmente_testgebiet.json'
vertice_file = './add-files/strassen_knoten_testgebiet.json'

with open(segments_file, 'rb') as f1:
    segments_json = json.load(f1)

with open(vertice_file, 'rb') as f2:
    vertices_json = json.load(f2)    

# extract data from strassen_segmente_testgebiet.json - file the city sent us
def extract_segment_data(segments_json):
    street_items = []
    for feature in segments_json['features']:
        coords = feature['geometry']['coordinates']
        coords = [(item[1], item[0]) for item in coords]
        street_name = feature['properties']['str']
        obj_id = feature['properties']['objectid']
        from_street = feature['properties']['von_str']
        to_street = feature['properties']['bis_str']
        street_nr = feature['properties']['str_nr']
        street_type = feature['properties']['sstrgsname']
        length = feature['properties']['laenge_m']
        street_items.append({'street_nr': street_nr, 'street_name': street_name,'object_id': obj_id, 'street_type': street_type, 'from_str': from_street, 'to_street': to_street, 'coords': coords, 'length': length})
    
    street_df = pd.DataFrame.from_records(street_items)
    return street_df

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



street_df = extract_segment_data(segments_json)
#vertice_df = extract_vertice_data(vertices_json)

# load the relevant data into DB tables
#load_data_into_tables(temp[["street_nr", "street_name"]].loc[~street_df['street_name'].str.contains("Parkplatz")])



# --- just for debugging ---
# plot segments and vertices on a map 

center = [51.322523347273126, 12.375431206686596]
map_leipzig = folium.Map(location=center, zoom_start=16)
for index, row in street_df.loc[~street_df['street_name'].str.contains("Parkplatz")].iterrows():
    coords = row['coords']
    if index%2 == 0:
        color = 'red'
    else:
        color = 'blue'
    folium.PolyLine(coords, color=color).add_to(map_leipzig)
    folium.Marker(coords[0],
                  popup=row['street_name']).add_to(map_leipzig)

# for index, row in vertice_df.iterrows():
#     coords = row['coords']
#     folium.Marker(coords).add_to(map_leipzig)

# save map to html file
map_leipzig.save('index.html')