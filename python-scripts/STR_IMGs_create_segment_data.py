import ERROR_CODES as ec
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME
from DB_helpers import open_connection
from helpers_geometry import calculate_street_deviation_from_north, find_angle_to_x, get_y_intercept, segment_iteration_condition, calculate_slope, calculate_bounding_box
from helpers_coordiantes import calulate_distance_of_two_coords, shift_pt_along_street
from STR_IMGs_api_calls import list_nearest_recordings, get_recording_id, render_by_ID, get_viewing_direction, list_recordings_in_bbox
from LOG import log
import STR_IMGs_config as CONF
import PATH_CONFIGS as PATHS

import os
import psycopg2
from datetime import datetime, timedelta
import concurrent.futures

log_start = None
execution_file = "STR_IMGs_create_segment_data"


def check_for_only_error_values(rec_IDs):
    """helper-func: check if all entries in recording ID list are just errors, if yes return True

    Args:
        rec_IDs (list): of cyclomedia recording ids

    Returns:
        bool: if list consists only of error codes, return True
    """
    rec_IDs_with_error = [item['recording_id'] for item in rec_IDs if item['recording_id'] == ec.CYCLO_NO_REC_ID_SINGLE]
    if len(rec_IDs_with_error) == len(rec_IDs):
        return True
    else:
        return False


# iterate a segment or a segmented segment from start to end coordinate and get all cyclomedia recording IDs in between
# compare recoding times of two adjacent points, if they have not been recorded right after another the process is started again !once!
# if the second run also couldnt find adjacent recordings, error code is returned
# for each point finds a list of nearest recordings from cyclomedia, iterating this list to find the next adjacent recording id regarding both recording time and location
# def get_nearest_recordings_for_street_pts(str_start: tuple, str_end:tuple, shift_length:int, slope_origin:float, quadrant, rec_IDs:list):
#     print(f"[i] Getting nearest recordings for street segment", str_start, str_end)
#     if check_for_only_error_values(rec_IDs):
#         first_run = True
#     else:
#         first_run = False

#     x_angle = find_angle_to_x([str_start, str_end])
#     b = get_y_intercept(str_start, slope_origin)

#     nearest_recordings_response = list_nearest_recordings(CONF.cyclo_srs, str_start[0], str_start[1], {}, False)
#     first_nearest_rec_ID, start_rec_time = get_recording_id(nearest_recordings_response, index=0)
#     if first_nearest_rec_ID == "" and first_run:
#         rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (str_start[0], str_start[1]), 'viewing_direction': 0, 'recording_point': (), 'recording_year': 0})
#         x_shifted, y_shifted = shift_pt_along_street((str_start[0], str_start[1]), x_angle, shift_length, slope_origin, b, quadrant)
#         if segment_iteration_condition(slope_origin, x_angle, str_start, str_end, x_shifted, y_shifted):
#             rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, quadrant, rec_IDs)
#         return rec_IDs
#     elif first_nearest_rec_ID == "" and not first_run:
#         rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (str_start[0], str_start[1]), 'viewing_direction': 0, 'recording_point': (), 'recording_year': 0})
#         return rec_IDs
    
#     rec_IDs.append({'recording_id': first_nearest_rec_ID, 'street_point': (str_start[0], str_start[1]), 'viewing_direction': 0, 'recording_point': (), 'recording_year': start_rec_time.year})
#     x_shifted, y_shifted = shift_pt_along_street((str_start[0], str_start[1]), x_angle, shift_length, slope_origin, b, quadrant)
#     #print(f"start point: {str_start[0], str_start[1]}, recording id:  {first_nearest_rec_ID} - time: {start_rec_time}")
#     #print("next point:", x_shifted, y_shifted)

#     while segment_iteration_condition(slope_origin, x_angle, str_start, str_end, x_shifted, y_shifted, quadrant):
#         recording_index = 0
#         nearest_recordings = list_nearest_recordings(CONF.cyclo_srs, x_shifted, y_shifted, {}, False)
#         nearest_rec_ID, rec_time = get_recording_id(nearest_recordings, recording_index)

