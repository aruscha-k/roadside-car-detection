import math


# https://math.stackexchange.com/questions/714378/find-the-angle-that-creating-with-y-axis-in-degrees
def find_angle_to_y(str_pts):
    start_pt, end_pt = str_pts[0], str_pts[1]
    y1 = max([start_pt[1], end_pt[1]])
    y2 = min([start_pt[1], end_pt[1]])  
    arcos = math.acos((y1-y2)/math.sqrt((start_pt[0]-end_pt[0])**2 + (y1-y2)**2))
    return arcos

# between two points, find the angle of the line they construct to the x-axis
# source https://stackoverflow.com/questions/41855261/calculate-the-angle-between-a-line-and-x-axis
# PARAMS: 
# str_pts (list) of two points
# RETURNS: angle in rad
def find_angle_to_x(str_pts):
    start_pt, end_pt = str_pts[0], str_pts[1]
    m = calculate_slope([start_pt, end_pt])
    #print(f"angle to x: {math.degrees(math.atan(m))}")
    return math.atan(m)


# method to determine the start and endpoint of a line according to this projects definition (s.WIKI)
# starting point is the one closest to city center
# PARAMS: str_pts (list) of street points
# RETURNS:
# str_start (float, float) start point
#  str_end  (float, float) end point
def calculate_start_end_pt(str_pts):
    print(f"i: Calc start and end point for: {str_pts}")
    x_angle = find_angle_to_x(str_pts)
    
    #! this method works for leipzig, because leipzig is located "right"/east of the coordinate origin and 
    # therefore the possible angles are max. 90 degrees
    if abs(math.degrees(x_angle)) <= 45:
        str_start = min(str_pts, key=lambda x: x[0])
        str_end = max(str_pts, key=lambda x: x[0])
        
    elif abs(math.degrees(x_angle)) > 45:
        str_start = min(str_pts, key=lambda x: x[1])
        str_end = max(str_pts, key=lambda x: x[1])
        
    return str_start, str_end


# Calculate a slope of a line (! uses the first and last point, so order if needed)
# PARAMS:
# linepts: (list) of points
# RETURNS:
# slope (float) if successfull
def calculate_slope(linepts):
    if len(linepts) > 0:
        first_pt = linepts[0]
        last_pt = linepts[-1]
        x1, y1 = first_pt[0], first_pt[1]
        x2, y2 = last_pt[0], last_pt[1]
        
        if (x2 - x1 != 0):
            return (y2 - y1) / (x2 - x1)
    
    else:
        print("[!] empty list")


# given a point and a slope of a line, calculate the y-intercept of the line
# PARAMS:
# pt: pt in the line
# slope: (float) slope of the line
# RETURNS:
# b: (float) y value of y-intercept 
def get_y_intercept(pt, slope):
    b = (-pt[0] * slope) + pt[1]
    return b




# given a list of two points (start and end point) of a line, 
# this method calculates the perpendicular (lotgerade) of the line at the start and end point
# PARAMS:
# str_pts (list) of two points
# RETURNS:
# pm (float) slope of the perpendicular
# b_start/b_end (float) y value of y-intercept of the start / end point
def calc_perpendicular(str_pts):
    start_pt, end_pt = str_pts[0], str_pts[1]
    m = calculate_slope(str_pts)
    pm = -(1/m)

    b_start = get_y_intercept(start_pt, pm)
    b_end = get_y_intercept(end_pt, pm)
    return pm, b_start, b_end


# given the slope and y intercept of two lines, this method calculates the interception point
# PARAMS:
# m1 / m2 (float) slope of first/second line
# b1 / b2 (float) y-intercept of first/second line
# RETURNS: 
# (x,y) point of interception
def calc_interception_of_two_lines(m1, b1, m2, b2):
    x = (b2-b1) / (m1-m2)
    y = m1 * x + b1

    return (x,y)



# def rotate(origin, point, angle):
#     """
#     Rotate a point counterclockwise by a given angle around a given origin.
#     The angle should be given in radians.
#     """
#     ox, oy = origin
#     px, py = point

#     qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
#     qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
#     return qx, qy

