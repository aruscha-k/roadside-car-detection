import ERROR_CODES as ec
from GLOBAL_VARS import ITERATION_LENGTH
from DB_helpers import open_connection
from helpers_geometry import calculate_start_end_pt, calculate_bounding_box, find_angle_to_x, calculate_slope, get_y_intercept, segment_iteration_condition
from helpers_coordiantes import convert_coords, sort_coords, shift_pt_along_street, calulate_distance_of_two_coords
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER
from LOG import log

import json
from datetime import datetime

log_start = None
execution_file = "DB_create_relations"

def create_segm_gid_relation(db_config:str=None, db_user:str=None):
    print('Creating area_segment_relation table ....')

    if not db_config:
        db_config = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
    if not db_user:
        db_user = DB_USER

    with open_connection(db_config, db_user) as con:

        cursor = con.cursor()
        cursor.execute("""CREATE TABLE area_segment_relation AS SELECT id AS area_id, segm_gid FROM trafficareas;""")
        cursor.execute("""ALTER TABLE area_segment_relation ADD COLUMN multiple_areas boolean, ADD COLUMN segment_id int""")

        cursor.execute("""SELECT segm_gid FROM area_segment_relation""")
        #iterate all segm_gids and get the segment Id and the number of segm_gis in area table
        for segm_gid in cursor.fetchall():
            segm_gid = segm_gid[0]
       
            cursor.execute("""SELECT id FROM segments WHERE segm_gid = (%s)""",(segm_gid,))
            res = cursor.fetchone()
            if res is None:
                continue
            else:
                segment_id = res[0]

            cursor.execute("""SELECT count(segm_gid) FROM trafficareas WHERE segm_gid = (%s)""",(segm_gid,))
            num_entries = cursor.fetchone()
            if num_entries is None:
                num_entries = None

            if num_entries[0] == 1:
                cursor.execute("""UPDATE area_segment_relation 
                                    SET segment_id = %s, multiple_areas = FALSE
                                    WHERE segm_gid = %s""",(segment_id, segm_gid,))
            if num_entries[0] > 1:
                cursor.execute("""UPDATE area_segment_relation 
                                SET segment_id = %s, multiple_areas = TRUE
                                WHERE segm_gid = %s""",(segment_id, segm_gid,))


def create_iteration_boxes(str_start, str_end, width, quadrant):

    iteration_segments = []
    x_angle = find_angle_to_x([str_start, str_end])
    slope = calculate_slope([str_start, str_end])
    if slope == None:
        b = 0
    else:
        b = get_y_intercept(str_start, slope)

    #first shift
    x_start, y_start  = str_start[0], str_start[1]
    x_shifted, y_shifted = shift_pt_along_street((x_start, y_start), x_angle, ITERATION_LENGTH, slope, b, quadrant)
    while segment_iteration_condition(slope, x_angle, str_start, str_end, x_shifted, y_shifted, quadrant):
        # bbox type = [start_left, end_left, end_right, start_right]
        bbox = calculate_bounding_box([(x_start, y_start), (x_shifted, y_shifted)], width, quadrant)
        iteration_segments.append(bbox)
        x_start, y_start = x_shifted, y_shifted
        dist = calulate_distance_of_two_coords([x_start, y_start], str_end)
        if ITERATION_LENGTH <= dist <= (ITERATION_LENGTH*1.2): #to avoid very small iteration boxes, check if the last part is only slightly bigger than the iteration length
            break
        x_shifted, y_shifted = shift_pt_along_street((x_start, y_start), x_angle, ITERATION_LENGTH, slope, b, quadrant)
   
    #last point when codition was false
    bbox = calculate_bounding_box([(x_start, y_start), (str_end[0], str_end[1])], width, quadrant)
    iteration_segments.append(bbox)

    return iteration_segments


def get_traffic_area_width(segm_gid, cursor):
    """ gets width for a segment id, checks if the segment consists of several traffic areas 
    Args:
        segm_gid (int): another ID for segments that the connects segments to traffic areas
        cursor (db cursor): 
        
    Returns:
        width (float): real number if width avaiable, error code if not (! string)
    """

    cursor.execute("""SELECT multiple_areas from area_segment_relation WHERE segm_gid =  %s""", (segm_gid, ))
    res = cursor.fetchone()
    if res == None:
        return ec.NO_TRAFFIC_AREA_INFO, ec.NO_TRAFFIC_AREA_INFO
    
    multiple_areas = res[0]
    if not multiple_areas:
        cursor.execute("""SELECT median_breite FROM trafficareas WHERE segm_gid = %s""", (segm_gid, ))
        median_width_original = cursor.fetchone()

        if median_width_original == []:
            print("[!] NO WIDTH FOR SEGMENT ", segm_gid)
            return ec.NO_WIDTH, ec.NO_WIDTH
        else:
            extended_median_with = median_width_original[0] + (0.75 * median_width_original[0])
            return extended_median_with, median_width_original[0]
    else:
        return ec.MULTIPLE_TRAFFIC_AREAS, ec.MULTIPLE_TRAFFIC_AREAS


