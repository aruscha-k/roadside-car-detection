import numpy as np
import cv2
import os
import torch
from sklearn.cluster import KMeans
from functools import reduce
from collections import Counter
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg

from PATH_CONFIGS import RES_FOLDER_PATH, CYCLO_DETECTION_MODEL, AIR_DETECTION_MODEL


def load_air_predictor():
    air_cfg = get_cfg()
    if not torch.cuda.is_available():
        print('not using gpu acceleration')
        air_cfg.MODEL.DEVICE = 'cpu'
    air_cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    air_cfg.MODEL.WEIGHTS = os.path.join(RES_FOLDER_PATH, AIR_DETECTION_MODEL)
    air_cfg.MODEL.ROI_HEADS.NUM_CLASSES = 5
    air_cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.90
    predictor = DefaultPredictor(air_cfg)
    return predictor

# OLD NET
# def load_cyclo_predictor():

#     cfg = get_cfg()
#     cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
#     cfg.DATASETS.TRAIN = ("test_set",)
#     cfg.DATASETS.TEST = ()
#     cfg.DATALOADER.NUM_WORKERS = 2
#     cfg.SOLVER.IMS_PER_BATCH = 2
#     cfg.SOLVER.BASE_LR = 0.0025  # pick a good LR
#     cfg.SOLVER.MAX_ITER = 1500    # 300 iterations seems good enough for this toy dataset; you will need to train longer for a practical dataset
#     cfg.SOLVER.STEPS = []        # do not decay learning rate
#     cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 1500   # faster, and good enough for this toy dataset (default: 512)
#     cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3 
#     cfg.MODEL.DEVICE = 'cpu'
#     cfg.MODEL.WEIGHTS = os.path.join(RES_FOLDER_PATH, CYCLO_DETECTION_MODEL)  # path to the model we just trained
#     cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.90   # set a custom testing threshold
#     predictor = DefaultPredictor(cfg)
#     return predictor

def load_cyclo_predictor():
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    cfg.DATASETS.TRAIN = ("test_set",)
    cfg.DATASETS.TEST = ()
    cfg.DATALOADER.NUM_WORKERS = 2
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml")  # Let training initialize from model zoo
    cfg.SOLVER.IMS_PER_BATCH = 2
    cfg.SOLVER.BASE_LR = 0.0025  # pick a good LR
    cfg.SOLVER.MAX_ITER = 1500    # 300 iterations seems good enough for this toy dataset; you will need to train longer for a practical dataset
    cfg.SOLVER.STEPS = []        # do not decay learning rate
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 1500   # faster, and good enough for this toy dataset (default: 512)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2 
    cfg.MODEL.DEVICE = 'cpu'
    cfg.MODEL.WEIGHTS = os.path.join(RES_FOLDER_PATH, CYCLO_DETECTION_MODEL)  # path to the model we just trained
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.90   # set a custom testing threshold
    predictor = DefaultPredictor(cfg)
    return predictor


def remove_unparked_cars_for_air(instances):
    # cluster the instances on their x cooridinates and remove the outliers, there should be two clusters
    # one cluster for each side of the street. the outliers are cars that are not parked
    centers = instances.pred_boxes.get_centers().cpu().numpy()

    # Cluster the x-coordinates using K-means
    kmeans = KMeans(n_clusters=2)
    centers_x = centers[:, 0].reshape(-1, 1)
    kmeans.fit(centers_x)
    cluster_centers = kmeans.cluster_centers_

    # Calculate the distance of all points to the closest cluster center
    distances = np.empty_like(centers_x)
    for i in range(len(centers_x)):
        distances[i] = min(abs(centers_x[i] - cluster_centers[0]), abs(centers_x[i] - cluster_centers[1]))

    # Define a threshold for the maximum distance from the cluster center
    max_distance = abs(cluster_centers[0][0] - cluster_centers[1][0]) * 0.4

    # Identify the points that are too far from the cluster centers
    outliers = np.where(distances > max_distance)[0]
    print("Removing " + str(len(outliers)) + " unparked cars")

    # Remove the outlier points from the instances object
    instances = instances[~np.isin(np.arange(len(centers)), outliers)]

    return instances