#         if nearest_rec_ID == "" and first_run:
#             rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (), 'recording_year': 0})
#             rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, quadrant, rec_IDs)
#             return rec_IDs
#         elif nearest_rec_ID == "" and not first_run:
#             rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (), 'recording_year': 0})
#             return rec_IDs
#         else:
#             t_delta = abs(((rec_time - start_rec_time).total_seconds()/60))

#         #print("FIRST WHILE", "recindex: ",recording_index, "num items response :", len(ET.fromstring(nearest_recordings.text)), "ID:", nearest_rec_ID, "time: ", rec_time)
        
#         # if time difference > x min, get the next point from the list of nearest recordings
#         # if no points lie within the time delta skip
#         while t_delta > 2:
            
#             recording_index += 1
#             nearest_rec_ID, rec_time = get_recording_id(nearest_recordings, recording_index)

#             if nearest_rec_ID == "" and first_run:
#                 rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (0,0), 'recording_year': 0})
#                 rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, quadrant, rec_IDs)
#                 return rec_IDs
#             elif nearest_rec_ID == "" and not first_run:
#                 rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (0,0), 'recording_year': 0})
#                 return rec_IDs
#             else:
#                 t_delta = abs(((rec_time - start_rec_time).total_seconds()/60))

#             #print("SECOND WHILE recording index", recording_index, "recID", nearest_rec_ID, "bool:", first_run, "tdelta", t_delta, "time: ", rec_time)
     
#         if nearest_rec_ID not in [item["recording_id"] for item in rec_IDs]:
#             rec_IDs.append({'recording_id': nearest_rec_ID, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (), 'recording_year': rec_time.year})
            
#         x_shifted, y_shifted = shift_pt_along_street((x_shifted, y_shifted), x_angle, shift_length, slope_origin, b, quadrant)
#         #print(f"next point: {x_shifted,y_shifted}", "rec_ID_keys", [item["recording_id"] for item in rec_IDs])
#         start_rec_time = rec_time

#     #print(rec_IDs)
#     return rec_IDs


def get_recordings_for_segment(bbox):
    min_lat = min(bbox, key=lambda x: x[0])[0]
    max_lat = max(bbox, key=lambda x: x[0])[0]
    min_lon = min(bbox, key=lambda x: x[1])[1]
    max_lon = max(bbox, key=lambda x: x[1])[1]

    # Determine the corners based on the calculations
    lower_corner, upper_corner= (min_lat, min_lon), (max_lat, max_lon)
    #print(lower_corner, upper_corner)

    # recordings format {'recording_id': recording_id, 'recording_location': recording_location, 'recording_direction': recording_direction, 'recording_date_time': recording_datetime}
    recordings = list_recordings_in_bbox(CONF.cyclo_srs, lower_corner, upper_corner)
    if recordings != []:
 
        # clean out recordings that deviate too much in time, get time junks that are on one stretch meaning, the time gap between two recordings should not be larger than the set threshold of 5 minutes
        # sort recordings by property recording date time (is ascending order)
        sorted_recordings = sorted(recordings, key=lambda x: x['recording_date_time'])
        
        # Define the time difference threshold (5 minutes)
        threshold = timedelta(minutes=5)
        indices = []
        # Compare pairwise datetime objects, save indices with bigger threshold
        for i in range(len(sorted_recordings)):
            try:
                time_difference = abs(sorted_recordings[i]['recording_date_time'] - sorted_recordings[i+1]['recording_date_time'])
                if time_difference > threshold:
                    indices.append(i)
            except IndexError:
                break
                
        print(indices)

        if indices != []:
            time_junks = []
            start, end = 0, len(sorted_recordings)
            for idx in indices:
                time_junks.append(sorted_recordings[start:idx])
                start = idx
            time_junks.append(sorted_recordings[start:end])
            # return the biggest time junk
            return max(time_junks, key=len)
        else:
            return sorted_recordings
    else:
        return []


