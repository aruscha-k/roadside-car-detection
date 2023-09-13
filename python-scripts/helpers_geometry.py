import math
import numpy as np


from GLOBAL_VARS import CITY_CENTERPT_LEIPZIG


#TODO delete? new method from miriam!
# PARAMS:
#  str_pts: 2 points of the beginning and end of street
# RETURNS:
#  arcos: angle to y axis in -> radians <-
# https://math.stackexchange.com/questions/714378/find-the-angle-that-creating-with-y-axis-in-degrees
def find_angle_to_y(str_pts):
    start_pt, end_pt = str_pts[0], str_pts[1]
    y1 = max([start_pt[1], end_pt[1]])
    y2 = min([start_pt[1], end_pt[1]])  
    arcos = math.acos((y1-y2)/math.sqrt((start_pt[0]-end_pt[0])**2 + (y1-y2)**2))
    print("Angle to y in degrees:", math.degrees(arcos))
    return arcos


#TODO
# between two points, find the angle of the line they construct to the x-axis
# source https://stackoverflow.com/questions/41855261/calculate-the-angle-between-a-line-and-x-axis
# !!! check coordinate reference system => different results for same coordinates in differen coordinate system
# !!! EPSG4326 returns angle in degrees, EPSG25833 returns angle in radian
# PARAMS: 
# str_pts (list) of two points
# RETURNS: angle in radians!
def find_angle_to_x(str_pts):
    start_pt, end_pt = str_pts[0], str_pts[-1]
    m = calculate_slope([start_pt, end_pt])
    if m == None:
        return math.radians(90)
    elif m == 0:
        return math.radians(0)
    else:
        # print(f"angle to x: {math.degrees(math.atan(m))}")
        return math.atan(m)
    

def unit_vector(vector):
    """
    normalizes a given vector to a length of one
    :param vector: any vector
    :return: its unit vector
    """
    if len(vector) == 0:
        return 0
    return vector / np.linalg.norm(vector)


# resulting angle will be in the range of -180° to 180°, where positive angles indicate counter-clockwise rotation from the y-axis (north direction),
# and negative angles represent a rotation in the clockwise direction
# CYCLOMEDIA GENAU ANDERS HERUM!
def calculate_street_deviation_from_north(start_pt, end_pt):
    v0 = [0, 1]
    v1 = unit_vector([end_pt[0] - start_pt[0], end_pt[1] - start_pt[1]])
    determinant = np.linalg.det([v0, v1])
    dot_product = np.dot(v0, v1)
    angle = np.math.atan2(determinant, dot_product)
    print("Deviation from north:", -np.degrees(angle))

    return -np.degrees(angle)


def calculate_quadrant_from_center(str_pts):
    """ given a specific point for a cities center, calculate in which quadrant a street lies, when point of origin is city center

    Args:
        str_pts (list): 2 points of the beginning (index = 0) and end (index=1) of street

    Returns:
        int: quadrant between 1-4 according to the naming of quadrants anti-clockwise
    """
    x = str_pts[0][0]
    y = str_pts[0][1]
    origin_x = CITY_CENTERPT_LEIPZIG[0]
    origin_y = CITY_CENTERPT_LEIPZIG[1]

    if x > origin_x and y > origin_y:
        quadrant = 1
    elif x < origin_x and y > origin_y:
        quadrant = 2
    elif x < origin_x and y < origin_y:
        quadrant = 3
    elif x > origin_x and y < origin_y:
        quadrant = 4
    else:
        print("[!!] Quadrant = Origin")

    return quadrant