def add_no_detection_area_for_cyclo(im):
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


def calculate_parking(predictions, img_type):
    if img_type == "cyclo":
        class_dict = {0: 'parallel', 1: 'diagonal/senkrecht', -1: 'kein Auto'}
    elif img_type == "air":
        class_dict = {0: 'diagonal/senkrecht', 1: 'parallel', 2: 'baumscheibe', 3:'sperrflaeche', 4:'zebrastreifen', -1: 'kein Auto'}
    parking_dict = {'left': [], 'right': []}
    
    all_left = reduce(lambda a,b: a+b, predictions['left'])
    all_right = reduce(lambda a,b: a+b, predictions['right'])
    
    full_percentage = 100
    for i in range(0,3):
        num_left_most_common = Counter(all_left).most_common(i+1)[i][1]
        class_left_most_common = Counter(all_left).most_common(i+1)[i][0]
        left_percentage = num_left_most_common/len(all_left)*100
        full_percentage = full_percentage - left_percentage
        parking_dict['left'].append((class_dict[class_left_most_common],round(left_percentage,2)))

        #print(f"left: {i+1}. run")
        #print(f"Class: {class_dict[class_left_most_common]} dominates {round(left_percentage,2)} % on left side.")
        if left_percentage >= 51 or full_percentage <= 25:
            break
    
    full_percentage = 100
    for i in range(0,3):
        
        num_right_most_common = Counter(all_right).most_common(i+1)[i][1]
        class_right_most_common = Counter(all_right).most_common(i+1)[i][0]
        right_percentage = num_right_most_common / len(all_right)*100
        full_percentage = full_percentage - right_percentage
        parking_dict['right'].append((class_dict[class_right_most_common], round(right_percentage,2)))
        
        #print(f"right: {i+1}. run")
        #print(f"Class: {class_dict[class_right_most_common]} dominates {round(right_percentage,2)} % on right side.")
        if right_percentage >= 51 or full_percentage <= 25:
            break

    return parking_dict


def run_detection(img_list, img_type):
    
    if img_type == "air":
        predictor = load_air_predictor()
    elif img_type == "cyclo":
        predictor = load_cyclo_predictor()
    else:
        print("[!] invalid img type - cannot load predictor")

    predictions = {'left': [], 'right': []}
    for img in img_list:
        im = cv2.imread(img)
        if im is not None:

            if img_type == "cyclo":
                im = add_no_detection_area_for_cyclo(im)

            outputs = predictor(im)
            instances = outputs["instances"].to("cpu")
            #remove cars not parked at the side in AIR IMAGES ONLY 

            if img_type == "air" and len(instances) > 2:
                instances = remove_unparked_cars_for_air(instances) 
            
            bboxes = instances.pred_boxes.tensor.cpu().numpy()
            classes = instances.pred_classes.cpu().numpy()
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
                
    parking_dict =  calculate_parking(predictions, img_type)
    print(parking_dict)
            
    return parking_dict


# -------- for debug only ----------------
# visualize prediction for 1 image
def visualize_prediction(filename, img_type):
    if img_type == "air":
        predictor = load_air_predictor()
        metadata = {"thing_classes": ['auto-diagonal', 'auto-parallel', 'baumscheibe', 'sperrflaeche', 'zebrastreifen']}
    elif img_type == "cyclo":
        predictor = load_cyclo_predictor()
        metadata = {"thing_classes": ['parallel', 'diagonal/senkrecht']}
    
    im = cv2.imread(filename)
    outputs = predictor(im)
    instances = outputs["instances"].to("cpu")
    
    v = Visualizer(im[:, :, ::-1], metadata=metadata, scale=1.0)
    out = v.draw_instance_predictions(instances)
    cv2.imshow('Prediction', out.get_image()[:, :, ::-1])
    cv2.waitKey(0)


if __name__ == "__main__":
    from detectron2.utils.visualizer import Visualizer

    visualize_prediction()