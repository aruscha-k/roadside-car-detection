import ERROR_CODES as ec
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME
from DB_helpers import open_connection
from helpers_geometry import find_angle_to_y, find_angle_to_x, calculate_slope, get_y_intercept
from helpers_coordiantes import calulate_distance_of_two_coords
from STR_IMGs_api_calls import list_nearest_recordings, get_recording_id, render_by_ID

import STR_IMGs_config as CONF
import PATH_CONFIGS as PATHS

import operator
import math
import psycopg2


#helper: check if all entries in recording ID are just errors
def check_for_only_error_values(rec_IDs):
    rec_IDs_with_error = [item['recording_id'] for item in rec_IDs if item['recording_id'] == ec.CYCLO_NO_REC_ID_SINGLE]
    if len(rec_IDs_with_error) == len(rec_IDs):
        return True


# find length of adjacent to move pt along x+length_adjacent and with this new x value calculate y by using line equation
def shift_pt_along_street(origin_pt, x_angle, shift_length, slope, y_intercept):
    length_adjacent = (math.cos(x_angle) * shift_length)
    shifted_x = origin_pt[0] + length_adjacent
    shifted_y = (slope * shifted_x) + y_intercept
    return (shifted_x, shifted_y)


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

    # set the operator according to the slope of the street (if "going down" operator is >, if "going up" operator is <)
    if slope_origin > 0:
        op = operator.lt
    if slope_origin < 0:
        op = operator.gt

    x_angle = find_angle_to_x([str_start, str_end])
    b = get_y_intercept(str_start, slope_origin)

    nearest_recordings_response = list_nearest_recordings(CONF.cyclo_srs, str_start[0], str_start[1], {}, False)
    first_nearest_rec_ID, start_rec_time = get_recording_id(nearest_recordings_response, index=0)
    if first_nearest_rec_ID == "" and first_run:
        rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (str_start[0], str_start[1]), 'recording_point': (), 'recording_year': 0})
        x_shifted, y_shifted = shift_pt_along_street((str_start[0], str_start[1]), x_angle, shift_length, slope_origin, b)
        if op(y_shifted, str_end[1]):
            rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, rec_IDs)
        return rec_IDs
    elif first_nearest_rec_ID == "" and not first_run:
        rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (str_start[0], str_start[1]), 'recording_point': (), 'recording_year': 0})
        return rec_IDs
    
    rec_IDs.append({'recording_id': first_nearest_rec_ID, 'street_point': (str_start[0], str_start[1]), 'recording_point': (), 'recording_year': start_rec_time.year})
    x_shifted, y_shifted = shift_pt_along_street((str_start[0], str_start[1]), x_angle, shift_length, slope_origin, b)
    #print(f"start point: {str_start[0], str_start[1]}, recording id:  {first_nearest_rec_ID} - time: {start_rec_time}")
    #print("next point:", x_shifted, y_shifted)

    while op(y_shifted, str_end[1]):
        recording_index = 0
        nearest_recordings = list_nearest_recordings(CONF.cyclo_srs, x_shifted, y_shifted, {}, False)
        nearest_rec_ID, rec_time = get_recording_id(nearest_recordings, recording_index)

        if nearest_rec_ID == "" and first_run:
            rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'recording_point': (), 'recording_year': 0})
            rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, rec_IDs)
            return rec_IDs
        elif nearest_rec_ID == "" and not first_run:
            rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'recording_point': (), 'recording_year': 0})
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
                rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'recording_point': (0,0), 'recording_year': 0})
                rec_IDs = get_nearest_recordings_for_street_pts((x_shifted,y_shifted), str_end, shift_length, slope_origin, rec_IDs)
                return rec_IDs
            elif nearest_rec_ID == "" and not first_run:
                rec_IDs.append({'recording_id': ec.CYCLO_NO_REC_ID_SINGLE, 'street_point': (x_shifted, y_shifted), 'recording_point': (0,0), 'recording_year': 0})
                return rec_IDs
            else:
                t_delta = abs(((rec_time - start_rec_time).total_seconds()/60))

            #print("SECOND WHILE recording index", recording_index, "recID", nearest_rec_ID, "bool:", first_run, "tdelta", t_delta, "time: ", rec_time)
     
        if nearest_rec_ID not in [item["recording_id"] for item in rec_IDs]:
            rec_IDs.append({'recording_id': nearest_rec_ID, 'street_point': (x_shifted, y_shifted), 'recording_point': (), 'recording_year': rec_time.year})
            
        x_shifted, y_shifted = shift_pt_along_street((x_shifted, y_shifted), x_angle, shift_length, slope_origin, b)
        #print(f"next point: {x_shifted,y_shifted}", "rec_ID_keys", [item["recording_id"] for item in rec_IDs])
        start_rec_time = rec_time

    return rec_IDs



