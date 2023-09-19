import ERROR_CODES as ec
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME
from DB_helpers import open_connection
from helpers_geometry import calculate_street_deviation_from_north, find_angle_to_x, get_y_intercept, segment_iteration_condition, calculate_slope
from helpers_coordiantes import calulate_distance_of_two_coords, shift_pt_along_street
from STR_IMGs_api_calls import list_nearest_recordings, get_recording_id, render_by_ID, get_viewing_direction

import STR_IMGs_config as CONF
import PATH_CONFIGS as PATHS

import psycopg2


# helper-func: check if all entries in recording ID list are just errors, if yes return True
def check_for_only_error_values(rec_IDs):
    rec_IDs_with_error = [item['recording_id'] for item in rec_IDs if item['recording_id'] == ec.CYCLO_NO_REC_ID_SINGLE]
    if len(rec_IDs_with_error) == len(rec_IDs):
        return True
    else:
        return False


# iterate a segment or a segmented segment from start to end coordinate and get all cyclomedia recording IDs in between
# compare recoding times of two adjacent points, if they have not been recorded right after another the process is started again !once!
# if the second run also couldnt find adjacent recordings, error code is returned
# for each point finds a list of nearest recordings from cyclomedia, iterating this list to find the next adjacent recording id regarding both recording time and location
def get_nearest_recordings_for_street_pts(str_start: tuple, str_end:tuple, shift_length:int, slope_origin:float, rec_IDs:list):
    print(f"[i] Getting nearest recordings for street segment", str_start, str_end)
    if check_for_only_error_values(rec_IDs):
        first_run = True
    else:
        first_run = False

    x_angle = find_angle_to_x([str_start, str_end])
    b = get_y_intercept(str_start, slope_origin)

    nearest_recordings_response = list_nearest_recordings(CONF.cyclo_srs, str_start[0], str_start[1], {}, False)
    first_nearest_rec_ID, start_rec_time = get_recording_id(nearest_recordings_response, index=0)
    if first_nearest_rec_ID == "" and first_run:
        rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (str_start[0], str_start[1]), 'viewing_direction': 0, 'recording_point': (), 'recording_year': 0})
        x_shifted, y_shifted = shift_pt_along_street((str_start[0], str_start[1]), x_angle, shift_length, slope_origin, b)
        if segment_iteration_condition(slope_origin, x_angle, str_start, str_end, x_shifted, y_shifted):
            rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, rec_IDs)
        return rec_IDs
    elif first_nearest_rec_ID == "" and not first_run:
        rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (str_start[0], str_start[1]), 'viewing_direction': 0, 'recording_point': (), 'recording_year': 0})
        return rec_IDs
    
    rec_IDs.append({'recording_id': first_nearest_rec_ID, 'street_point': (str_start[0], str_start[1]), 'viewing_direction': 0, 'recording_point': (), 'recording_year': start_rec_time.year})
    x_shifted, y_shifted = shift_pt_along_street((str_start[0], str_start[1]), x_angle, shift_length, slope_origin, b)
    #print(f"start point: {str_start[0], str_start[1]}, recording id:  {first_nearest_rec_ID} - time: {start_rec_time}")
    #print("next point:", x_shifted, y_shifted)

    while segment_iteration_condition(slope_origin, x_angle, str_start, str_end, x_shifted, y_shifted):
        recording_index = 0
        nearest_recordings = list_nearest_recordings(CONF.cyclo_srs, x_shifted, y_shifted, {}, False)
        nearest_rec_ID, rec_time = get_recording_id(nearest_recordings, recording_index)

        if nearest_rec_ID == "" and first_run:
            rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (), 'recording_year': 0})
            rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, rec_IDs)
            return rec_IDs
        elif nearest_rec_ID == "" and not first_run:
            rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (), 'recording_year': 0})
            return rec_IDs
        else:
            t_delta = abs(((rec_time - start_rec_time).total_seconds()/60))

        #print("FIRST WHILE", "recindex: ",recording_index, "num items response :", len(ET.fromstring(nearest_recordings.text)), "ID:", nearest_rec_ID, "time: ", rec_time)
        
        # if time difference > x min, get the next point from the list of nearest recordings
        # if no points lie within the time delta skip
        while t_delta > 2:
            
            recording_index += 1
            nearest_rec_ID, rec_time = get_recording_id(nearest_recordings, recording_index)

            if nearest_rec_ID == "" and first_run:
                rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (0,0), 'recording_year': 0})
                rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, rec_IDs)
                return rec_IDs
            elif nearest_rec_ID == "" and not first_run:
                rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (0,0), 'recording_year': 0})
                return rec_IDs
            else:
                t_delta = abs(((rec_time - start_rec_time).total_seconds()/60))

            #print("SECOND WHILE recording index", recording_index, "recID", nearest_rec_ID, "bool:", first_run, "tdelta", t_delta, "time: ", rec_time)
     
        if nearest_rec_ID not in [item["recording_id"] for item in rec_IDs]:
            rec_IDs.append({'recording_id': nearest_rec_ID, 'street_point': (x_shifted, y_shifted), 'viewing_direction': 0, 'recording_point': (), 'recording_year': rec_time.year})
            
        x_shifted, y_shifted = shift_pt_along_street((x_shifted, y_shifted), x_angle, shift_length, slope_origin, b)
        #print(f"next point: {x_shifted,y_shifted}", "rec_ID_keys", [item["recording_id"] for item in rec_IDs])
        start_rec_time = rec_time

    print(rec_IDs)
    return rec_IDs


