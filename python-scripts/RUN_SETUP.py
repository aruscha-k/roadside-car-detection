from DB_create_db_schema import run_create_db_schema
from DB_load_city_data import run_read_city_data
from DB_create_relations import add_ot_to_segments, create_segm_gid_relation, create_segmentation_and_iteration

from STR_IMGs_create_segment_data import get_cyclomedia_data
from AIR_IMGs_create_air_segments import create_air_segments


if __name__ == "main":
    # CREATION OF ALL NECESSARY DATANBASES
    run_create_db_schema()
    run_read_city_data()
    add_ot_to_segments()
    create_segm_gid_relation()
    create_segmentation_and_iteration()


    # EXTRACTION OF IMAGES; if db_config_path and db_user set to None, they are taken from config file
    get_cyclomedia_data(db_config_path=None, db_user=None, suburb_list=['Südvorstadt'], cyclo_segment_db_table="segments_cyclomedia_withdeviation", debug_mode = False)
    create_air_segments(db_config_path=None, db_user=None, suburb_list=[])