def write_segmentation_values_to_DB(cursor, con, segment_id, segmentation_counter, width, start_lat, start_lon, end_lat, end_lon, quadrant):
    """
    Args:
        segment_id (int): ID for segments
        segmentation_counter (int): number of times the coordinates will be subdivided
        width (float): extended width
        start_lat, start_lon (float, float): coordinates of the current segmentation
        end_lat, end_lon (float, float): coordinates of the current segmentation
        quadrant (int): 1-4 quadrant of the coordinates system
    """
    cursor.execute("""INSERT INTO segments_segmentation 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) """, (segment_id, segmentation_counter, width, start_lat, start_lon, end_lat, end_lon, quadrant,))
    con.commit()
                   

def write_iteration_boxes_to_DB(cursor, con, bboxes, segment_id, segmentation_number, db_table):
    """
    Args:
        segment_id (int): ID for segments
        segmentation_number (int): subdivision of segmentation
        bboxes (list): of floats -> [start_left, end_left, end_right, start_right]
        db_table (string): name of db table to save to
    """
    for idx, bbox in enumerate(bboxes):
        left_coords = [bbox[0], bbox[1]]
        right_coords = [bbox[3], bbox[2]]
        #print(left_coords,right_coords)
        # left_coords = [convert_coords("EPSG:25833", "EPSG:4326", coord[0], coord[1]) for coord in left_coords]
        # right_coords = [convert_coords("EPSG:25833", "EPSG:4326", coord[0], coord[1]) for coord in right_coords]

        cursor.execute("""
                        INSERT INTO {}
                        VALUES (%s, %s, %s, %s, %s)""".format(db_table), (segment_id, segmentation_number, idx, json.dumps(left_coords), json.dumps(right_coords), ))
    con.commit()


def write_segment_street_sides_to_DB(cursor, con, iteration_boxes, segment_id, segmentation_number):
    """
    writes the first and last iteration box to DB that make up one street side => function to extract the sides of the street for visualisation from the iteration boxes 
    Args:
        segm_gid (int): another ID for segments that the connects segments to traffic areas
        iteration_boxes (list): all iteration boxes within the segment, one item like [start_left, end_left, end_right, start_right]
        segmentation_number (int): number of iteration within segment
    """
    start_left, end_left = iteration_boxes[0][0], iteration_boxes[-1][1]
    start_right, end_right = iteration_boxes[0][3], iteration_boxes[-1][2]
    
    left_coords = [start_left, end_left]
    right_coords = [start_right, end_right]
    left_coords = [convert_coords("EPSG:25833", "EPSG:4326", coord[0], coord[1]) for coord in left_coords]
    right_coords = [convert_coords("EPSG:25833", "EPSG:4326", coord[0], coord[1]) for coord in right_coords]

    cursor.execute("""
                INSERT INTO visualisation_segments_segmentation_sides 
                VALUES (%s, %s, %s, %s)""", (segment_id, segmentation_number, json.dumps(left_coords), json.dumps(right_coords), ))
    con.commit()

    