# NEW: calculate shortest_angular_distance between cyclomedia recording direction angle and street north deviation angle
# if between specified range return True, else False
def is_recording_direction_equal_street_direction(viewing_direction, street_north_deviation):
    # Calculate the absolute difference between the angles
    abs_diff = abs(viewing_direction - street_north_deviation)
    print("viewing_direction: ", viewing_direction, street_north_deviation)
    
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
def get_image_IDs_from_cyclomedia(segment_id:int, segmentation_number:int, rec_IDs:list, north_deviation: float, max_distance:int, folder_dir:str):
    print(f"[i] Getting image IDs and images from cyclo")
    if len(rec_IDs) == 0:
        return rec_IDs

    # for filesaving
    if segmentation_number < 10:
        segmentation_number = "0" + str(segmentation_number)

    for idx, item in enumerate(rec_IDs):

        # TODO GET CYCLOMEDIA RECORDING DIRECTION
        # for the cyclomedia api the y_angle gives the deviation from north direction. yaw = 0 => looking towards north,
        # for streets with falling slope the y_angle is measured "on the other side" therefore it is not represention the deivation from north without adding 90
        # if slope_origin < 0:
        #     y_angle = (90-y_angle) + 90
        # elif slope_origin > 0:
        #     y_angle = y_angle
        

        if item['recording_id'] == ec.CYCLO_NO_REC_ID_SINGLE:
            item['recording_point'] = (0,0)
            continue

        viewing_direction =  get_viewing_direction(CONF.cyclo_srs, item['recording_id'])
        item['viewing_direction'] = viewing_direction
        equal_direction = is_recording_direction_equal_street_direction(viewing_direction, north_deviation)

        if equal_direction:
            #direction 90/-90 would be on the right/left side of the car
            params = {'yaw': str(viewing_direction), 'hfov': '80'}

        if not equal_direction:
            print("NOT EQUAL:", segment_id, item['recording_id'])
            #direction 90/-90 would be on the right/left side of the car
            viewing_direction += 180
            params = {'yaw': str(viewing_direction), 'hfov': '80'}

        response, recording_lat, recording_lon = render_by_ID(CONF.cyclo_srs, item['recording_id'], params, True)
        item['recording_point'] = (recording_lat, recording_lon)

        if response.status_code == 200:

            # calc distance between streeet and recording point, if too large, cyclomedia didnt drive through the street
            distance = calulate_distance_of_two_coords(item['recording_point'], item['street_point'])

            if distance > max_distance:
                print("[!!!] MAX DIST not saving image")
                item['recording_id'] = ec.CYCLO_MAX_DIST
                item['recording_point'] = (0,0) 
                continue    
        
            else:

                img_file_name = str(segment_id) + "_" + str(segmentation_number) + "_" + str(item['recording_id']) + ".jpg"
                with open(folder_dir + img_file_name, 'wb') as file:
                    file.write(response.content)
            
        else:
            print(f"[!!!] BAD STATUSCODE: for image with id: {item['recording_id']}")
            item['recording_id'] = ec.CYCLO_BAD_RESPONSE_CODE
            item['recording_point'] = (0,0)
            continue

    return rec_IDs


