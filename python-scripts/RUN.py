from DB_create_db_schema import run_create_db_schema
from DB_load_city_data import run_read_city_data
from DB_create_relations import add_ot_to_segments, create_segm_gid_relation, create_segmentation_and_iteration

from STR_IMGs_create_segment_data import get_cyclomedia_data
from AIR_IMGs_create_air_segments import create_air_segments
from STR_IMGs_create_driveway_data import get_cyclomedia_data_for_driveways

from ML_IMGs_run import run_ml_detection
from ML_result_merge import run_merge_ml_results


run_setup = True
run_image_extraction = True
run_image_detection = True

suburb_list = []

if __name__ == "main":
    # CREATION OF ALL NECESSARY DATANBASES
    if run_setup:
        run_create_db_schema()
        run_read_city_data()
        add_ot_to_segments()
        create_segm_gid_relation()
        create_segmentation_and_iteration()


    # EXTRACTION OF IMAGES; if db_config_path and db_user set to None, they are taken from config file
    if run_image_extraction:
        get_cyclomedia_data(db_config_path=None, db_user=None, suburb_list=suburb_list, cyclo_segment_db_table="segments_cyclomedia_withdeviation", debug_mode = False)
        get_cyclomedia_data_for_driveways(db_config_path=None, db_user=None, suburb_list=suburb_list, cyclo_segment_db_table="segments_cyclomedia_withdeviation")
        create_air_segments(db_config_path=None, db_user=None, suburb_list=suburb_list)

    # RUN ML DETECTION
    if run_image_detection:
        run_ml_detection(db_config_path=None, db_user=None, suburb_list=suburb_list, img_type="cyclo", result_table_name="parking_cyclo_nofilter") # img_type = "air" / "cyclo" 
        run_ml_detection(db_config_path=None, db_user=None, suburb_list=suburb_list, img_type="air", result_table_name="parking_iteration_air_only_nofilter") # img_type = "air" / "cyclo" 
        run_merge_ml_results(db_config_path=None, db_user=None, suburb_list=suburb_list, img_type="") # img_type = "air" / "cyclo" / "" (for both)