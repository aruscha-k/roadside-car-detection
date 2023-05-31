import os

DB_CONFIG_FILE_NAME = "db_config.json"
LOAD_DATA_CONFIG_NAME = "load_data_config.json"

CYCLO_DETECTION_MODEL = "streetmodel_80img_00025lr_1500bs.pth"
AIR_DETECTION_MODEL = ""

RES_FOLDER_PATH = "./add-files"

DATASET_FOLDER_PATH = "datasets/complete"

DB_USER_ARUSCHA = os.path.join(RES_FOLDER_PATH, 'db_aruscha.json')
DB_USER = DB_USER_ARUSCHA

# ------ img resources --------#
IMG_FOLDER_PATH = "./imgs/"
if not os.path.exists(IMG_FOLDER_PATH):
    os.mkdir(IMG_FOLDER_PATH)
    
CYCLO_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "cyclomedia/"
if not os.path.exists(CYCLO_IMG_FOLDER_PATH):
    os.mkdir(CYCLO_IMG_FOLDER_PATH)

AIR_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "air/"
if not os.path.exists(AIR_IMG_FOLDER_PATH):
    os.mkdir(AIR_IMG_FOLDER_PATH)

AIR_TEMP_CROPPED_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "temp_crop/"
if not os.path.exists(AIR_TEMP_CROPPED_FOLDER_PATH):
    os.mkdir(AIR_TEMP_CROPPED_FOLDER_PATH)

AIR_CROPPED_ROTATED_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "rotated/"
if not os.path.exists(AIR_CROPPED_ROTATED_FOLDER_PATH):
    os.mkdir(AIR_CROPPED_ROTATED_FOLDER_PATH)