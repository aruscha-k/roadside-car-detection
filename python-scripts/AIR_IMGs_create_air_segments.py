import DB_helpers as db_helper
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, AIR_TEMP_CROPPED_FOLDER_PATH, AIR_CROPPED_ROTATED_FOLDER_PATH, DATASET_FOLDER_PATH, DB_USER
from AIR_IMGs_process import calculate_bounding_box, get_rotation_angle_for_img, cut_out_shape, rotate_img_only


# suburb_list = [(ot_name, ot_nr), ..]
def create_air_segments(db_config, suburb_list):

    with db_helper.open_connection(db_config, DB_USER) as con:
        recording_year = 2019
        cursor = con.cursor()
       
        if suburb_list == []:
             # get ortsteile and their number codes
            cursor.execute("""SELECT ot_name, ot_nr FROM ortsteile""")
            suburb_list = cursor.fetchall()
        
        for ot_name, ot_nr in suburb_list:
            print("Getting Segments in: ", ot_name)
            
            # get all segments for ot
            cursor.execute("""SELECT id, segm_gid FROM segments WHERE ot_name = %s""", (ot_name, ))
            id_fetch = cursor.fetchall()
            segment_id_list = [item[0] for item in id_fetch]
            segment_gid_list = [item[1] for item in id_fetch]

            # in tif
            in_tif = DATASET_FOLDER_PATH + "/air-imgs/" + str(recording_year) +"/" + str(ot_nr) +"_"+ str(recording_year) + ".tif"

            for i, segment_id in enumerate(segment_id_list):
                print(f"------{i+1} of {len(segment_id_list)+1}, segment_ID: {segment_id}--------")

                # check if information is valid
                cursor.execute("""SELECT segmentation_number FROM segments_segmentation WHERE segment_id = %s""", (segment_id, ))
                segmentation_no = cursor.fetchall()
                if len(segmentation_no) == 1 and segmentation_no[0][0] == -1:
                    print("[!] information invalid - skip")
                    continue

                # get width of street segment
                cursor.execute("""SELECT median_breite FROM trafficareas WHERE segm_gid = %s""", (segment_gid_list[i], ))
                median_breite = cursor.fetchall()

                if median_breite == []:
                    print("[!] NO WIDTH FOR SEGMENT ", segment_id)
                    continue
                elif len(median_breite) > 1:
                    print("multiple areas . skip")
                    continue
                else:
                    median_breite = median_breite[0][0] + (1/3*median_breite[0][0] )
    
                #get segment information
                cursor.execute("""SELECT * FROM segments_segmentation WHERE segment_id = %s ORDER BY segmentation_number""", (segment_id, ))
                segmentation_result_rows = cursor.fetchall()

                if segmentation_result_rows == []:
                    print("NO RESULT FOR ID %s", segment_id)
                    continue
                #check if the data already exists in folder or in tag table?: TODO
                # else:
                    # if len(cyclo_result_rows) == len(segmentation_result_rows):
                    #     print("EXIST - SKIP")
                    #     continue

                #cut out img:
                # segment is not divided into smaller parts
                elif len(segmentation_result_rows) == 1:
                    segmentation_number = segmentation_result_rows[0][1]
                    start_lat, start_lon = segmentation_result_rows[0][2], segmentation_result_rows[0][3]
                    end_lat, end_lon = segmentation_result_rows[0][4], segmentation_result_rows[0][5]
                    temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                    
                    img_filename = str(ot_name) + "_" + str(segment_id) + "_" + str(segmentation_number)
                    bbox = calculate_bounding_box(temp_coords, median_breite)
                    rotation_angle = get_rotation_angle_for_img(temp_coords)
                    cut_out_success = cut_out_shape(bbox, AIR_TEMP_CROPPED_FOLDER_PATH + img_filename + ".tif", in_tif)

                    if cut_out_success:
                        #rotate_img_only(cropped_folder, rotated_folder, str(row['object_id']) + ".tif", rotation_angle)
                        rotate_img_only(AIR_TEMP_CROPPED_FOLDER_PATH, AIR_CROPPED_ROTATED_FOLDER_PATH, img_filename + ".tif", rotation_angle)
                        #TODO: WRITE TO DB

                # segment is divided into smaller parts
                elif len(segmentation_result_rows) > 1:
                    for idx, row in enumerate(segmentation_result_rows):
                        segmentation_number = segmentation_result_rows[idx][1]
                        start_lat, start_lon = segmentation_result_rows[idx][2], segmentation_result_rows[idx][3]
                        end_lat, end_lon = segmentation_result_rows[idx][4], segmentation_result_rows[idx][5]
                    
                        img_filename = str(ot_name) + "_" + str(segment_id) + "_" + str(segmentation_number)
            
                        temp_coords = [(start_lat, start_lon), (end_lat, end_lon)]
                        bbox = calculate_bounding_box(temp_coords, median_breite)
                        rotation_angle = get_rotation_angle_for_img(temp_coords)
                        cut_out_success = cut_out_shape(bbox, AIR_TEMP_CROPPED_FOLDER_PATH + img_filename + ".tif", in_tif)
                        if cut_out_success:
                            rotate_img_only(AIR_TEMP_CROPPED_FOLDER_PATH, AIR_CROPPED_ROTATED_FOLDER_PATH, img_filename + ".tif", rotation_angle)
                            #TODO: WRITE TO DB
                    


if __name__ == "__main__":
    config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
    db_config = db_helper.load_json(config_path)
    create_air_segments(db_config=db_config, suburb_list=[('Lindenau',70)])