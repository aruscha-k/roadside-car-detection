
from DB_helpers import open_connection
from PATH_CONFIGS import CYCLO_IMG_FOLDER_PATH, AIR_CROPPED_ITERATION_FOLDER_PATH, RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER
from ML_IMGs_methods import run_detection
import ERROR_CODES as ec
from LOG import log

from datetime import datetime
import os
import psycopg2

# import matplotlib.pyplot as plt
# from shapely.geometry import Polygon


log_start = None
execution_file = "ML_IMGs_run"

def add_image_to_list(img_folder, img_file, img_position_information, img_path_and_position_list, img_type, segment_id):
    """helper method to check, if image for ML detection exists and to log in file if it doenst exist

    Args:
        img_folder (str): folder path to use for ML detection
        img_file (str): img name
        img_position_information (!! list or tuple !!): bbox of segment poly (list for air) or recording lat /lon (tuple for cyclo)
        img_path_and_position_list (list): list to add image to if exists
        img_type (str): air or cyclo
        segment_id (int): segment ID 

    Returns:
        list: list with or without the checked image file
    """
    if os.path.exists(os.path.join(img_folder, img_file)):
        img_path_and_position_list.append((img_file, img_position_information))
    else:
        print("[!!] invalid path", img_folder + img_file)
        img_path_and_position_list.append(("", (0,0)))
        log(execution_file = execution_file, img_type=img_type, logstart=log_start, logtime=datetime.now(), message= f"no file found for segment_id {segment_id}")
    return img_path_and_position_list


