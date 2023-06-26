from pyproj import Transformer
from geopy import distance
import math
import requests
from helpers_geometry import calculate_quadrant_from_center

# Convert one point between different EPSG
# PARAMS:
# from_epgs, to_epgs: (string) the epsg formats to converto from/to (e.g. "EPSG:25833" )
# lat, lon of the point
# pyproj expects the input in the order of (longitude, latitude); always_xy switches that to (lat,lon)
# RETURNS: (lat, lon) of converted point
def convert_coords(from_epgs, to_epgs, lat, lon):
    #print("i: Convert coords")
    #transformer = Transformer.from_crs(from_epgs, to_epgs, always_xy=True)
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


# find length of adjacent to move pt along x+length_adjacent and with this new x value calculate y by using line equation
def shift_pt_along_street(origin_pt, x_angle, shift_length, slope, y_intercept):
    quadrant = calculate_quadrant_from_center([origin_pt])
    if slope == None: #parallel to y
        shifted_x = origin_pt[0]
        if quadrant in [1, 2]:
            shifted_y = origin_pt[1] + shift_length 
        if quadrant in [3, 4]:
            shifted_y = origin_pt[1] - shift_length
        return (shifted_x, shifted_y)
       
    elif slope == 0:
        shifted_y = origin_pt[1]
        if quadrant in [1, 4]:
            shifted_x = origin_pt[0] + shift_length
        if quadrant in [2, 3]:
            shifted_x = origin_pt[0] - shift_length
        return (shifted_x, shifted_y)

    elif slope > 0:
        length_adjacent = (math.cos(x_angle) * shift_length)
        if abs(math.degrees(x_angle)) <= 45:
            if quadrant in [1, 4]:
                shifted_x = origin_pt[0] + length_adjacent
            if quadrant in [2, 3]:
                shifted_x = origin_pt[0] - length_adjacent
          
        elif abs(math.degrees(x_angle)) > 45:
            if quadrant in [1, 2]:
                shifted_x = origin_pt[0] + length_adjacent
            elif quadrant in [3, 4]:
                shifted_x = origin_pt[0] - length_adjacent

    elif slope < 0:
        length_adjacent = (math.cos(x_angle) * shift_length)
        if abs(math.degrees(x_angle)) <= 45:
            if quadrant in [1, 4]:
                shifted_x = origin_pt[0] + length_adjacent
            elif quadrant in [2, 3]:
                shifted_x = origin_pt[0] - length_adjacent

        elif abs(math.degrees(x_angle)) > 45:
            if quadrant in [1, 2]:
                shifted_x = origin_pt[0] - length_adjacent
            elif quadrant in [3, 4]:
                shifted_x = origin_pt[0] + length_adjacent

    shifted_y = (slope * shifted_x) + y_intercept
    return (shifted_x, shifted_y)
