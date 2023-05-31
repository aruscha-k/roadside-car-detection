from DB_helpers import open_connection
from helpers_geometry import calculate_start_end_pt
from helpers_coordiantes import convert_coords, sort_coords
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER


def create_segm_gid_relation(db_config, db_user):
    print('Creating area_segment_relation table ....')

    with open_connection(db_config, db_user) as con:

        cursor = con.cursor()
        cursor.execute("""CREATE TABLE area_segment_relation AS SELECT id AS area_id, segm_gid FROM trafficareas;""")
        cursor.execute("""ALTER TABLE area_segment_relation ADD COLUMN multiple_areas boolean, ADD COLUMN segment_id int""")

        cursor.execute("""SELECT segm_gid FROM area_segment_relation""")
        #iterate all segm_gids and get the segment Id and the number of segm_gis in area table
        for segm_gid in cursor.fetchall():
            segm_gid = segm_gid[0]
       
            cursor.execute("""SELECT id FROM segments WHERE segm_gid = (%s)""",(segm_gid,))
            res = cursor.fetchone()
            if res is None:
                continue
            else:
                segment_id = res[0]

            cursor.execute("""SELECT count(segm_gid) FROM trafficareas WHERE segm_gid = (%s)""",(segm_gid,))
            num_entries = cursor.fetchone()
            if num_entries is None:
                num_entries = None

            if num_entries[0] == 1:
                cursor.execute("""UPDATE area_segment_relation 
                                    SET segment_id = %s, multiple_areas = FALSE
                                    WHERE segm_gid = %s""",(segment_id, segm_gid,))
            if num_entries[0] > 1:
                cursor.execute("""UPDATE area_segment_relation 
                                SET segment_id = %s, multiple_areas = TRUE
                                WHERE segm_gid = %s""",(segment_id, segm_gid,))


def create_segmentation(db_config, db_user):
    print('Creating segmentations ....')

    with open_connection(db_config, db_user) as con:
        cursor = con.cursor()
        cursor.execute("""SELECT id FROM segments""")
        segment_id_list = [item[0] for item in cursor.fetchall()]

        for segment_id in segment_id_list:
            cursor.execute("""SELECT geom_type FROM segments WHERE id = %s""", (segment_id, ))
            geom_type = cursor.fetchone()[0]

            # geom_type can be LineString or MultiLineString
            if geom_type == "LineString":
                cursor.execute("""SELECT geom_coordinates FROM segments WHERE id = %s""", (segment_id, ))
                coords = cursor.fetchone()[0]

                #TODO: check if segment exists already?

                # if more than two coordinates, street has a bend => 
                # partition the segment further and extract every two pairs of coordinate
                if len(coords) > 2:
                    #print(f"[i] more than 2 coords: {segment_id}")

                    converted_coords = [convert_coords("EPSG:25833", "EPSG:4326", pt[0], pt[1]) for pt in coords]
                    str_start, str_end = calculate_start_end_pt(converted_coords)
                    sorted_coords = sort_coords(converted_coords, str_start)
                    
                    # if sorting method didnt work TODO
                    if sorted_coords != []:
                        sorted_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in sorted_coords]
                        segmentation_counter = 1
                    else:
                        cursor.execute("""INSERT INTO segments_segmentation VALUES (%s, %s, %s, %s, %s, %s) """, (segment_id, -1,  -1, -1, -1, -1, ))

                    for i in range(0,len(sorted_coords)):
                        try:
                            cursor.execute("""INSERT INTO segments_segmentation VALUES (%s, %s, %s, %s, %s, %s) """, (segment_id, segmentation_counter,  sorted_coords[i][0], sorted_coords[i][1], sorted_coords[i+1][0], sorted_coords[i+1][1], ))
                            segmentation_counter += 1

                        except IndexError:
                            break   
                else:
                    segmentation_counter = 0 
                    converted_coords = [convert_coords("EPSG:25833", "EPSG:4326", pt[0], pt[1]) for pt in coords]
                    str_start, str_end = calculate_start_end_pt(converted_coords)
                    sorted_coords = sort_coords(converted_coords, str_start)
                    sorted_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in sorted_coords]
                    cursor.execute("""INSERT INTO segments_segmentation VALUES (%s, %s, %s, %s, %s, %s) """, (segment_id, segmentation_counter,  sorted_coords[0][0], sorted_coords[0][1], sorted_coords[1][0], sorted_coords[1][1], ))

def add_ot_to_segments(db_config, db_user):
    print("Add OT to segments...")
    with open_connection(db_config, db_user) as con:
        cursor = con.cursor()

        #convert geometry from JSON to postgis column type for tables segemtns and ortsteile
        # make sure POSTGIS EXTENSION IS INSTALLED
        for table in ['ortsteile', 'segments']:
            cursor.execute(""" 
                    ALTER TABLE {} ADD COLUMN geometry_from_json geometry;
                    UPDATE {} SET geometry_from_json = ST_GeomFromGeoJSON(geometry);
                    ALTER TABLE {} DROP COLUMN geometry;""".format(table, table, table))

        # add ot_name to segments table checking with ortsteile geometry
        cursor.execute(""" 
                UPDATE segments
                SET ot_name = ot.ot_name
                FROM ortsteile ot
                WHERE ST_Intersects(segments.geometry_from_json, ot.geometry_from_json);""")
        
        con.commit()


if __name__ == "__main__":
    config_path = f'{RES_FOLDER_PATH}/{DB_CONFIG_FILE_NAME}'

    add_ot_to_segments(config_path, DB_USER)
    create_segm_gid_relation(config_path, DB_USER)
    create_segmentation(config_path, DB_USER)