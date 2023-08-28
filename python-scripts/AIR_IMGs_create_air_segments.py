import ERROR_CODES as ec
from DB_helpers import open_connection
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, AIR_TEMP_CROPPED_FOLDER_PATH, DATASET_FOLDER_PATH, DB_USER
from AIR_IMGs_process import cut_out_shape
from helpers_geometry import calculate_bounding_box

import json

# suburb_list = [(ot_name, ot_nr), ..]
def create_air_segments(db_config_path, db_user, suburb_list):

    with open_connection(db_config_path, db_user) as con:
        recording_year = 2019
        cursor = con.cursor()
       
        if suburb_list == []:
             # get ortsteile and their number codes
            cursor.execute("""SELECT ot_name, ot_nr FROM ortsteile""")
            suburb_list = cursor.fetchall()
        
        for ot_name, ot_nr in suburb_list:
            print("Getting Segments in: ", ot_name)
            
            # get all segments for ot
            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            id_fetch = cursor.fetchall()
            segment_id_list = [item[0] for item in id_fetch]

            # in tif
            in_tif = DATASET_FOLDER_PATH + "/air-imgs/" + str(recording_year) +"/" + str(ot_nr) +"_"+ str(recording_year) + ".tif"

            for i, segment_id in enumerate(segment_id_list):
                print(f"------{i+1} of {len(segment_id_list)+1}, segment_ID: {segment_id}--------")

                 #get segment information
                cursor.execute("""SELECT segmentation_number, width, start_lat, start_lon, end_lat, end_lon FROM segments_segmentation WHERE segment_id = %s ORDER BY segmentation_number""", (segment_id, ))
                segmentation_result_rows = cursor.fetchall()

                if segmentation_result_rows == []:
                    print("NO RESULT FOR ID %s - skip!", segment_id)
                    continue

                # check if information is valid
                segmentation_number = segmentation_result_rows[0][0]
                if len(segmentation_result_rows) == 1:
                    if segmentation_number == ec.WRONG_COORD_SORTING:
                        #TODO
                        # rec_IDs = [{'recording_id': ec.WRONG_COORD_SORTING, 'street_point': (0,0), 'recording_point': (0,0), 'recording_year': 0}]
                        # load_into_db(rec_IDs=rec_IDs, segment_id=segment_id, segmentation_number=segmentation_number, connection=con)
                        print("[!] no segmentation information - SKIP")
                        continue
               
                #check if the data already exists in folder or in tag table?: TODO
                # else:
                    # if len(cyclo_result_rows) == len(segmentation_result_rows):
                    #     print("EXIST - SKIP")
                    #     continue
                median_breite = segmentation_result_rows[0][1]
                if median_breite == ec.NO_WIDTH or median_breite == ec.MULTIPLE_TRAFFIC_AREAS:
                    print("[!] no valid width information - SKIP")

                # cut out img:
                # segment is not divided into smaller parts
                if len(segmentation_result_rows) == 1:
                                  
                    segmentation_number = segmentation_result_rows[0][0]
                    start_lat, start_lon = segmentation_result_rows[0][2], segmentation_result_rows[0][3]
                    end_lat, end_lon = segmentation_result_rows[0][4], segmentation_result_rows[0][5]
                    temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                    segment_img_filename = str(ot_name) + "_" + str(segment_id) + "_" + str(segmentation_number) 

                    # calculate the bounding box
                    #bbox = [start_left, end_left, end_right, start_right]
                    bbox = calculate_bounding_box(temp_coords, median_breite)

                    out_tif = AIR_TEMP_CROPPED_FOLDER_PATH + segment_img_filename + ".tif"
                    cut_out_success = cut_out_shape(bbox, out_tif, in_tif)
                    
                    if cut_out_success:
                        cursor.execute("""INSERT INTO segments_air VALUES (%s, %s, %s, %s)""", (segment_id, segmentation_number, 0, json.dumps(bbox)), )
                        con.commit()
                    else:
                        print("CUT OUT NOT POSSIBLE")
                        continue #TODO?

                # segment is divided into smaller parts
                elif len(segmentation_result_rows) > 1:
                    for idx, row in enumerate(segmentation_result_rows):
                        segmentation_number = segmentation_result_rows[idx][0]
                        start_lat, start_lon = segmentation_result_rows[idx][2], segmentation_result_rows[idx][3]
                        end_lat, end_lon = segmentation_result_rows[idx][4], segmentation_result_rows[idx][5]
                    
                        segment_img_filename = str(ot_name) + "_" + str(segment_id) + "_" + str(segmentation_number)
            
                        temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                        bbox = calculate_bounding_box(temp_coords, median_breite)
                    
                        out_tif = AIR_TEMP_CROPPED_FOLDER_PATH + segment_img_filename + ".tif"
                        cut_out_success = cut_out_shape(bbox, out_tif, in_tif)
                        if cut_out_success:
                            cursor.execute("""INSERT INTO segments_air VALUES (%s, %s, %s, %s)""", (segment_id, segmentation_number, 0, json.dumps(bbox)), )
                            con.commit()
                        else:
                            print("CUT OUT NOT POSSIBLE")
                            continue #TODO?
                    

if __name__ == "__main__":
    config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
    create_air_segments(db_config_path=config_path, db_user=DB_USER, suburb_list=[('Südvorstadt', '40'), ("Anger-Crottendorf", "22"), ("Lindenau", 70), ("Volkmarsdorf", 21), ("Zentrum-Südost", "02")])