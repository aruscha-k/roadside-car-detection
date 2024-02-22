import os

from GLOBAL_VARS import RECORDING_YEAR

LOG_FILES = "./logfiles/"
if not os.path.exists(LOG_FILES):
    os.mkdir(LOG_FILES)

RES_FOLDER_PATH = "./add-files"
DATASET_FOLDER_PATH = "datasets/complete/"
extern_AIR_IMGS_FOLDER_PATH = "/Volumes/PARKPLATZ/datasets/"

# ------ database config --------#
# DB_CONFIG_FILE_NAME = "db_config.json"
DB_CONFIG_FILE_NAME = "db_config_clipped.json"
LOAD_DATA_CONFIG_NAME = "load_data_config.json"
DB_USER_ARUSCHA = os.path.join(RES_FOLDER_PATH, 'db_aruscha.json')
DB_USER = DB_USER_ARUSCHA

# ------ ML models --------#
CYCLO_DETECTION_MODEL = "models/train2_streetmodel_150img_00025lr_1500bs.pth"
#AIR_DETECTION_MODEL = "parking_air3_LR00012_Maxiter5000_BS1500_totalloss01728.pth"
AIR_DETECTION_MODEL = "models/parking_air30_LR00015_maxiter2000_BS1500_totalloss0111.pth"
DRIVEWAY_DETECTION_MODEL = "models/model_20231108134516"

# ------ img resources --------#
local_IMG_FOLDER_PATH = "./imgs/"
extern_IMG_FOLDER_PATH = "/Volumes/PARKPLATZ/imgs_clipped/"
IMG_FOLDER_PATH = extern_IMG_FOLDER_PATH

if not os.path.exists(IMG_FOLDER_PATH):
    os.mkdir(IMG_FOLDER_PATH)    

# --- cyclomedia --- 
CYCLO_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "cyclomedia/" + str(RECORDING_YEAR) + "/"
if not os.path.exists(CYCLO_IMG_FOLDER_PATH):
    os.mkdir(CYCLO_IMG_FOLDER_PATH)

CYCLO_DRIVEWAYS_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "cyclomedia-driveways/" + str(RECORDING_YEAR) + "/"
if not os.path.exists(CYCLO_DRIVEWAYS_IMG_FOLDER_PATH):
    os.mkdir(CYCLO_DRIVEWAYS_IMG_FOLDER_PATH)

# --- air ---
AIR_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "air/"
if not os.path.exists(AIR_IMG_FOLDER_PATH):
    os.mkdir(AIR_IMG_FOLDER_PATH)

AIR_CROPPED_OUT_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "crop/" + str(RECORDING_YEAR) + "/"
if not os.path.exists(AIR_CROPPED_OUT_FOLDER_PATH):
    os.mkdir(AIR_CROPPED_OUT_FOLDER_PATH)

AIR_CROPPED_ITERATION_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "iteration/" + str(RECORDING_YEAR) + "/"
if not os.path.exists(AIR_CROPPED_ITERATION_FOLDER_PATH):
    os.mkdir(AIR_CROPPED_ITERATION_FOLDER_PATH)

AIR_CROPPED_ROTATED_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "rotated/" + str(RECORDING_YEAR) + "/"
if not os.path.exists(AIR_CROPPED_ROTATED_FOLDER_PATH):
    os.mkdir(AIR_CROPPED_ROTATED_FOLDER_PATH)

# ---  demo ML img ---
DEMO_IMGS_FOLDER_PATH = IMG_FOLDER_PATH + "demo/"
if not os.path.exists(DEMO_IMGS_FOLDER_PATH):
    os.mkdir(DEMO_IMGS_FOLDER_PATH)

DEMO_AIR_DETECTION_FOLDER_PATH = DEMO_IMGS_FOLDER_PATH + "air/"
if not os.path.exists(DEMO_AIR_DETECTION_FOLDER_PATH):
    os.mkdir(DEMO_AIR_DETECTION_FOLDER_PATH)

DEMO_CYCLO_DETECTION_FOLDER_PATH = DEMO_IMGS_FOLDER_PATH + "cyclomedia/"
if not os.path.exists(DEMO_CYCLO_DETECTION_FOLDER_PATH):
    os.mkdir(DEMO_CYCLO_DETECTION_FOLDER_PATH)