def get_image_IDs_from_cyclomedia(segment_id:int, segmentation_number:int, rec_IDs:list, slope_origin:float, y_angle:float, max_distance:int):
    print(f"[i] Getting image IDs and images from cyclo")
    if len(rec_IDs) == 0:
        return rec_IDs

    # for the cyclomedia api the y_angle gives the deviation from north direction. for streets with falling slope
    # the y_angle is measured "on the other side" therefore it is not represention the deivation from north without adding 90
    if slope_origin < 0:
        y_angle = (90-math.degrees(y_angle)) + 90
    elif slope_origin > 0:
        y_angle = math.degrees(y_angle)
    # for filesaving
    if segmentation_number < 10:
        segmentation_number = "0" + str(segmentation_number)

    for idx, item in enumerate(rec_IDs):

        if item['recording_id'] == ec.CYCLO_NO_REC_ID_SINGLE:
            item['recording_point'] = (0,0)
            continue

        #direction 90/-90 would be on the right/left side of the car
        params = {'yaw': str(y_angle), 'hfov': '80'}
        response, recording_lat, recording_lon = render_by_ID(CONF.cyclo_srs, item['recording_id'], params, False)
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
                if idx < 10:
                    idx = "0" + str(idx)

                img_file_name = str(segment_id)+ "_" + str(segmentation_number) + "_" + str(idx) +  "_" + str(item['recording_id']) + ".jpg"
                with open(PATHS.CYCLO_IMG_FOLDER_PATH + img_file_name, 'wb') as file:
                    file.write(response.content)
            
        else:
            print(f"[!!!] BAD STATUSCODE: for image with id: {item['recording_id']}")
            item['recording_id'] = ec.CYCLO_BAD_RESPONSE_CODE
            item['recording_point'] = (0,0)
            continue

    return rec_IDs


def load_into_db(rec_IDs, segment_id, segmentation_number, connection):
    print("[i] Load to DB")
    cursor = connection.cursor()
    if check_for_only_error_values(rec_IDs):
        try:
            cursor.execute("""INSERT INTO segments_cyclomedia VALUES (%s, %s, %s, %s, %s, %s) """, (segment_id, ec.CYCLO_NO_REC_ID_TOTAL, segmentation_number, 0, 0, 0,))
            connection.commit()
        except psycopg2.errors.UniqueViolation:
            print(f"Value already in table. segment {segment_id}, segmentation number {segmentation_number}, order: {idx} ")
            connection.rollback()
            return
            
    else:
        for idx, dict_item in enumerate(rec_IDs):
            try:
                record_lat, record_lon = dict_item['recording_point'][0], dict_item['recording_point'][1]
                cursor.execute("""INSERT INTO segments_cyclomedia VALUES (%s, %s, %s, %s, %s, %s, %s) """, (segment_id, dict_item['recording_id'], segmentation_number, idx, record_lat, record_lon,dict_item['recording_year'], ))
                connection.commit()
            except psycopg2.errors.UniqueViolation as e:
                print(f"Value already in table. segment {segment_id}, segmentation number {segmentation_number}, order: {idx} ")
                connection.rollback()
                continue


# # suburb_list = [(ot_name, ot_nr), ..], in this case ot_nr is not relevant and can be 0 all the time
def get_cyclomedia_data(db_config, db_user, suburb_list):
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

                cursor.execute("""SELECT * FROM segments_segmentation WHERE segment_id = %s ORDER BY segmentation_number""", (segment_id, ))
                segmentation_result_rows = cursor.fetchall()

                #TODO: sollte nicht mehr auftreten nach einführung von error codes
                if segmentation_result_rows == []:
                    print("NO RESULT FOR ID %s", segment_id)
                    continue

                # check if information is valid #TODO zusammenführen
                elif len(segmentation_result_rows) == 1:
                    segmentation_no = segmentation_result_rows[0][1]
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
                        segmentation_number = segmentation_result_rows[0][1]
                        start_lat, start_lon = segmentation_result_rows[0][2], segmentation_result_rows[0][3]
                        end_lat, end_lon = segmentation_result_rows[0][4], segmentation_result_rows[0][5]
                        temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                        y_angle = find_angle_to_y(temp_coords)
                        slope_origin = calculate_slope(temp_coords)

                        rec_IDs = get_nearest_recordings_for_street_pts((start_lat, start_lon), (end_lat, end_lon), shift_length, slope_origin, [])
                        rec_IDs = get_image_IDs_from_cyclomedia(segment_id, segmentation_number, rec_IDs, slope_origin, y_angle, 9)

                        load_into_db(rec_IDs=rec_IDs, segment_id = segment_id, segmentation_number=segmentation_number, connection=con)
            
                    # segment is divided into smaller parts
                    elif len(segmentation_result_rows) > 1:
                        
                        for idx, row in enumerate(segmentation_result_rows):
                            segmentation_number = segmentation_result_rows[idx][1]
                            print("--segmentation_number: ", segmentation_number)
                            start_lat, start_lon = segmentation_result_rows[idx][2], segmentation_result_rows[idx][3]
                            end_lat, end_lon = segmentation_result_rows[idx][4], segmentation_result_rows[idx][5]
                            temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                            y_angle = find_angle_to_y(temp_coords)
                            slope_origin = calculate_slope(temp_coords)

                            rec_IDs = get_nearest_recordings_for_street_pts((start_lat, start_lon), (end_lat, end_lon), shift_length, slope_origin, [])
                            rec_IDs = get_image_IDs_from_cyclomedia(segment_id, segmentation_number, rec_IDs, slope_origin, y_angle, 9)

                            load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_number, connection=con)
                        
                    #break


if __name__ == "__main__":
    config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
                                                    #suburb list = tuple
    get_cyclomedia_data(config_path, PATHS.DB_USER, suburb_list=[])