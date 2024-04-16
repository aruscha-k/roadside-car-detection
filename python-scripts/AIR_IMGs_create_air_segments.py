import ERROR_CODES as ec
from DB_helpers import open_connection
from GLOBAL_VARS import RECORDING_YEAR
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, AIR_CROPPED_OUT_FOLDER_PATH, AIR_CROPPED_ITERATION_FOLDER_PATH, DATASET_FOLDER_PATH, extern_AIR_IMGS_FOLDER_PATH, DB_USER
from AIR_IMGs_helper_methods import cut_out_shape
from helpers_geometry import calculate_bounding_box
from LOG import log

from datetime import datetime
import json
import psycopg2
import os

DATASET_FOLDER_PATH = extern_AIR_IMGS_FOLDER_PATH
log_start = None
execution_file = "AIR_IMGs_create_air_segments"


# suburb_list = [(ot_name, ot_nr), ..]
def create_air_segments(db_config_path:str, db_user:str, suburb_list:list):
    global log_start
    log_start = datetime.now()

    if not db_config_path:
        db_config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
    if not db_user:
        db_user = DB_USER

    with open_connection(db_config_path, db_user) as con:
        cursor = con.cursor()
       
        if suburb_list == []:
             # get ortsteile and their number codes
            cursor.execute("""SELECT ot_name, ot_nr FROM ortsteile""")
            suburb_list = cursor.fetchall()

        else:
            suburb_with_nr = []
            for ot_name in suburb_list:
                cursor.execute("""SELECT ot_nr FROM ortsteile WHERE ot_name = %s""", (ot_name, ))
                ot_nr = cursor.fetchone()
                if ot_nr == None:
                    print(f"[!] No ot_nr found for {ot_name}. CHECK SPELLING?")
                else:
                    suburb_with_nr.append((ot_name, ot_nr[0]))
            suburb_list = suburb_with_nr
            print(suburb_list)
        
        for ot_name, ot_nr in suburb_list:
            print("Getting Segments in: ", ot_name)
            
            # get all segments for ot
            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            id_fetch = cursor.fetchall()
            segment_id_list = [item[0] for item in id_fetch]

            # in tif
            in_tif = DATASET_FOLDER_PATH + "air-imgs/" + str(RECORDING_YEAR) +"/" + str(ot_nr) +"_"+ str(RECORDING_YEAR) + ".tif"
            if not os.path.exists(in_tif):
                print("[!] No input TIF to cut out from")
                continue

            for i, segment_id in enumerate(segment_id_list):
                print(f"------{i+1} of {len(segment_id_list)+1}, segment_ID: {segment_id}--------")

                 #get segment information
                cursor.execute("""SELECT segmentation_number, width, start_lat, start_lon, end_lat, end_lon, quadrant FROM segments_segmentation WHERE segment_id = %s ORDER BY segmentation_number""", (segment_id, ))
                segmentation_result_rows = cursor.fetchall()

                if segmentation_result_rows == []:
                    print("NO RESULT FOR ID %s - SKIP!", segment_id)
                    log(execution_file = execution_file, img_type="air", logstart=log_start, logtime=datetime.now(), message=f"No segmentation result for segment{segment_id}")
                    continue

                # check if information is valid
                segmentation_number = segmentation_result_rows[0][0]
                if len(segmentation_result_rows) == 1:
                    if segmentation_number == ec.WRONG_COORD_SORTING:
                        #TODO
                        # rec_IDs = [{'recording_id': ec.WRONG_COORD_SORTING, 'street_point': (0,0), 'recording_point': (0,0), 'recording_year': 0}]
                        # load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_number, connection=con)
                        log(execution_file = execution_file, img_type="air", logstart=log_start, logtime=datetime.now(), message=f"Wrong coord sorting for segment {segment_id}")
                        print("[!] no segmentation information - SKIP")
                        continue
               
                #check if the data already exists in folder or in tag table?: TODO
                else:
                    cursor.execute("""SELECT * FROM segments_air WHERE segment_id = %s AND segmentation_number = %s AND recording_year = %s""", (segment_id, segmentation_number, RECORDING_YEAR,))
                    segment_result_row = cursor.fetchall()
                    if segment_result_row != []:
                        print("EXIST - SKIP")
                        continue

                median_breite = segmentation_result_rows[0][1]
                if median_breite == ec.NO_WIDTH or median_breite == ec.MULTIPLE_TRAFFIC_AREAS:
                    print("[!] no valid width information - SKIP")
                    log(execution_file = execution_file, img_type="air", logstart=log_start, logtime=datetime.now(), message=f"No width for segment {segment_id}")
                    continue

                # cut out img:
                # segment is not divided into smaller parts
                if len(segmentation_result_rows) == 1:
                                  
                    segmentation_number = segmentation_result_rows[0][0]
                    start_lat, start_lon = segmentation_result_rows[0][2], segmentation_result_rows[0][3]
                    end_lat, end_lon = segmentation_result_rows[0][4], segmentation_result_rows[0][5]
                    quadrant = segmentation_result_rows[0][6]
                    temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                    segment_img_filename = str(ot_name) + "_" + str(segment_id) + "_" + str(segmentation_number) 

                    # calculate the bounding box
                            #bbox = [start_left, end_left, end_right, start_right]
                    bbox = calculate_bounding_box(temp_coords, median_breite, quadrant)

                    segment_out_tif = AIR_CROPPED_OUT_FOLDER_PATH + segment_img_filename + ".tif"
                    cut_out_success, message = cut_out_shape(bbox, segment_out_tif, in_tif)
                    
                    if cut_out_success:
                        try:
                            cursor.execute("""INSERT INTO segments_air (segment_id, segmentation_number, recording_year, bbox) VALUES (%s, %s, %s, %s)""", (segment_id, segmentation_number, RECORDING_YEAR, json.dumps(bbox)), )
                            con.commit()
                        except psycopg2.errors.UniqueViolation:
                            con.rollback()
                            continue

                        # cut out iteration images
                        cursor.execute("""SELECT iteration_number, left_coordinates, right_coordinates FROM segments_segmentation_iteration WHERE segment_id = %s AND segmentation_number = %s""", (segment_id, segmentation_number, ))
                        iteration_information = cursor.fetchall()

                        for item in iteration_information:
                            iteration_number = item[0]
                            left_coords = item[1]
                            right_coords = item[2]
                            iter_bbox = [left_coords[0], left_coords[1], right_coords[1], right_coords[0]]
                            iter_out_tif = AIR_CROPPED_ITERATION_FOLDER_PATH + str(ot_name) + "_" + str(segment_id) + "_" + str(segmentation_number) + "_" + str(iteration_number) + ".tif"

                            cut_out_success, message = cut_out_shape(bbox=iter_bbox, out_tif=iter_out_tif, in_tif=segment_out_tif)
                            if not cut_out_success:
                                log(execution_file = execution_file, img_type="air", logstart=log_start, logtime=datetime.now(), message=f"{segment_id}: {iteration_number}, No iteration image cut out!")

                    else:
                        print("[!] CUT OUT NOT POSSIBLE")
                        log(execution_file = execution_file, img_type="air", logstart=log_start, logtime=datetime.now(), message=f"{segment_id}: {message}")
                        continue #TODO? is this streets whose segment crosses 2 tifff files?

                # segment is divided into smaller parts
                elif len(segmentation_result_rows) > 1:
                    for idx, row in enumerate(segmentation_result_rows):
                        segmentation_number = segmentation_result_rows[idx][0]
                        start_lat, start_lon = segmentation_result_rows[idx][2], segmentation_result_rows[idx][3]
                        end_lat, end_lon = segmentation_result_rows[idx][4], segmentation_result_rows[idx][5]
                        quadrant = segmentation_result_rows[idx][6]
                    
                        segment_img_filename = str(ot_name) + "_" + str(segment_id) + "_" + str(segmentation_number)
            
                        temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                        bbox = calculate_bounding_box(temp_coords, median_breite, quadrant)
                    
                        segment_out_tif = AIR_CROPPED_OUT_FOLDER_PATH + segment_img_filename + ".tif"
                        cut_out_success, message = cut_out_shape(bbox, segment_out_tif, in_tif)
                        if cut_out_success:
                            try:
                                cursor.execute("""INSERT INTO segments_air (segment_id, segmentation_number, recording_year, bbox) VALUES (%s, %s, %s, %s)""", (segment_id, segmentation_number, RECORDING_YEAR, json.dumps(bbox)), )
                                con.commit()
                            except psycopg2.errors.UniqueViolation:
                                con.rollback()
                                continue
                            # cut out iteration images
                            cursor.execute("""SELECT iteration_number, left_coordinates, right_coordinates FROM segments_segmentation_iteration WHERE segment_id = %s AND segmentation_number = %s""", (segment_id, segmentation_number, ))
                            iteration_information = cursor.fetchall()

                            for item in iteration_information:
                                iteration_number = item[0]
                                left_coords = item[1]
                                right_coords = item[2]
                                iter_bbox = [left_coords[0], left_coords[1], right_coords[1], right_coords[0]]
                                iter_out_tif = AIR_CROPPED_ITERATION_FOLDER_PATH + str(ot_name) + "_" + str(segment_id) + "_" + str(segmentation_number) + "_" + str(iteration_number) + ".tif"
                                cut_out_success, message = cut_out_shape(bbox=iter_bbox, out_tif=iter_out_tif, in_tif=segment_out_tif)
                                if not cut_out_success:
                                    log(execution_file = execution_file, img_type="air", logstart=log_start, logtime=datetime.now(), message=f"{segment_id}: {iteration_number}, No iteration image cut out!")


                        else:
                            print("[!] CUT OUT NOT POSSIBLE")
                            log(execution_file = execution_file, img_type="air", logstart=log_start, logtime=datetime.now(), message=f"{segment_id}: {message}")
                            continue #TODO?
                    

if __name__ == "__main__":
    create_air_segments(db_config_path=None, db_user=None, suburb_list=[])