def calculate_start_end_pt(str_pts):
    """method to determine the start and endpoint of a line according to this projects definition (s.WIKI) according to slope and quadrant the street lies in, starting point is the one closest to city center

    Args:
        str_pts (list): street points

    Returns:
        str_start (float, float): start point
        str_end (float, float): end point
    """
    #print(f"i: Calc start and end point for: {str_pts}")
    x_angle = find_angle_to_x(str_pts)
    slope = calculate_slope(str_pts)
    quadrant = calculate_quadrant_from_center(str_pts)

    # if street parallel to y
    if slope == None:
        if str_pts[-1][1] > CITY_CENTERPT_LEIPZIG[1]:
            str_start = min(str_pts, key=lambda x: x[1])
            str_end = max(str_pts, key=lambda x: x[1])
        else:
            str_start = max(str_pts, key=lambda x: x[1])
            str_end = min(str_pts, key=lambda x: x[0])

    # if street parallel to x
    elif slope == 0:
        if str_pts[-1][0] > CITY_CENTERPT_LEIPZIG[0]:
            str_start = min(str_pts, key=lambda x: x[0])
            str_end = max(str_pts, key=lambda x: x[0])
        else:
            str_start = max(str_pts, key=lambda x: x[0])
            str_end = min(str_pts, key=lambda x: x[0])

    elif slope > 0:
        if abs(math.degrees(x_angle)) <= 45:
            if quadrant in [1, 4]:
                str_start = min(str_pts, key=lambda x: x[0])
                str_end = max(str_pts, key=lambda x: x[0])
            elif quadrant in [2, 3]:
                str_start = max(str_pts, key=lambda x: x[0])
                str_end = min(str_pts, key=lambda x: x[0])
        elif abs(math.degrees(x_angle)) > 45:
            if quadrant in [1, 2]:
                str_start = min(str_pts, key=lambda x: x[0])
                str_end = max(str_pts, key=lambda x: x[0])
            elif quadrant in [3, 4]:
                str_start = max(str_pts, key=lambda x: x[0])
                str_end = min(str_pts, key=lambda x: x[0])

    elif slope < 0:
        if abs(math.degrees(x_angle)) <= 45:
            if quadrant in [1, 4]:
                str_start = min(str_pts, key=lambda x: x[0])
                str_end = max(str_pts, key=lambda x: x[0])
            elif quadrant in [2, 3]:
                str_start = max(str_pts, key=lambda x: x[0])
                str_end = min(str_pts, key=lambda x: x[0])

        elif abs(math.degrees(x_angle)) > 45:
            if quadrant in [1, 2]:
                str_start = max(str_pts, key=lambda x: x[0])
                str_end = min(str_pts, key=lambda x: x[0])
            elif quadrant in [3, 4]:
                str_start = min(str_pts, key=lambda x: x[0])
                str_end = max(str_pts, key=lambda x: x[0])

    return str_start, str_end


# method to use, when getting images from cyclomedia: for this a segment has to be iterated by x meters along the street
# this method helps choosing the right condition regarding quadrant and slope of the street
# PARAMS:
#   slope: slope of the line of the street
#   x_angle: the angle of the street to the x axis in degrees (TODO CHECK)
#   str_start, str_end: tuple of (lon, lat) each
#   x_shifted, y_shifted: the current shift point as (lon, lat)
# RETURNS:
#   True/False (bool): for the while-loop in which the shifting happens
def segment_iteration_condition(slope, x_angle, str_start, str_end, x_shifted, y_shifted):
    quadrant = calculate_quadrant_from_center([str_start, str_end])
    # street parallel to y; endpoint is dependent on y-value
    if slope == None:
        if y_shifted > CITY_CENTERPT_LEIPZIG[1]:
            while y_shifted < str_end[1]:
                return True
            else:
                return False
        else:
            while y_shifted > str_end[1]:
                return True
            else:
                return False

    # if street parallel to x; endpoint is dependent on x-value
    elif slope == 0:
        if x_shifted > CITY_CENTERPT_LEIPZIG[0]:
            while x_shifted < str_end[0]:
                return True
            else:
                return False
        else:
            while x_shifted > str_end[0]:
                return True
            else:
                return False

    elif slope > 0:
        if abs(math.degrees(x_angle)) <= 45:
            if quadrant in [1, 4]:
                while x_shifted < str_end[0]:
                    return True
                else:
                    return False
            if quadrant in [2, 3]:
                while x_shifted > str_end[0]:
                    return True
                else:
                    return False
        elif abs(math.degrees(x_angle)) > 45:
            if quadrant in [1, 2]:
                while x_shifted < str_end[0]:
                    return True
                else:
                    return False
            if quadrant in [3, 4]:
                while x_shifted > str_end[0]:
                    return True
                else:
                    return False

    elif slope < 0:
        if abs(math.degrees(x_angle)) <= 45:
            if quadrant in [1, 4]:
                while x_shifted < str_end[0]:
                    return True
                else:
                    return False
            if quadrant in [2, 3]:
                while x_shifted > str_end[0]:
                    return True
                else:
                    return False
        elif abs(math.degrees(x_angle)) > 45:
            if quadrant in [1, 2]:
                while x_shifted > str_end[0]:
                    return True
                else:
                    return False
            if quadrant in [3, 4]:
                while x_shifted < str_end[0]:
                    return True
                else:
                    return False


