from pyproj import Transformer
from geopy import distance

# Convert one point between different EPSG
# PARAMS:
# from_epgs, to_epgs: (string) the epsg formats to converto from/to (e.g. "EPSG:25833" )
# lat, lon of the point
# RETURNS: (lat, lon) of converted point
def convert_coords(from_epgs, to_epgs, lat, lon):
    #print("i: Convert coords")
    transformer = Transformer.from_crs(from_epgs, to_epgs)
    trans_lat, trans_lon = transformer.transform(lat, lon)
    #print(f" conv cords: {trans_lat, trans_lon}")
    return (trans_lat, trans_lon)


# sorts the coordinates so that the start_pt is on index 0
def sort_coords(converted_coords, start_pt):
    if converted_coords[0] == start_pt:
        return converted_coords
    elif converted_coords[-1] == start_pt:
        return list(reversed(converted_coords))
    else:
        print("!!!!! COORDS NOT ORDERED LIKE THAT")
        return []


# calculate distance in m between two coordinates
# PAMARS:
# coords: coords as (lat,lon)
# RETURNS
# distance: in meters
def calulate_distance_of_two_coords(coord1, coord2):
    trans_coord1_lat , trans_coord1_lon = convert_coords("EPSG:25833", "EPSG:4326", coord1[0], coord1[1])
    trans_coord2_lat , trans_coord2_lon = convert_coords("EPSG:25833", "EPSG:4326", coord2[0], coord2[1])

    # default ellipsoid = WGS-84
    dist = distance.distance((trans_coord1_lat, trans_coord1_lon), (trans_coord2_lat, trans_coord2_lon)).m
    return dist