def is_recording_direction_equal_street_direction(viewing_direction, street_north_deviation):
    """calculate shortest_angular_distance between cyclomedia recording direction angle and street north deviation angle
        if between specified range return True, else False

    Args:
        viewing_direction (float): viewing direction of cyclomedia car
        street_north_deviation (float): street deviation from north 

    Returns:
        bool: True if they point "in the same direction", else false
    """
    # Calculate the absolute difference between the angles
    abs_diff = abs(viewing_direction - street_north_deviation)
    #print("viewing_direction: ", viewing_direction, street_north_deviation)
    
    # Check for wraparound
    if abs_diff > 180:
        abs_diff = 360 - abs_diff

    if 0 <= abs_diff <= 30:
        return True
    else:
        return False


# for a list of recording_IDs, call cyclomedia function to retrieve the corresponding image
# PARAMS:
#  slope_origin (float) the slope of the segment / street
#  max_distance (float) a threshold value how far apart a recording point and the street point for which the recoridng point is are allowed to be apart
#  y_angle (float) angle in degrees of the deviation from north direction
#  folder dir (string) path to the folder to save the imgs in
#  rec_IDs of type {'recording_id': recording_id, 'recording_location': recording_location, 'recording_direction': recording_direction, 'recording_date_time': recording_datetime} 
# def get_image_IDs_from_cyclomedia(segment_id:int, segmentation_number:int, rec_IDs:list, north_deviation: float, max_distance:int, folder_dir:str):
    
#     print(f"[i] Getting image IDs and images from cyclo")
#     if len(rec_IDs) == 0:
#         return rec_IDs

#     # for filesaving
#     if segmentation_number < 10:
#         segmentation_number = "0" + str(segmentation_number)

#     for idx, item in enumerate(rec_IDs):
   
#         # if item['recording_id'] == ec.CYCLO_NO_REC_ID_SINGLE:
#         #     log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"No recording ID for segment: {segment_id}, error code: {ec.CYCLO_NO_REC_ID_SINGLE}")
#         #     item['recording_point'] = (0,0)
#         #     continue

#         # viewing_direction =  get_viewing_direction(CONF.cyclo_srs, item['recording_id'])
#         # item['viewing_direction'] = viewing_direction
#           item['recording_year'] = dict_item['recording_date_time'].year
#         recording_direction = item['recording_direction']
#         equal_direction = is_recording_direction_equal_street_direction(recording_direction, north_deviation)

#         if equal_direction:
#             #direction 90/-90 would be on the right/left side of the car
#             params = {'yaw': str(recording_direction), 'hfov': '80'}

#         if not equal_direction:
#             #print("NOT EQUAL:", segment_id, item['recording_id'])
#             #direction 90/-90 would be on the right/left side of the car
#             recording_direction += 180
#             params = {'yaw': str(recording_direction), 'hfov': '80'}

#         response, recording_lat, recording_lon = render_by_ID(CONF.cyclo_srs, item['recording_id'], params, False)
#         item['recording_point'] = (recording_lat, recording_lon)

#         if response.status_code == 200:

#             # calc distance between streeet and recording point, if too large, cyclomedia didnt drive through the street
#             #distance = calulate_distance_of_two_coords(item['recording_point'], item['street_point'])

#             # if distance > max_distance:
#             #     print("[!!!] MAX DIST not saving image")
#             #     item['recording_id'] = ec.CYCLO_MAX_DIST
#             #     item['recording_point'] = (0,0) 
#             #     log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"MAX distance for segment: {segment_id}, error code: {ec.CYCLO_MAX_DIST}")
#             #     continue    
        
#             # else:

#             if not os.path.exists(folder_dir):
#                 os.mkdir(folder_dir)
#             img_file_name = str(segment_id) + "_" + str(segmentation_number) + "_" + str(item['recording_id']) + ".jpg"
            
#             with open(folder_dir + img_file_name, 'wb') as file:
#                 file.write(response.content)
            
#         else:
#             print(f"[!!!] BAD STATUSCODE: for image with id: {item['recording_id']}")
#             log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"Bad cyclomedia status code for segment: {segment_id}, error code: {ec.CYCLO_BAD_RESPONSE_CODE}")
#             item['recording_id'] = ec.CYCLO_BAD_RESPONSE_CODE
#             item['recording_point'] = (0,0)
#             continue

#     return rec_IDs


def get_image_IDs_from_cyclomedia(segment_id: int, segmentation_number: int, rec_IDs: list, north_deviation: float, max_distance: int, folder_dir: str):
    print(f"[i] Getting image IDs and images from cyclo")
    
    if len(rec_IDs) == 0:
        return rec_IDs

    # for filesaving
    if segmentation_number < 10:
        segmentation_number = "0" + str(segmentation_number)

    def process_item(item):
        nonlocal folder_dir

        recording_direction = item['recording_direction']
        item['recording_year'] = item['recording_date_time'].year
        
        equal_direction = is_recording_direction_equal_street_direction(recording_direction, north_deviation)

        if equal_direction:
            params = {'yaw': str(recording_direction), 'hfov': '80'}
        else:
            recording_direction += 180
            params = {'yaw': str(recording_direction), 'hfov': '80'}

        response, recording_lat, recording_lon = render_by_ID(CONF.cyclo_srs, item['recording_id'], params, False)
        item['recording_location'] = (recording_lat, recording_lon)

        if response.status_code == 200:
            img_file_name = f"{segment_id}_{segmentation_number}_{item['recording_id']}.jpg"
            img_path = os.path.join(folder_dir, img_file_name)

            if not os.path.exists(folder_dir):
                os.makedirs(folder_dir)

            with open(img_path, 'wb') as file:
                file.write(response.content)

        else:
            print(f"[!!!] BAD STATUSCODE: for image with id: {item['recording_id']}")
            log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(),
                message=f"Bad cyclomedia status code for segment: {segment_id}, error code: {ec.CYCLO_BAD_RESPONSE_CODE}")
            item['recording_id'] = ec.CYCLO_BAD_RESPONSE_CODE
            item['recording_location'] = (0, 0)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(process_item, rec_IDs)

    return rec_IDs


# after validating all recording IDs concerning distances and times, load the remaining rec IDs into the DB 
# PARAMS: 
#  rec_IDs (list of dict) of recording ID and information
#  segment_id: the segment ID the information is for
#  segmentation_number: the segmentation number of the segment
#  connection: DB connection
def load_into_db(rec_IDs, segment_id, segmentation_number, db_table, connection):
    print("[i] Load to DB")
    cursor = connection.cursor()
    if check_for_only_error_values(rec_IDs):
        try:
            cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s, %s, %s) """.format(db_table), (segment_id, ec.CYCLO_NO_REC_ID_TOTAL, segmentation_number, 0, 0, 0,))
            log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"Only Error codes for segment: {segment_id}")
            connection.commit()
        except psycopg2.errors.UniqueViolation:
            print(f"Value already in table. segment {segment_id}, segmentation number {segmentation_number}")
            connection.rollback()
            return
            
    else:
        for dict_item in rec_IDs:
            try:
                record_lat, record_lon = dict_item['recording_location'][0], dict_item['recording_location'][1]
                cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s, %s, %s) """.format(db_table), (segment_id, dict_item['recording_id'], segmentation_number, record_lat, record_lon, dict_item['recording_year'], ))
                connection.commit()
            except psycopg2.errors.UniqueViolation as e:
                print(f"Value already in table. segment {segment_id}, segmentation number {segmentation_number} ")
                connection.rollback()
                continue