def calculate_slope(linepts: list):
    """ Calculate a slope of a line (! uses the first and last point, so order if needed)
    !!! check coordinate reference system => different results for coordinates in different coordinate systems (EPSG4326 or EPSG 25833)

    Args:
        linepts (list): of points

    Returns:
        float: slope if successfull
    """
    if len(linepts) > 0:
        first_pt = linepts[0]
        last_pt = linepts[-1]
        x1, y1 = first_pt[0], first_pt[1]
        x2, y2 = last_pt[0], last_pt[1]

        # check if lines is parallel to y
        if abs(x1 - x2) < 0.0000001:
           # print("parallel to y")
            return None
        
        # check if the line is parallel to x 
        if abs(x2 - x1) > 0.0000001:
            #print((y2 - y1) / (x2 - x1))
            return (y2 - y1) / (x2 - x1)
        else:
            return 0
        
    else:
        print("[!] calculate slope: empty list")


def get_y_intercept(pt, slope):
    """given a point and a slope of a line, calculate the y-intercept of the line

    Args:
        pt (tuple): pt in the line
        slope (float): slope of the line

    Returns:
        float: y value of y-intercept 
    """
    b = (-pt[0] * slope) + pt[1]
    return b


def calc_perpendicular(str_pts):
    """given a list of two points (start and end point) of a line, this method calculates the perpendicular (lotgerade) of the line at the start and end point

    Args:
        str_pts (list): of two points

    Returns:
        pm (float): slope of the perpendicular
        b_start/b_end (float): y value of y-intercept of the start / end point
    """
    start_pt, end_pt = str_pts[0], str_pts[1]
    m = calculate_slope(str_pts)
    pm = -(1/m)
    b_start = get_y_intercept(start_pt, pm)
    b_end = get_y_intercept(end_pt, pm)
    return pm, b_start, b_end


def calc_interception_of_two_lines(m1, b1, m2, b2):
    """ given the slope and y intercept of two lines, this method calculates the interception point

    Args:
        m1 (float): slope of first line
        b1 (float): y-intercept of first line
        m2 (float): slope of second line
        b2 (float): y-intercept of second line

    Returns:
        (x,y): point of interception
    """
    x = (b2-b1) / (m1-m2)
    y = m1 * x + b1

    return (x,y)


