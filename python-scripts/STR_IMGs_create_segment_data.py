import ERROR_CODES as ec
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER, CYCLO_IMG_FOLDER_PATH
from DB_helpers import open_connection
from helpers_geometry import calculate_street_deviation_from_north, calculate_bounding_box, is_recording_direction_equal_street_direction
from helpers_coordiantes import is_point_within_polygon
from STR_IMGs_api_calls import render_by_ID, list_recordings_in_bbox
from LOG import log
import STR_IMGs_config as CONF

import os
import psycopg2
from datetime import datetime, timedelta
import concurrent.futures

log_start = None
execution_file = "STR_IMGs_create_segment_data"


def check_for_only_error_values(rec_IDs:list):
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


def get_recordings_for_segment(bbox:list):
    # Determine lower and upper corner based on the calculations
    min_lat = min(bbox, key=lambda x: x[0])[0]
    max_lat = max(bbox, key=lambda x: x[0])[0]
    min_lon = min(bbox, key=lambda x: x[1])[1]
    max_lon = max(bbox, key=lambda x: x[1])[1]
    lower_corner, upper_corner= (min_lat, min_lon), (max_lat, max_lon)
    #print(lower_corner, upper_corner)

    # recordings format [{'recording_id': .., 'recording_location': .., 'recording_direction': .., 'recording_date_time': ..}, ]
    recordings = list_recordings_in_bbox(CONF.cyclo_srs, lower_corner, upper_corner)
    
    if recordings != []:
        # clean out recordings again, using the real street bbox
        recordings_within_street_bbox = [item for item in recordings if is_point_within_polygon(item['recording_location'], bbox)]

        # clean out recordings that deviate too much in time, get time junks that are on one stretch meaning, the time gap between two recordings should not be larger than the set threshold of 5 minutes
        # sort recordings by property recording date time (= ascending order)
        sorted_recordings = sorted(recordings_within_street_bbox, key=lambda x: x['recording_date_time'])
        
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
        # print("indices:", indices)

        if indices != []:
            time_junks = []
            start, end = 0, len(sorted_recordings)
            for idx in indices:
                time_junks.append(sorted_recordings[start:idx+1])
                start = idx+1 #because last slice is not includes
            time_junks.append(sorted_recordings[start:end])
            # return the biggest time junk
            return max(time_junks, key=len)
        else:
            return sorted_recordings
    else:
        return []


def get_image_IDs_from_cyclomedia(segment_id: int, segmentation_number: int, rec_IDs: list, north_deviation_street: float, max_distance: int, folder_dir: str, debug_mode: bool):
    print(f"[i] Getting image IDs and images from cyclo")

    print_url = True if debug_mode else False
    
    if len(rec_IDs) == 0:
        return rec_IDs

    # for filesaving
    if segmentation_number < 10:
        segmentation_number = "0" + str(segmentation_number)

    def process_item(item):
        nonlocal folder_dir

        recording_direction = item['recording_direction']
        item['recording_year'] = item['recording_date_time'].year
        
        equal_direction = is_recording_direction_equal_street_direction(recording_direction, north_deviation_street)

        if equal_direction:
            params = {'yaw': str(recording_direction), 'hfov': '80'}
        else:
            recording_direction += 180
            params = {'yaw': str(recording_direction), 'hfov': '80'}

        response, recording_lat, recording_lon = render_by_ID(CONF.cyclo_srs, item['recording_id'], params, print_url = print_url)
        item['recording_location'] = (recording_lat, recording_lon)

        if not debug_mode:
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
def load_into_db(rec_IDs:list, segment_id:int, segmentation_number:int, db_table:str, connection):
    print("[i] Load to DB")
    cursor = connection.cursor()
    if check_for_only_error_values(rec_IDs):
        try:
            cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s, %s, %s, %s) """.format(db_table), (segment_id, ec.CYCLO_NO_REC_ID_TOTAL, segmentation_number, 0, 0, 0, 0,))
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
                cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s, %s, %s, %s) """.format(db_table), (segment_id, dict_item['recording_id'], segmentation_number, record_lat, record_lon, dict_item['recording_direction'], dict_item['recording_year'], ))
                connection.commit()
            except psycopg2.errors.UniqueViolation as e:
                print(f"Value already in table. segment {segment_id}, segmentation number {segmentation_number} ")
                connection.rollback()
                continue


