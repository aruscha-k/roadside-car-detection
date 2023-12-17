from DB_helpers import open_connection
from PATH_CONFIGS import DB_USER_ARUSCHA, DB_CONFIG_FILE_NAME, RES_FOLDER_PATH
from helpers_coordiantes import convert_coords


import json


def export_to_city_for_annotation(db_config, db_user, suburb_list):

    import pandas as pd
    sides_df = pd.read_csv('/Users/aruscha/Desktop/all_sides_iteration.csv')

    with open_connection(db_config, db_user) as con:
        cursor = con.cursor()

        for ot_name in suburb_list:
            print(f"Processing {ot_name}")

            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            segment_ids = [item[0] for item in cursor.fetchall()]

            filtered_df = sides_df[sides_df['segment_id'].isin(segment_ids)]
            filtered_df.to_csv(f'/Users/aruscha/Desktop/annotation_{ot_name}.csv')


def export_to_geojson_with_suburbs(db_config, db_user, suburb_list, parking_table):


    with open_connection(db_config, db_user) as con:

            cursor = con.cursor()
            if suburb_list == []:
          
                cursor.execute("""SELECT ot_name, ot_nr FROM ortsteile""")
                suburb_list = cursor.fetchall()

            features = []
            for ot_name, ot_nr in suburb_list:
  
                cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
                segment_id_list = [item[0] for item in cursor.fetchall()]
                for i, segment_id in enumerate(segment_id_list):

                    cursor.execute("""SELECT * FROM {} WHERE segment_id = %s""".format(parking_table), (segment_id, ))

    geojson_feature_left = {
                        "type" : "Feature",
                        "geometry" : {},
                        "properties" : {
                            "objectid" : 0,
                            "parking_left": "",
                            "certainty": 0 }
                    }
    
    geojson_feature_right = {
                        "type" : "Feature",
                        "geometry" : {},
                        "properties" : {
                            "objectid" : 0,
                            "parking_right": "",
                            "certainty": 0 }
                    }
    
    geojson_file = {
                    "type" : "FeatureCollection",
                    "name" : "strassen_segmente_with_parking",
                    "features" : features
                    }
    

def export_segmentation_to_geojson(db_config, db_user, parking_table, output_file_path):
    
    features = []
    with open_connection(db_config, db_user) as con:

        cursor = con.cursor()
        cursor.execute("""SELECT segment_id, segmentation_number, parking, value, percentage FROM {}""".format(parking_table))
        results = cursor.fetchall()
        for res in results:
            segment_id = res[0]
            segmentation_number = res[1]    
            parking = res[2]
            value = res[3]
            percentage = res[4]
             
            if parking == "left":
                # get side coordinates
                cursor.execute("""SELECT left_coords FROM segments_segmentation_sides WHERE segment_id = %s AND segmentation_number = %s""", (segment_id, segmentation_number, ))
                side_coordinates = cursor.fetchone()
                if side_coordinates is not None:
                    left_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in side_coordinates[0]]

                    geojson_feature_left = {
                            "type" : "Feature",
                            "geometry" : {
                                "type" : "LineString",
                                "coordinates" : left_coords},
                            "properties" : {
                                "objectid" : segment_id,
                                "segmentation_number": segmentation_number,
                                "parking_left": value,
                                "certainty": percentage }
                        }
                    features.append(geojson_feature_left)

            if parking == "right":
                # get side coordinates
                cursor.execute("""SELECT right_coords FROM segments_segmentation_sides WHERE segment_id = %s AND segmentation_number = %s""", (segment_id, segmentation_number, ))
                side_coordinates = cursor.fetchone()
                if side_coordinates is not None:
                    right_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in side_coordinates[0]]

                geojson_feature_right = {
                        "type" : "Feature",
                        "geometry" : {
                            "type" : "LineString",
                            "coordinates" : right_coords},
                        "properties" : {
                            "objectid" : segment_id,
                            "segmentation_number": segmentation_number,
                            "parking_right": value,
                            "certainty": percentage }
                    }
                features.append(geojson_feature_right)
    
    geojson_data = {
                    "type" : "FeatureCollection",
                    "name" : "strassen_segmente_with_parking",
                    "features" : features
                    }
    
    with open(output_file_path, 'w') as json_file:
        json.dump(geojson_data, json_file)


def export_iteration_to_geojson(db_config, db_user, parking_table, output_file_path):
    
    features = []
    with open_connection(db_config, db_user) as con:

        cursor = con.cursor()
        cursor.execute("""SELECT segment_id, segmentation_number, iteration_number, parking_side, value, percentage FROM {}""".format(parking_table))
        results = cursor.fetchall()
        for res in results:
            segment_id = res[0]
            segmentation_number = res[1]   
            iteration_number = res[2] 
            parking_side = res[3]
            value = res[4]
            percentage = res[5]
             
            if parking_side == "left":
                # get side coordinates
                cursor.execute("""SELECT left_coordinates FROM segments_segmentation_iteration WHERE segment_id = %s AND segmentation_number = %s AND iteration_number = %s""", (segment_id, segmentation_number, iteration_number, ))
                side_coordinates = cursor.fetchone()
                if side_coordinates is not None:
                    # left_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in side_coordinates[0]]
                    left_coords = side_coordinates[0]
                    

                geojson_feature_left = {
                        "type" : "Feature",
                        "geometry" : {
                            "type" : "LineString",
                            "coordinates" : left_coords},
                        "properties" : {
                            "objectid" : segment_id,
                            "segmentation_number": segmentation_number,
                            "iteration_number": iteration_number,
                            "parking_left": value,
                            "certainty": percentage }
                    }
                features.append(geojson_feature_left)

            if parking_side == "right":
                # get side coordinates
                cursor.execute("""SELECT right_coordinates FROM segments_segmentation_iteration WHERE segment_id = %s AND segmentation_number = %s AND iteration_number = %s""", (segment_id, segmentation_number, iteration_number,))
                side_coordinates = cursor.fetchone()
                if side_coordinates is not None:
                    # right_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in side_coordinates[0]]
                    right_coords = side_coordinates[0]

                geojson_feature_right = {
                        "type" : "Feature",
                        "geometry" : {
                            "type" : "LineString",
                            "coordinates" : right_coords},
                        "properties" : {
                            "objectid" : segment_id,
                            "segmentation_number": segmentation_number,
                            "iteration_number": iteration_number,
                            "parking_right": value,
                            "certainty": percentage }
                    }
                features.append(geojson_feature_right)
    
    geojson_data = {
                    "type" : "FeatureCollection",
                    "name" : "strassen_segmente_iteration_based_with_parking",
                    "features" : features
                    }
    
    with open(output_file_path, 'w') as json_file:
        json.dump(geojson_data, json_file)
    
    

if __name__ == "__main__":
    config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'
    export_iteration_to_geojson(db_config=config_path, db_user=DB_USER_ARUSCHA, parking_table="parking_iteration", output_file_path="firstrun_iterations_v1.geojson")
    # export_to_city_for_annotation(db_config=config_path, db_user=DB_USER_ARUSCHA, suburb_list=['Südvorstadt', 'Volkmarsdorf'])