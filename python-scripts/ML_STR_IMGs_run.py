
from DB_helpers import open_connection, load_json
import DB_helpers as db_helper
import STR_IMGs_config as CONF
from PATH_CONFIGS import CYCLO_IMG_FOLDER_PATH, RES_FOLDER_PATH, DB_CONFIG_FILE_NAME
from ML_STR_IMGs_methods import run_detection
import os

def run(db_config, suburb_list):
    with db_helper.open_connection(db_config, False) as con:
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

                cursor.execute("""SELECT record_id, segmentation_number, order_number FROM segments_cyclomedia WHERE segment_id = %s ORDER BY segmentation_number ASC, order_number ASC""", (segment_id, ))
                result_rows = cursor.fetchall()
                if result_rows == []:
                    print("no result for ", segment_id)
                    continue

                else:
                    img_path_list = []
                    for idx, row in enumerate(result_rows):

                        segmentation_number = result_rows[idx][1]
                        recording_id = result_rows[idx][0]
                        order_number = result_rows[idx][2]

                        if segmentation_number < 10:
                            segmentation_number = "0" + str(segmentation_number)
                        if order_number < 10:
                            order_number = "0" + str(order_number)

                        #read image and predict
                        img_file_path = CYCLO_IMG_FOLDER_PATH + str(segment_id)+ "_" + str(segmentation_number) + "_" + str(order_number) +  "__" + str(recording_id) + ".jpg"
                        if os.path.exists(img_file_path):
                            img_path_list.append(img_file_path)
                        else:
                            print("invalid path", img_file_path)

                    run_detection(img_path_list)

                    # TODO: write to DB

                if i == 5:
                    break





if __name__ == "__main__":

    db_config = load_json(RES_FOLDER_PATH +"/"+ DB_CONFIG_FILE_NAME)
    run(db_config, [("Lindenau", 0)])


#https://atlas.cyclomedia.com/PanoramaRendering/Render/WE4IK5SE/?apiKey=2_4lO_8ZuXEBuXY5m7oVWzE1KX41mvcd-PQZ2vElan85eLY9CPsdCLstCvYRWrQ5&srsName=epsg:55567837&direction=0&hfov=80
#test_rec_IDs = ['WE4IK5OM', 'WE4IK5SO', 'WE4IK5SN', 'WE4IK5SM', 'WE4IK5SL', 'WE4IK5SK', 'WE4IK5SJ', 'WE4IK5SI', 'WE4IK5SH', 'WE4IK5SG', 'WE4IK5SF', 'WE4IK5SE', 'WE4IK5SD', 'WE4IK5SC', 'WE4IK5SB', 'WE4IK5SA', 'WE4IK5S9', 'WE4IK5S8', 'WE4IK5S7', 'WE4IK5S6', 'WE4IK5S5', 'WE4MDYHX', 'WE4IK5N8']