# main function to collect all data and get images from cyclomedia
# PARAMS:
#  suburb_list = [ot_name, ..], in this case ot_nr is not relevant
#  get_sideways_imgs (bool) if for each recording point the sideways direction of 90/-90 should be extracted as well (takes 3 times longer)
def get_cyclomedia_data(db_config, db_user, suburb_list, db_table, get_sideways_imgs):
    print("getting cyclomedia data...")
    global log_start 
    log_start = datetime.now()

    with open_connection(db_config, db_user) as con:

        cursor = con.cursor()
        if suburb_list == []:
             # get ortsteile and their number codes
            cursor.execute("""SELECT ot_name FROM ortsteile""")
            suburb_list = cursor.fetchall()
        
        for ot_name in suburb_list:
            print("getting cyclomedia data for ", ot_name)

            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            segment_id_list = [item[0] for item in cursor.fetchall()]
            if segment_id_list == []:
                print("No data for suburb: ", ot_name, "Check spelling?")
                return
            
            for i, segment_id in enumerate(segment_id_list):
            
                print(f"------{i+1} of {len(segment_id_list)+1}, segment_ID: {segment_id}--------")

                cursor.execute("""SELECT segmentation_number, start_lat, start_lon, end_lat, end_lon, width, quadrant FROM segments_segmentation WHERE segment_id = %s ORDER BY segmentation_number""", (segment_id, ))
                segmentation_result_rows = cursor.fetchall()

                #TODO: sollte nicht mehr auftreten nach einführung von error codes
                if segmentation_result_rows == []:
                    print("NO RESULT FOR ID %s", segment_id)
                    log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"No segmentation results for segment: {segment_id}")
                    continue

                # check if information is valid #TODO zusammenführen
                elif len(segmentation_result_rows) == 1:
                    segmentation_no = segmentation_result_rows[0][0]
                    if segmentation_no == ec.WRONG_COORD_SORTING:
                        rec_IDs = [{'recording_id': ec.WRONG_COORD_SORTING, 'recording_location': (0,0), 'recording_year': 0}]
                        load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_no, db_table=db_table, connection=con)
                        log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"Wrong coord sorting for segment: {segment_id}")
                        print("[!] information invalid - skip")
                        continue

                # check if the data already exists: aggregate all cyclomedia record_ids to the segmentation number and compare with the segmentation number
                # TODO: doestn work, when segmentation =0) and there is one entry even though there should be more
                cursor.execute("""SELECT array_agg(segmentation_number) FROM {} WHERE segment_id = %s GROUP BY segmentation_number""".format(db_table), (segment_id, ))
                cyclo_result_rows = cursor.fetchall()
                if len(cyclo_result_rows) == len(segmentation_result_rows): 
                    print("EXIST - SKIP")
                    continue
                
                #TODO implement error codes
                cursor.execute("""SELECT multiple_areas FROM area_segment_relation WHERE segment_id = %s""", (segment_id, ))
                multiple_areas = cursor.fetchone()
                
                if multiple_areas is None:
                    print("[!!!] no information about traffic area - skip")
                    log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"No traffic area information for segment: {segment_id}")
                    continue

                elif multiple_areas[0] == True:
                    print("[!!!] multiple traffic areas - skip")
                    log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"Multiple traffic areas for segment: {segment_id}")
                    #TODO implement multiple traffic areas => could work with the new way implemented getting cyclomedia IDs from WFS api
                    continue

                elif multiple_areas[0] == False:


                    shift_length = 3
                    # segment is not divided into smaller parts
                    if len(segmentation_result_rows) == 1:
                        segmentation_number = segmentation_result_rows[0][0]
                        start_lat, start_lon = segmentation_result_rows[0][1], segmentation_result_rows[0][2]
                        end_lat, end_lon = segmentation_result_rows[0][3], segmentation_result_rows[0][4]
                        quadrant = segmentation_result_rows[0][6]
                        median_width = segmentation_result_rows[0][5]
                        temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                        bbox = calculate_bounding_box(temp_coords, median_width, quadrant)
                        #slope_origin = calculate_slope([(start_lat, start_lon), (end_lat, end_lon)])
                        north_deviation = calculate_street_deviation_from_north((start_lat, start_lon), (end_lat, end_lon))
                        print("START & END COORDS: ", (start_lat, start_lon), (end_lat, end_lon))
       
                        #rec_IDs = get_nearest_recordings_for_street_pts((start_lat, start_lon), (end_lat, end_lon), shift_length, slope_origin, quadrant, [])
                        recordings = get_recordings_for_segment(bbox) 
                        img_folder_dir = PATHS.CYCLO_IMG_FOLDER_PATH + ot_name + "/"
                        rec_IDs = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = recordings, north_deviation = north_deviation, max_distance = 9, folder_dir= img_folder_dir)
                        load_into_db(rec_IDs=rec_IDs, segment_id = segment_id, segmentation_number=segmentation_number, db_table=db_table, connection=con)

                        # if get_sideways_imgs: #TODO
                        #     # right side??
                        #     _ = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = rec_IDs, slope_origin = slope_origin, max_distance = 9, y_angle = (90 + y_angle_degrees), folder_dir=PATHS.CYCLO_90_IMG_FOLDER_PATH)
                        #     # left side??
                        #     _ = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = rec_IDs, slope_origin = slope_origin, max_distance = 9, y_angle = (-90 + y_angle_degrees), folder_dir=PATHS.CYCLO_MINUS90_IMG_FOLDER_PATH)
            
                    # segment is divided into smaller parts
                    elif len(segmentation_result_rows) > 1:
                        
                        for idx, row in enumerate(segmentation_result_rows):
                            segmentation_number = segmentation_result_rows[idx][0]
                            start_lat, start_lon = segmentation_result_rows[idx][1], segmentation_result_rows[idx][2]
                            end_lat, end_lon = segmentation_result_rows[idx][3], segmentation_result_rows[idx][4]
                            quadrant = segmentation_result_rows[idx][6]
                            median_width = segmentation_result_rows[idx][5]
                            temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                            bbox = calculate_bounding_box(temp_coords, median_width, quadrant)
                            #slope_origin = calculate_slope([(start_lat, start_lon), (end_lat, end_lon)])
                            north_deviation = calculate_street_deviation_from_north((start_lat, start_lon), (end_lat, end_lon))
                            print("START & END COORDS: ", (start_lat, start_lon), (end_lat, end_lon))                                                        
       
                            #rec_IDs = get_nearest_recordings_for_street_pts((start_lat, start_lon), (end_lat, end_lon), shift_length, slope_origin, quadrant, [])
                            recordings = get_recordings_for_segment(bbox) 
                            img_folder_dir = PATHS.CYCLO_IMG_FOLDER_PATH + ot_name + "/"
                            rec_IDs = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = recordings, north_deviation = north_deviation, max_distance = 9, folder_dir= img_folder_dir)
                            load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_number, db_table=db_table, connection=con)

                            # if get_sideways_imgs: # TODO
                            #     # right side??
                            #     _ = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = rec_IDs, slope_origin = slope_origin, max_distance = 9, y_angle = (90 + y_angle_degrees), folder_dir=PATHS.CYCLO_90_IMG_FOLDER_PATH)
                            #     # left side??
                            #     _ = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = rec_IDs, slope_origin = slope_origin, max_distance = 9, y_angle = (-90 + y_angle_degrees), folder_dir=PATHS.CYCLO_MINUS90_IMG_FOLDER_PATH)




if __name__ == "__main__":
    config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
                                                    #suburb list = tuple (sstr, int)
    get_cyclomedia_data(config_path, PATHS.DB_USER, suburb_list=['Südvorstadt'], db_table="segments_cyclomedia_newmethod", get_sideways_imgs = False)