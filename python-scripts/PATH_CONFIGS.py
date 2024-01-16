import os

DB_CONFIG_FILE_NAME = "db_config.json"
LOAD_DATA_CONFIG_NAME = "load_data_config.json"

CYCLO_DETECTION_MODEL = "models/train2_streetmodel_150img_00025lr_1500bs.pth"
#AIR_DETECTION_MODEL = "parking_air3_LR00012_Maxiter5000_BS1500_totalloss01728.pth"
AIR_DETECTION_MODEL = "models/parking_air30_LR00015_maxiter2000_BS1500_totalloss0111.pth"

RES_FOLDER_PATH = "./add-files"

LOG_FILES = "./logfiles/"
if not os.path.exists(LOG_FILES):
    os.mkdir(LOG_FILES)

DATASET_FOLDER_PATH = "datasets/complete/"
extern_AIR_IMGS_FOLDER_PATH = "/Volumes/PARKPLATZ/datasets/"

DB_USER_ARUSCHA = os.path.join(RES_FOLDER_PATH, 'db_aruscha.json')
DB_USER = DB_USER_ARUSCHA

# ------ img resources --------#
#IMG_FOLDER_PATH = "./imgs/"
extern_IMG_FOLDER_PATH = "/Volumes/PARKPLATZ/imgs/"
IMG_FOLDER_PATH = extern_IMG_FOLDER_PATH

if not os.path.exists(IMG_FOLDER_PATH):
    os.mkdir(IMG_FOLDER_PATH)    
    
CYCLO_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "cyclomedia/"
if not os.path.exists(CYCLO_IMG_FOLDER_PATH):
    os.mkdir(CYCLO_IMG_FOLDER_PATH)

CYCLO_90_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "cyclomedia90/"
if not os.path.exists(CYCLO_90_IMG_FOLDER_PATH):
    os.mkdir(CYCLO_90_IMG_FOLDER_PATH)

CYCLO_MINUS90_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "cyclomedia-90/"
if not os.path.exists(CYCLO_MINUS90_IMG_FOLDER_PATH):
    os.mkdir(CYCLO_MINUS90_IMG_FOLDER_PATH)

# --- air ---

AIR_IMG_FOLDER_PATH = IMG_FOLDER_PATH + "air/"
if not os.path.exists(AIR_IMG_FOLDER_PATH):
    os.mkdir(AIR_IMG_FOLDER_PATH)

AIR_CROPPED_OUT_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "crop/"
if not os.path.exists(AIR_CROPPED_OUT_FOLDER_PATH):
    os.mkdir(AIR_CROPPED_OUT_FOLDER_PATH)

AIR_CROPPED_ITERATION_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "iteration/"
if not os.path.exists(AIR_CROPPED_ITERATION_FOLDER_PATH):
    os.mkdir(AIR_CROPPED_ITERATION_FOLDER_PATH)

AIR_CROPPED_ROTATED_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "rotated/"
if not os.path.exists(AIR_CROPPED_ROTATED_FOLDER_PATH):
    os.mkdir(AIR_CROPPED_ROTATED_FOLDER_PATH)

# AIR_TRAIN_FOLDER_PATH = AIR_IMG_FOLDER_PATH + "train/"
# if not os.path.exists(AIR_TRAIN_FOLDER_PATH):
#     os.mkdir(AIR_TRAIN_FOLDER_PATH)

AIR_PADDED = AIR_IMG_FOLDER_PATH + "padded/"
if not os.path.exists(AIR_PADDED):
    os.mkdir(AIR_PADDED)

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