def run_ml_detection(db_config_path:str, db_user:str, suburb_list:list, img_type:str, result_table_name:str):
    """ run methods to get images, use ML detection and write results to DB
        iterate all segments in suburb and, for each segment fetch all iteration steps (bounding boxes). for each box, check which record IDs (cyclo) / detected cars (air) lie within and run ML on them
        write result to DB
    Args:
        db_config_path (str): path to config file
        db_user (str): DB user to log in
        suburb_list (list of tuples): (ot_name, ot_nummer)
        img_type (str): air or cyclo
        result_table_name (str): the table of the DB to write into
    """
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
        
        for ot_name, ot_nr in suburb_list:
            print("[i] Getting Segments in ", ot_name)

            # get all segments
            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            segment_id_list = [item[0] for item in cursor.fetchall()]

            for i, segment_id in enumerate(segment_id_list):
                print(f"------{i+1} of {len(segment_id_list)+1}, segment_ID: {segment_id}--------")
                
                cursor.execute("""SELECT segmentation_number FROM segments_segmentation WHERE segment_id = %s ORDER BY segmentation_number ASC""", (segment_id, ))
                segments_segmentation_rows = cursor.fetchall()
                if segments_segmentation_rows == []:
                    print("no result for segment: ", segment_id)
                    log(execution_file = execution_file, img_type=img_type, logstart=log_start, logtime=datetime.now(), message=f"{segment_id}: No Result for segment")
                    continue

                else:
                    # iterate result rows segmentation rows
                    for idx, row in enumerate(segments_segmentation_rows):
                        segmentation_number = segments_segmentation_rows[idx][0]
                        print("--segmentation number:", segmentation_number)

                        # get iteration step information; left_coordinates/right_coordinates = 2 coordpairs each
                        # if not iteration information was found, skip parking detection
                        cursor.execute(""" SELECT iteration_number, left_coordinates, right_coordinates FROM segments_segmentation_iteration WHERE segment_id = %s AND segmentation_number = %s ORDER BY iteration_number ASC""", (segment_id, segmentation_number, ))
                        iteration_result_rows = cursor.fetchall()
                        if iteration_result_rows == []:
                            print("no iteration information for segment: ", segment_id)
                            log(execution_file = execution_file, img_type=img_type, logstart=log_start, logtime=datetime.now(), message=f"{segment_id}: No iteration information for segment")
                            continue


                        # check for existing in DB: if in the parking table (parking_res_count) there is the same number as iteration numbers * 2 (for left, right), there is already an entry so SKIP
                        cursor.execute("""SELECT count(*) FROM {} WHERE segment_id = %s AND segmentation_number = %s""".format(result_table_name), (segment_id, segmentation_number,))
                        parking_res_count = cursor.fetchone()[0]
                        if parking_res_count == (len(iteration_result_rows)*2):
                            print("EXISTS - skip")
                            continue


                        img_filename_and_position_list = []
                        if img_type == "cyclo":
                            
                            cursor.execute("""SELECT recording_id, recording_lat, recording_lon FROM segments_cyclomedia_newmethod WHERE segment_id = %s AND segmentation_number = %s""", (segment_id, segmentation_number, ))
                            cyclo_rows = cursor.fetchall()
                            for row in cyclo_rows:
                            
                                recording_id = row[0]
                                recording_lat, recording_lon = row[1], row[2]
                        
                                if segmentation_number < 10:
                                    segmentation_no_string = "0" + str(segmentation_number)
                                else:
                                    segmentation_no_string = str(segmentation_number)
            
                                img_file_name = str(segment_id)+ "_" + segmentation_no_string +  "_" + str(recording_id) + ".jpg"
                                img_folder = os.path.join(CYCLO_IMG_FOLDER_PATH, ot_name + "/")
                                img_filename_and_position_list = add_image_to_list(img_folder = img_folder, img_file = img_file_name, img_position_information = (recording_lat, recording_lon), img_path_and_position_list = img_filename_and_position_list, img_type=img_type, segment_id=segment_id)
           

                        iter_information = {}
                        for iteration_row in iteration_result_rows:
                        
                            iteration_number = iteration_row[0]
                            left_coords, right_coords = iteration_row[1], iteration_row[2]
                            iteration_poly = [left_coords[0], left_coords[1], right_coords[1], right_coords[0]]
                            iter_information[iteration_number] = iteration_poly

                            if img_type == "air":
                                img_file_name = str(ot_name) + "_" +  str(segment_id)+ "_" + str(segmentation_number) + "_" + str(iteration_number) + ".tif"
                                img_filename_and_position_list = add_image_to_list(img_folder = AIR_CROPPED_ITERATION_FOLDER_PATH, img_file = img_file_name, img_position_information = iteration_poly, img_path_and_position_list = img_filename_and_position_list, img_type=img_type, segment_id=segment_id)

                        #print(img_filename_and_position_list,"\n", iter_information)
                        parking_dict = run_detection(img_filename_and_position_list, ot_name, img_type, iter_information, filter_unparked_cars=False)
                        
                        # write to DB # parking_dict = {iteration_number: {'left': (parking, percentage), 'right': (parking, percentage)}}
                        for iteration_number, value in parking_dict.items():
                            for side, (parking, percentage) in value.items():
                                try:
                                    cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s, %s, %s)""".format(result_table_name), (segment_id, segmentation_number, iteration_number, side, parking, percentage,))
                                    con.commit()
                                   
                                except psycopg2.errors.UniqueViolation as e:
                                    print(e) #TODO LOG?
                                    con.rollback()


if __name__ == "__main__":
    #run_ml_detection(db_config_path=None, db_user=None, suburb_list=['Südvorstadt'], img_type="cyclo", result_table_name="parking_cyclo_nofilter")
    run_ml_detection(db_config_path=None, db_user=None, suburb_list=['Südvorstadt'], img_type="air", result_table_name="parking_iteration_air_only_nofilter")


#https://atlas.cyclomedia.com/PanoramaRendering/Render/WE4IK5SE/?apiKey=2_4lO_8ZuXEBuXY5m7oVWzE1KX41mvcd-PQZ2vElan85eLY9CPsdCLstCvYRWrQ5&srsName=epsg:55567837&direction=0&hfov=80
#test_rec_IDs = ['WE4IK5OM', 'WE4IK5SO', 'WE4IK5SN', 'WE4IK5SM', 'WE4IK5SL', 'WE4IK5SK', 'WE4IK5SJ', 'WE4IK5SI', 'WE4IK5SH', 'WE4IK5SG', 'WE4IK5SF', 'WE4IK5SE', 'WE4IK5SD', 'WE4IK5SC', 'WE4IK5SB', 'WE4IK5SA', 'WE4IK5S9', 'WE4IK5S8', 'WE4IK5S7', 'WE4IK5S6', 'WE4IK5S5', 'WE4MDYHX', 'WE4IK5N8']