# after validating all recording IDs concerning distances and times, load the remaining rec IDs into the DB 
# PARAMS: 
#  rec_IDs (dict) of recording ID and information
#  segment_id: the segment ID the information is for
#  segmentation_number: the segmentation number of the segment
#  connection: DB connection
def load_into_db(rec_IDs, segment_id, segmentation_number, connection):
    print("[i] Load to DB")
    cursor = connection.cursor()
    if check_for_only_error_values(rec_IDs):
        try:
            cursor.execute("""INSERT INTO segments_cyclomedia VALUES (%s, %s, %s, %s, %s, %s) """, (segment_id, ec.CYCLO_NO_REC_ID_TOTAL, segmentation_number, 0, 0, 0,))
            connection.commit()
        except psycopg2.errors.UniqueViolation:
            print(f"Value already in table. segment {segment_id}, segmentation number {segmentation_number}")
            connection.rollback()
            return
            
    else:
        for dict_item in rec_IDs:
            try:
                record_lat, record_lon = dict_item['recording_point'][0], dict_item['recording_point'][1]
                cursor.execute("""INSERT INTO segments_cyclomedia VALUES (%s, %s, %s, %s, %s, %s) """, (segment_id, dict_item['recording_id'], segmentation_number, record_lat, record_lon,dict_item['recording_year'], ))
                connection.commit()
            except psycopg2.errors.UniqueViolation as e:
                print(f"Value already in table. segment {segment_id}, segmentation number {segmentation_number} ")
                connection.rollback()
                continue