def calculate_bounding_box(str_pts, width):
    """ given two points and the wanted width calculate two parallel lines and perpendiculars so get a bounding box for a street segment function cant be joined with calculate_start_end segments, because it is used on iteration of segmentated semgents => more detailed

    Args:
        str_pts (list): of two points
        width (float): width of the street

    Returns:
        list: bbox with points in order [start_left, end_left, end_right, start_right]
    """
   
    # slope of original line
    slope_origin = calculate_slope(str_pts)
    #if street parallel to y-axis
    if slope_origin == None:
        if str_pts[0][1] > CITY_CENTERPT_LEIPZIG[1]:
            start_left = (str_pts[0][0] - (width/2), str_pts[0][1])
            end_left = (str_pts[1][0] - (width/2), str_pts[1][1])
            end_right = (str_pts[1][0] + (width/2), str_pts[1][1])
            start_right = (str_pts[0][0] + (width/2), str_pts[0][1])
   
        else:
            start_left = (str_pts[0][0] + (width/2), str_pts[0][1])
            end_left = (str_pts[1][0] + (width/2), str_pts[1][1])
            end_right = (str_pts[1][0] - (width/2), str_pts[1][1])
            start_right = (str_pts[0][0] - (width/2), str_pts[0][1])
        bounding_box = [start_left, end_left, end_right, start_right]
        return bounding_box
        
    # if street parallel to x
    elif slope_origin == 0:
        b_origin = get_y_intercept(str_pts[0], slope_origin) 
        if str_pts[0][0] > CITY_CENTERPT_LEIPZIG[0]:
            start_left = (str_pts[0][0], b_origin + (width/2))
            end_left = (str_pts[1][0], b_origin + (width/2))
            end_right = (str_pts[1][0], b_origin - (width/2))
            start_right = (str_pts[0][0], b_origin - (width/2))
       
        else:
            start_left = (str_pts[0][0], b_origin - (width/2))
            end_left = (str_pts[1][0], b_origin - (width/2))
            end_right = (str_pts[1][0], b_origin + (width/2))
            start_right = (str_pts[0][0], b_origin + (width/2))
        bounding_box = [start_left, end_left, end_right, start_right]
        return bounding_box


    # y intercept of original line, angle to x-axis of original line
    
    b_origin = get_y_intercept(str_pts[0], slope_origin) 
    x_angle = find_angle_to_x(str_pts)

   # calc y intercept of parallel line: parallel line has slope of m_origin
    new_width = width/2 * math.sqrt((slope_origin**2) + 1)
    b_parallel_below = (b_origin-new_width)
    b_parallel_above = (b_origin+new_width)

    # calc perpendiculars for start point and endpoints
    m_perpendicular, b_perpend_start, b_perpend_end = calc_perpendicular(str_pts)
    # calculate quadrant line lies in from street start and street end
    quadrant = calculate_quadrant_from_center([str_pts[0], str_pts[1]])
    
    if slope_origin > 0:
        if abs(math.degrees(x_angle)) <= 45:
            if quadrant in [1, 4]:
                start_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_above) #upper left
                end_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_above) #upper right
                end_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_below) # lower right
                start_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_below) #lower left
                
            if quadrant in [2, 3]:
                start_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_below) #upper left
                end_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_below) #upper right
                end_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_above) # lower right
                start_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_above) #lower left
                
        elif abs(math.degrees(x_angle)) > 45:
            if quadrant in [1, 2]:
                start_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_above) #upper left
                end_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_above) #upper right
                end_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_below) # lower right
                start_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_below) #lower left

            if quadrant in [3, 4]:
                start_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_below) #upper left
                end_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_below) #upper right
                end_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_above) # lower right
                start_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_above) #lower left

    elif slope_origin < 0:
        if abs(math.degrees(x_angle)) <= 45:
            if quadrant in [1, 4]:
                start_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_above) #upper left
                end_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_above) #upper right
                end_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_below) # lower right
                start_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_below) #lower left

            if quadrant in [2, 3]:
                start_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_below) #upper left
                end_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_below) #upper right
                end_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_above) # lower right
                start_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_above) #lower left
                
        elif abs(math.degrees(x_angle)) > 45:
            if quadrant in [1, 2]:
                start_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_below) #upper left
                end_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_below) #upper right
                end_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_above) # lower right
                start_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_above) #lower left

            if quadrant in [3, 4]:
                start_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_above) #upper left
                end_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_above) #upper right
                end_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, slope_origin, b_parallel_below) # lower right
                start_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, slope_origin, b_parallel_below) #lower left

    bounding_box = [start_left, end_left, end_right, start_right]
    return bounding_box


# if __name__ == "__main__":
#     find_angle_to_y([(316822.5120000001, 5688438.680999999), (316822.10240000044, 5688330.902699999)])
#     calculate_slope([(316822.5120000001, 5688438.680999999), (316822.10240000044, 5688330.902699999)])