# for every segment in the segments table check, if the segment is sectioned into more than one piece (Len(coords) > 2) if yes => segment has a bend
# for every segment add information if it is segmented and if yes the specific start end coordinates of the segmented segment to a table segments_segmentation
def create_segmentation_and_iteration(db_config:str=None, db_user:str=None):
    print('Creating segmentations and iteration boxes....')

    if not db_config:
        db_config = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
    if not db_user:
        db_user = DB_USER

    global log_start
    log_start = datetime.now()

    with open_connection(db_config, db_user) as con:
        cursor = con.cursor()
        cursor.execute("""SELECT id, segm_gid, geom_type, geom_coordinates FROM segments""")
        result = cursor.fetchall()

        for idx, res_item in enumerate(result):
            segment_id, segm_gid, geom_type, geom_coords = res_item[0], res_item[1], res_item[2], res_item[3]
            print("segment id", idx, segment_id)
          
            # geom_type can be LineString or MultiLineString
            #TODO: Multilinestring
            if geom_type == "LineString":
        
                #TODO: check if segment exists already?
                #converted_coords = [convert_coords("EPSG:25833", "EPSG:4326", pt[0], pt[1]) for pt in geom_coords]
                str_start, str_end, quadrant = calculate_start_end_pt(geom_coords)
                sorted_coords = sort_coords(geom_coords, str_start)
                
                
                # if sorting method didnt work TODO: find way to sort coords
                if sorted_coords == []:
                    # sorted_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in sorted_coords]
                # else:
                    log(execution_file=execution_file, img_type="", logstart=log_start, logtime=datetime.now(), message= f"Wrong coord sorting for segment: {segment_id}")
                    write_segmentation_values_to_DB(cursor, con, segment_id, ec.WRONG_COORD_SORTING, ec.WRONG_COORD_SORTING, ec.WRONG_COORD_SORTING, ec.WRONG_COORD_SORTING, ec.WRONG_COORD_SORTING, ec.WRONG_COORD_SORTING, ec.WRONG_COORD_SORTING)
                    continue

                extended_median_with, median_width_original = get_traffic_area_width(segm_gid, cursor)
                if median_width_original == ec.NO_WIDTH or median_width_original == ec.MULTIPLE_TRAFFIC_AREAS or median_width_original == ec.NO_TRAFFIC_AREA_INFO:
                        error_core = median_width_original
                        log(execution_file=execution_file, img_type="", logstart=log_start, logtime=datetime.now(), message= f"No width for segment: {segment_id}, error code: {error_core}")
                        print("[!!] ERROR CODE: No width for segment or multiple traffic areas: ", segment_id, "error code: ", error_core)
                        write_segmentation_values_to_DB(cursor, con, segment_id, error_core, error_core, error_core, error_core, error_core, error_core, error_core)
                        continue
                
                # if more than two coordinates, street has a bend => 
                # partition the segment further and extract every two pairs of coordinate
                if len(sorted_coords) > 2:
                    segmentation_counter = 1
                    for i in range(0, len(sorted_coords)):
                        # print("segmentation counter:", segmentation_counter)
                        try:
                            write_segmentation_values_to_DB(cursor, con, segment_id, segmentation_counter, extended_median_with, sorted_coords[i][0], sorted_coords[i][1], sorted_coords[i+1][0], sorted_coords[i+1][1], quadrant)
                            iteration_segments_bboxes = create_iteration_boxes((sorted_coords[i][0], sorted_coords[i][1]), (sorted_coords[i+1][0], sorted_coords[i+1][1]), extended_median_with, quadrant)
                            write_iteration_boxes_to_DB(cursor, con, iteration_segments_bboxes, segment_id, segmentation_counter, db_table = 'segments_segmentation_iteration')
                            
                            # for visualisation save original widths
                            original_width_iteration_segments_bboxes = create_iteration_boxes((sorted_coords[i][0], sorted_coords[i][1]), (sorted_coords[i+1][0], sorted_coords[i+1][1]), median_width_original, quadrant)
                            write_iteration_boxes_to_DB(cursor, con, original_width_iteration_segments_bboxes, segment_id, segmentation_counter, db_table = 'visualisation_segments_segmentation_iteration_sides')
                            write_segment_street_sides_to_DB(cursor, con, original_width_iteration_segments_bboxes, segment_id, segmentation_counter)
                            segmentation_counter += 1

                        except IndexError:
                            break  
                # segment does not have bend
                else:
                    segmentation_counter = 0 
                    write_segmentation_values_to_DB(cursor, con, segment_id, segmentation_counter, extended_median_with, sorted_coords[0][0], sorted_coords[0][1], sorted_coords[1][0], sorted_coords[1][1], quadrant)
                    iteration_segments_bboxes = create_iteration_boxes(sorted_coords[0], sorted_coords[1], extended_median_with, quadrant)
                    write_iteration_boxes_to_DB(cursor, con, iteration_segments_bboxes, segment_id, segmentation_counter, db_table = 'segments_segmentation_iteration')

                     # for visualisation save original widths
                    original_width_iteration_segments_bboxes = create_iteration_boxes(sorted_coords[0], sorted_coords[1], median_width_original, quadrant)
                    write_iteration_boxes_to_DB(cursor, con, original_width_iteration_segments_bboxes, segment_id, segmentation_counter, db_table = 'visualisation_segments_segmentation_iteration_sides')
                    write_segment_street_sides_to_DB(cursor, con, original_width_iteration_segments_bboxes, segment_id, segmentation_counter)


# add the geometries as PostGIS geometries
# in the loaded segments table intersect each segment with the ortsteile geometry and if there is an intersection, add the accoding ot_name to segments table
def add_ot_to_segments(db_config:str=None, db_user:str=None):
    print("Add OT to segments...")

    if not db_config:
        db_config = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
    if not db_user:
        db_user = DB_USER

    with open_connection(db_config, db_user) as con:
        cursor = con.cursor()

        #convert geometry from JSON to postgis column type for tables segemtns and ortsteile
        # make sure POSTGIS EXTENSION IS INSTALLED
        for table in ['ortsteile', 'segments']:
            cursor.execute(""" 
                    ALTER TABLE {} ADD COLUMN geometry_from_json geometry;
                    UPDATE {} SET geometry_from_json = ST_GeomFromGeoJSON(geometry);
                    ALTER TABLE {} DROP COLUMN geometry;""".format(table, table, table))

        # add ot_name to segments table checking with ortsteile geometry
        cursor.execute(""" 
                UPDATE segments
                SET ot_name = ot.ot_name
                FROM ortsteile ot
                WHERE ST_Intersects(segments.geometry_from_json, ot.geometry_from_json);""")
        
        con.commit()


if __name__ == "__main__":

    # add_ot_to_segments()
    # create_segm_gid_relation()
    create_segmentation_and_iteration()

    