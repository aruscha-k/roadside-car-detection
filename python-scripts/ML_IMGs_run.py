
from DB_helpers import open_connection
from PATH_CONFIGS import CYCLO_IMG_FOLDER_PATH, AIR_CROPPED_ROTATED_FOLDER_PATH, RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER, LOG_FILES
from ML_IMGs_methods import run_detection
import ERROR_CODES as ec
from datetime import datetime
import os
import psycopg2

def log(img_type, logstart, logtime, message: str):
    log_file_name = str(logstart) + "_" + str(img_type) + ".txt"
    log_file = os.path.join(LOG_FILES, log_file)
    if os.path.exists(log_file):
        with open(log_file, 'a') as lfile:
            lfile.write(logtime, message)
    else:
        with open(log_file, 'w') as lfile:
            lfile.write(logtime, message)


def run(db_config, db_user, suburb_list, img_type, result_table_name):
    log_start = datetime.now()
    with open_connection(db_config, db_user) as con:
        
        cursor = con.cursor()

        if suburb_list == []:
             # get ortsteile and their number codes
            cursor.execute("""SELECT ot_name, ot_nr FROM ortsteile""")
            suburb_list = cursor.fetchall()
        
        for ot_name, ot_nr in suburb_list:
            print("[i] Getting Segments in ", ot_name)

            # get all segments
            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            segment_id_list = [item[0] for item in cursor.fetchall()]

            for i, segment_id in enumerate(segment_id_list):
                print(f"------{i+1} of {len(segment_id_list)+1}, segment_ID: {segment_id}--------")

                if img_type == "cyclo":
                    cursor.execute("""SELECT record_id, segmentation_number, order_number FROM segments_cyclomedia WHERE segment_id = %s ORDER BY segmentation_number ASC, order_number ASC""", (segment_id, ))
                elif img_type == "air":
                    cursor.execute("""SELECT segmentation_number FROM segments_segmentation WHERE segment_id = %s ORDER BY segmentation_number ASC""", (segment_id, ))

                result_rows = cursor.fetchall()
                if result_rows == []:
                    print("no result for ", segment_id)
                    log(img_type=img_type, logstart=log_start, logtime=datetime.now(), message=f"{segment_id}: No Result in segmentation")
                    continue

                else:
                    img_path_list = []
                    for idx, row in enumerate(result_rows):

                        if img_type == "cyclo":
                            segmentation_number = result_rows[idx][1]
                            recording_id = result_rows[idx][0]
                            order_number = result_rows[idx][2]
                            if recording_id in [ec.CYCLO_BAD_RESPONSE_CODE, ec.CYCLO_MAX_DIST, ec.CYCLO_NO_REC_ID_SINGLE, ec.CYCLO_NO_REC_ID_TOTAL, ec.WRONG_COORD_SORTING]:
                                log(img_type=img_type, logstart=log_start, logtime=datetime.now(), message=f"{segment_id}: Error code {recording_id}")

                            if segmentation_number < 10:
                                segmentation_number = "0" + str(segmentation_number)
                            if order_number < 10:
                                order_number = "0" + str(order_number)
                            img_file_path = CYCLO_IMG_FOLDER_PATH + str(segment_id)+ "_" + str(segmentation_number) + "_" + str(order_number) +  "__" + str(recording_id) + ".jpg"

                        elif img_type == "air":
                            segmentation_number = result_rows[idx][0]
                            img_file_path = AIR_CROPPED_ROTATED_FOLDER_PATH + str(ot_name) + "_" +  str(segment_id)+ "_" + str(segmentation_number) + ".tif"
                        
                        if os.path.exists(img_file_path):
                            img_path_list.append(img_file_path)
                        else:
                            print("invalid path", img_file_path)
                            break
                    
                    if img_path_list == []:
                        continue
                    parking_dict = run_detection(img_path_list, img_type)

                    #  write to DB # parking_dict = {'left': [()], 'right': []}
                    for key, value in parking_dict.items():

                        for (parking, percentage) in parking_dict[key]:
                            try:
                                if img_type == "cyclo":
                                    cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s)""".format(result_table_name), (segment_id, key, parking, percentage,))
                                elif img_type == "air":
                                    cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s)""".format(result_table_name), (segment_id, key, parking, percentage,))

                            except psycopg2.errors.UniqueViolation as e:
                                continue
                    con.commit()



if __name__ == "__main__":

    db_config_path = os.path.join(RES_FOLDER_PATH, DB_CONFIG_FILE_NAME)
    run(db_config_path, DB_USER, [("Lindenau", 70)], img_type="cyclo", result_table_name="parking_cyclomedia_train2")
    #run(db_config_path, DB_USER, [("Lindenau", 70)], img_type="air", result_table_name="parking_air")


#https://atlas.cyclomedia.com/PanoramaRendering/Render/WE4IK5SE/?apiKey=2_4lO_8ZuXEBuXY5m7oVWzE1KX41mvcd-PQZ2vElan85eLY9CPsdCLstCvYRWrQ5&srsName=epsg:55567837&direction=0&hfov=80
#test_rec_IDs = ['WE4IK5OM', 'WE4IK5SO', 'WE4IK5SN', 'WE4IK5SM', 'WE4IK5SL', 'WE4IK5SK', 'WE4IK5SJ', 'WE4IK5SI', 'WE4IK5SH', 'WE4IK5SG', 'WE4IK5SF', 'WE4IK5SE', 'WE4IK5SD', 'WE4IK5SC', 'WE4IK5SB', 'WE4IK5SA', 'WE4IK5S9', 'WE4IK5S8', 'WE4IK5S7', 'WE4IK5S6', 'WE4IK5S5', 'WE4MDYHX', 'WE4IK5N8']