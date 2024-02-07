from DB_create_db_schema import run_create_db_schema
from DB_load_city_data import run_read_city_data
from DB_create_relations import add_ot_to_segments, create_segm_gid_relation, create_segmentation_and_iteration


if __name__ == "main":
    # CREATION OF ALL NECESSARY DATANBASES
    run_create_db_schema()
    run_read_city_data()
    add_ot_to_segments()
    create_segm_gid_relation()
    create_segmentation_and_iteration()


    # EXTRACTION OF IMAGES