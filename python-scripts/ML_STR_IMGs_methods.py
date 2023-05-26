import numpy as np
import cv2
import os
from functools import reduce
from collections import Counter
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg

from PATH_CONFIGS import RES_FOLDER_PATH, CYCLO_DETECTION_MODEL

# if "device_mode" in os.environ:
#     device_mode = os.environ['device_mode']

def load_model_and_predictor():

    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    cfg.DATASETS.TRAIN = ("test_set",)
    cfg.DATASETS.TEST = ()
    cfg.DATALOADER.NUM_WORKERS = 2
    cfg.SOLVER.IMS_PER_BATCH = 2
    cfg.SOLVER.BASE_LR = 0.0025  # pick a good LR
    cfg.SOLVER.MAX_ITER = 1500    # 300 iterations seems good enough for this toy dataset; you will need to train longer for a practical dataset
    cfg.SOLVER.STEPS = []        # do not decay learning rate
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 1500   # faster, and good enough for this toy dataset (default: 512)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3 
    cfg.MODEL.DEVICE = 'cpu'
    cfg.MODEL.WEIGHTS = os.path.join(RES_FOLDER_PATH, CYCLO_DETECTION_MODEL)  # path to the model we just trained
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.90   # set a custom testing threshold
    predictor = DefaultPredictor(cfg)
    return predictor


def add_no_detection_area(im):
    im_width = im.shape[1]
    im_height = im.shape[0]
    
    midpoint = (int(im_width/2),int(im_height/2)+50)
    # upper image area
    #upper_points = np.array([[(0,0), (0,midpoint[1]) ,(im_width, midpoint[1]), (im_width, 0)]])
    #im = cv2.fillPoly(im, pts=[upper_points], color=(0, 0, 0))
    
    midpoint = (int(im_width/2),int(im_height/2)-50)
    # car sight area
    car_left = (int(im_width/3)-50,im_height)
    car_right = ((2*int(im_width/3)+50),im_height)
    points = np.array([[car_left, midpoint, car_right]])
    im = cv2.fillPoly(im, pts=[points], color=(0, 0, 0))
    return im


def detect(im, predictor):
    # TODO: autos im sichtfeldverdeckung nachher abziehen
    im = add_no_detection_area(im)
    
    outputs = predictor(im)  # format is documented at https://detectron2.readthedocs.io/tutorials/models.html#model-output-format
    
    bboxes = outputs['instances'].pred_boxes.tensor.cpu().numpy()
    classes = outputs['instances'].pred_classes.cpu().numpy()
    
    return bboxes, classes


def assign_left_right(im, boxes, classes):
    left = []
    right = []
    im_width = im.shape[1]
    im_height = im.shape[0]
    midpoint = (int(im_width/2),int(im_height/2))
    for idx, box in enumerate(boxes):
        #[oben rechts (2 Pkt), unten rechts (2 
        x_start = box[0]
        x_end = box[2]
        if x_start < midpoint[0] and x_end < midpoint[0]:
            left.append(classes[idx])
        elif x_start > midpoint[0] and x_end > midpoint[0]:
            right.append(classes[idx])
    return left, right


def run_detection(img_list):
    predictor = load_model_and_predictor()

    predictions = {'left': [], 'right': []}
    for img in img_list:
        im = cv2.imread(img)
        if im is not None:
            bboxes, classes = detect(im, predictor)
            left, right = assign_left_right(im, bboxes, classes)
            # add [-1] if no cars were detected 
            if len(left) == 0:
                predictions['left'].append([-1])
            else: 
                predictions['left'].append(left)
            if len(right) == 0:
                predictions['right'].append([-1])
            else:
                predictions['right'].append(right)
                
    print(predictions)
    calculate_parking(predictions)
            
    return predictions


def calculate_parking(predictions):
    class_dict = {0: 'diagonal/senkrecht', 1:'parallel', 2:'baumscheibe', -1: 'kein Auto'}
    
    #num_predictions_left = len(predictions['left'])
    
    all_left = reduce(lambda a,b: a+b, predictions['left'])
        
    #num_predictions_right = len(predictions['right'])
    all_right = reduce(lambda a,b: a+b, predictions['right'])
    
    for i in range(0,3):
        print(f"left: {i+1}. run")
        num_left_most_common = Counter(all_left).most_common(i+1)[i][1]
        
        class_left_most_common = Counter(all_left).most_common(i+1)[i][0]
        left_percentage = num_left_most_common/len(all_left)*100
        print(f"Class: {class_dict[class_left_most_common]} dominates {round(left_percentage,2)} % on left side.")
        if left_percentage >= 51:
            break
        
    for i in range(0,3):
        print(f"right: {i+1}. run")
        num_right_most_common = Counter(all_right).most_common(i+1)[i][1]
        class_right_most_common = Counter(all_right).most_common(i+1)[i][0]
        right_percentage = num_right_most_common/len(all_right)*100
        print(f"Class: {class_dict[class_right_most_common]} dominates {round(right_percentage,2)} % on right side.")
        
        if right_percentage >= 51:
            break