# main function to collect all data and get images from cyclomedia
# PARAMS:
#  suburb_list = [(ot_name, ot_nr), ..], in this case ot_nr is not relevant and can be 0 all the time
#  get_sideways_imgs (bool) if for each recording point the sideways direction of 90/-90 should be extracted as well (takes 3 times longer)
def get_cyclomedia_data(db_config, db_user, suburb_list, get_sideways_imgs):
    print("getting cyclomedia data...")
    with open_connection(db_config, db_user) as con:

        cursor = con.cursor()
        if suburb_list == []:
             # get ortsteile and their number codes
            cursor.execute("""SELECT ot_name, ot_nr FROM ortsteile""")
            suburb_list = cursor.fetchall()
        
        for ot_name, ot_nr in suburb_list:
            print("getting cyclomedia data for ", ot_name)

            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            segment_id_list = [item[0] for item in cursor.fetchall()]
            for i, segment_id in enumerate(segment_id_list):
            
                print(f"------{i+1} of {len(segment_id_list)+1}, segment_ID: {segment_id}--------")

                cursor.execute("""SELECT segmentation_number, start_lat, start_lon, end_lat, end_lon FROM segments_segmentation WHERE segment_id = %s ORDER BY segmentation_number""", (segment_id, ))
                segmentation_result_rows = cursor.fetchall()

                #TODO: sollte nicht mehr auftreten nach einführung von error codes
                if segmentation_result_rows == []:
                    print("NO RESULT FOR ID %s", segment_id)
                    continue

                # check if information is valid #TODO zusammenführen
                elif len(segmentation_result_rows) == 1:
                    segmentation_no = segmentation_result_rows[0][0]
                    if segmentation_no == ec.WRONG_COORD_SORTING:
                        rec_IDs = [{'recording_id': ec.WRONG_COORD_SORTING, 'street_point': (0,0), 'recording_point': (0,0), 'recording_year': 0}]
                        load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_no, connection=con)
                        print("[!] information invalid - skip")
                        continue

                # check if the data already exists: aggregate all cyclomedia record_ids to the segmentation number and compare with the segmentation number
                cursor.execute("""SELECT array_agg(segmentation_number) FROM segments_cyclomedia WHERE segment_id = %s GROUP BY segmentation_number""", (segment_id, ))
                cyclo_result_rows = cursor.fetchall()
                
                if len(cyclo_result_rows) == len(segmentation_result_rows): 
                    print("EXIST - SKIP")
                    continue
                
                cursor.execute("""SELECT multiple_areas FROM area_segment_relation WHERE segment_id = %s""", (segment_id, ))
                multiple_areas = cursor.fetchone()
                
                if multiple_areas is None:
                    print("[!!!] no information about traffic area - skip")
                    continue

                elif multiple_areas[0] == True:
                    print("[!!!] multiple traffic areas - skip")
                    #TODO!
                    continue

                elif multiple_areas[0] == False:
                    
                    shift_length = 3
                    # segment is not divided into smaller parts
                    if len(segmentation_result_rows) == 1:
                        segmentation_number = segmentation_result_rows[0][0]
                        start_lat, start_lon = segmentation_result_rows[0][1], segmentation_result_rows[0][2]
                        end_lat, end_lon = segmentation_result_rows[0][3], segmentation_result_rows[0][4]
                        slope_origin = calculate_slope([(start_lat, start_lon), (end_lat, end_lon)])
                        north_deviation = calculate_street_deviation_from_north((start_lat, start_lon), (end_lat, end_lon))
                        print("START & END COORDS: ", (start_lat, start_lon), (end_lat, end_lon))
       
                        rec_IDs = get_nearest_recordings_for_street_pts((start_lat, start_lon), (end_lat, end_lon), shift_length, slope_origin, [])
                        rec_IDs = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = rec_IDs, north_deviation = north_deviation, max_distance = 9, folder_dir=PATHS.CYCLO_IMG_FOLDER_PATH)
                        load_into_db(rec_IDs=rec_IDs, segment_id = segment_id, segmentation_number=segmentation_number, connection=con)

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
                            slope_origin = calculate_slope([(start_lat, start_lon), (end_lat, end_lon)])
                            north_deviation = calculate_street_deviation_from_north((start_lat, start_lon), (end_lat, end_lon))
                            print("START & END COORDS: ", (start_lat, start_lon), (end_lat, end_lon))                                                        
       
                            rec_IDs = get_nearest_recordings_for_street_pts((start_lat, start_lon), (end_lat, end_lon), shift_length, slope_origin, [])
                            rec_IDs = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = rec_IDs, north_deviation = north_deviation, max_distance = 9, folder_dir=PATHS.CYCLO_IMG_FOLDER_PATH)
                            load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_number, connection=con)

                            # if get_sideways_imgs: # TODO
                            #     # right side??
                            #     _ = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = rec_IDs, slope_origin = slope_origin, max_distance = 9, y_angle = (90 + y_angle_degrees), folder_dir=PATHS.CYCLO_90_IMG_FOLDER_PATH)
                            #     # left side??
                            #     _ = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = rec_IDs, slope_origin = slope_origin, max_distance = 9, y_angle = (-90 + y_angle_degrees), folder_dir=PATHS.CYCLO_MINUS90_IMG_FOLDER_PATH)




if __name__ == "__main__":
    config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
                                                    #suburb list = tuple (sstr, int)
    get_cyclomedia_data(config_path, PATHS.DB_USER, suburb_list=[("Südvorstadt", 70)], get_sideways_imgs = False)