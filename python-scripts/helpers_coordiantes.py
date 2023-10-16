from pyproj import Transformer
from geopy import distance
import math
from shapely.geometry import Point, Polygon
from helpers_geometry import calculate_quadrant_from_center


def convert_coords(from_epsg, to_epsg, lat, lon):
    """ convert one coordante point from / to different EPSGs
    Args:
        from_epsg (string): epsg number described in PyProj (e.g. "EPSG:25833")
        to_epsg (string): epsg number described in PyProj (e.g. "EPSG:25833")
        lat (float): Lat coord of src epsg
        lon (float): Lom coord of src epsg

    Returns:
        tuple: transformed coordinate tuple
    """

    transformer = Transformer.from_crs(from_epsg, to_epsg)

    trans_lat, trans_lon = transformer.transform(lat, lon)
    #print(f" conv cords: {trans_lat, trans_lon}")
    return (trans_lat, trans_lon)


def sort_coords(converted_coords, start_pt):
    """ sorts the coordinate list so that the start_pt is on index 0

    Args:
        converted_coords (list): of coordinate points
        start_pt (tuple): of lat,lon

    Returns:
        list: ordered list, where startpoint is on index 0 and end point is on index -1
    """
    if converted_coords[0] == start_pt:
        return converted_coords
    elif converted_coords[-1] == start_pt:
        return list(reversed(converted_coords))
    else:
        #TODO
        print("!!!!! COORDS NOT ORDERED LIKE THAT")
        return []
    

def calulate_distance_of_two_coords(coord1, coord2):
    """ calculate distance in m between two coordinates

    Args:
        coord1 ((lat,lon)): point1
        coord2 ((lat,lon)): point 2

    Returns:
        float: distance between two points in m
    """
    trans_coord1_lat , trans_coord1_lon = convert_coords("EPSG:25833", "EPSG:4326", coord1[0], coord1[1])
    trans_coord2_lat , trans_coord2_lon = convert_coords("EPSG:25833", "EPSG:4326", coord2[0], coord2[1])

    # default ellipsoid = WGS-84
    dist = distance.distance((trans_coord1_lat, trans_coord1_lon), (trans_coord2_lat, trans_coord2_lon)).m
    return dist


def shift_pt_along_street(origin_pt, x_angle, shift_length, slope, y_intercept):
    """ Method to shift a point along a line of a street with a specified shift length, calculates new (x,y) value using line equation
        is used to get all cyclomedia recording points within a street segment
        different cases a differentiated between regarding the alignment and position of the street segment in the coordinates system

    Args:
        origin_pt (tuple): point to shift from
        x_angle (float): angle in degrees of the deviation from x-axis
        shift_length (int): in meters, length to shift points with
        slope (float): slope of the line representing the street
        y_intercept (float): point at which line crosses y-axis

    Returns:
        tuple: the shifted point
    """
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


def is_point_within_polygon(point_coordinates, polygon_coordinates):
    """ helper function for cyclomedia to determine, if the recording location is within the iteration polygon
    Args:
        point_coordinates (tuple): point of the recording position
        polygon_coordinates (list): list of points of the iteration poly

    Returns:
        bool: if the point lies withing the polygon
    """
    point = Point(point_coordinates)
    polygon = Polygon(polygon_coordinates)
    #print(f"point lies within: {polygon.contains(point)} ")
    
    return polygon.contains(point)