# main function to collect all data and get images from cyclomedia
# PARAMS:
#  suburb_list = [ot_name, ..], in this case ot_nr is not relevant
#  debug_mode (bool) no saving images or to DB if debug mode on
def get_cyclomedia_data(db_config_path:str, db_user:str, suburb_list:list, cyclo_segment_db_table:str, debug_mode:bool):

    if not db_config_path:
        db_config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
    if not db_user:
        db_user = DB_USER

    print("getting cyclomedia data...")
    global log_start 
    log_start = datetime.now()

    with open_connection(db_config_path, db_user) as con:

        cursor = con.cursor()
        if suburb_list == []:
            # get ortsteile
            cursor.execute("""SELECT ot_name FROM ortsteile""")
            suburb_list = [item[0] for item in cursor.fetchall()]
        
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
                        rec_IDs = [{'recording_id': ec.WRONG_COORD_SORTING, 'recording_location': (0,0), 'recording_year': 0, 'recording_direction': 0}]
                        if not debug_mode:
                            load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_no, db_table=cyclo_segment_db_table, connection=con)
                        log(execution_file=execution_file, img_type="cyclo", logstart=log_start, logtime=datetime.now(), message= f"Wrong coord sorting for segment: {segment_id}")
                        print("[!] information invalid - skip")
                        continue

                # check if the data already exists: aggregate all cyclomedia record_ids to the segmentation number and compare with the segmentation number
                # TODO: doestn work, when segmentation =0) and there is one entry even though there should be more
                if not debug_mode:
                    cursor.execute("""SELECT array_agg(segmentation_number) FROM {} WHERE segment_id = %s GROUP BY segmentation_number""".format(cyclo_segment_db_table), (segment_id, ))
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

                    # shift_length = 3
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
                        north_deviation_street = calculate_street_deviation_from_north((start_lat, start_lon), (end_lat, end_lon))
                        print("START & END COORDS: ", (start_lat, start_lon), (end_lat, end_lon))
       
                        #rec_IDs = get_nearest_recordings_for_street_pts((start_lat, start_lon), (end_lat, end_lon), shift_length, slope_origin, quadrant, [])
                        recordings = get_recordings_for_segment(bbox) 
                        img_folder_dir = CYCLO_IMG_FOLDER_PATH + ot_name + "/"
                        rec_IDs = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = recordings, north_deviation_street = north_deviation_street, max_distance = 9, folder_dir= img_folder_dir, debug_mode = debug_mode)
                        if not debug_mode:
                            load_into_db(rec_IDs=rec_IDs, segment_id = segment_id, segmentation_number=segmentation_number, db_table=cyclo_segment_db_table, connection=con)

            
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
                            north_deviation_street = calculate_street_deviation_from_north((start_lat, start_lon), (end_lat, end_lon))
                            print("START & END COORDS: ", (start_lat, start_lon), (end_lat, end_lon))                                                        
       
                            #rec_IDs = get_nearest_recordings_for_street_pts((start_lat, start_lon), (end_lat, end_lon), shift_length, slope_origin, quadrant, [])
                            recordings = get_recordings_for_segment(bbox) 
                            img_folder_dir = CYCLO_IMG_FOLDER_PATH + ot_name + "/"
                            rec_IDs = get_image_IDs_from_cyclomedia(segment_id = segment_id, segmentation_number = segmentation_number, rec_IDs = recordings, north_deviation_street = north_deviation_street, max_distance = 9, folder_dir= img_folder_dir, debug_mode= debug_mode)
                            if not debug_mode:
                                load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_number, db_table=cyclo_segment_db_table, connection=con)



if __name__ == "__main__":
    # debug_mode: no saving to DB and to image folder if debug mode on
                                                    #suburb list = [string, string,... ]    #segments_cyclomedia_newmethod
    get_cyclomedia_data(db_config_path=None, db_user=None, suburb_list=['Südvorstadt'], cyclo_segment_db_table="segments_cyclomedia_withdeviation", debug_mode = False)