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

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches

from PATH_CONFIGS import RES_FOLDER_PATH, CYCLO_DETECTION_MODEL, AIR_DETECTION_MODEL
from helpers_coordiantes import is_point_within_polygon
from helpers_geometry import find_angle_to_y


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


def rotate_image_and_bboxes(filename, angle, bboxes):
    # Get the height and width of the image
    height, width = cv2.imread(filename).shape[:2]

    # Calculate the center of the image
    center_x = width / 2
    center_y = height / 2

    # Calculate the rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D((center_x, center_y), angle, 1.0)

    # Calculate the sine and cosine of the rotation angle
    abs_cos_angle = abs(rotation_matrix[0, 0])
    abs_sin_angle = abs(rotation_matrix[0, 1])

    # Calculate the new dimensions of the image
    new_width = int(height * abs_sin_angle + width * abs_cos_angle)
    new_height = int(height * abs_cos_angle + width * abs_sin_angle)

    # Calculate the translation matrix to center the image after rotation
    dx = int((new_width - width) / 2)
    dy = int((new_height - height) / 2)

    # img = Image.open(filename)
    # # expand 1 is used to keep the image from beeing cropped when rotated >90
    # rotated_img = img.rotate(angle=angle, expand=1)

    # Calculate the new coordinates of the bounding boxes
    rotated_bboxes  = []
    centers = []
    for bbox in bboxes:
        # Extract the coordinates of the bounding box
        x1, y1, x3, y3 = bbox
        x2 = x3
        y2 = y1
        x4 = x1
        y4 = y3

        # Translate the coordinates to the center of the image
        x1 -= center_x
        y1 -= center_y
        x2 -= center_x
        y2 -= center_y
        x3 -= center_x
        y3 -= center_y
        x4 -= center_x
        y4 -= center_y

        # Rotate the coordinates in the opposite direction
        new_x1 = x1 * abs_cos_angle + y1 * abs_sin_angle
        new_y1 = -x1 * abs_sin_angle + y1 * abs_cos_angle
        new_x2 = x2 * abs_cos_angle + y2 * abs_sin_angle
        new_y2 = -x2 * abs_sin_angle + y2 * abs_cos_angle
        new_x3 = x3 * abs_cos_angle + y3 * abs_sin_angle
        new_y3 = -x3 * abs_sin_angle + y3 * abs_cos_angle
        new_x4 = x4 * abs_cos_angle + y4 * abs_sin_angle
        new_y4 = -x4 * abs_sin_angle + y4 * abs_cos_angle

        # Translate the coordinates back to the top-left corner of the image
        new_x1 += center_x + dx
        new_y1 += center_y + dy
        new_x2 += center_x + dx
        new_y2 += center_y + dy
        new_x3 += center_x + dx
        new_y3 += center_y + dy
        new_x4 += center_x + dx
        new_y4 += center_y + dy

        # bbox_center_x = (new_x1 + new_x3) / 2
        # bbox_center_y = (new_y1 + new_y3) / 2

        # Add the new coordinates to the list of bounding boxes
        rotated_bboxes .append(
            [int(new_x1), int(new_y1), int(new_x2), int(new_y2), int(new_x3), int(new_y3), int(new_x4), int(new_y4)])
        #centers.append([int(bbox_center_x), int(bbox_center_y)])

    return rotated_bboxes 



def calculate_iou(box1, box2):
    # Calculate the coordinates of the intersection rectangle
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    # If the boxes do not overlap, return IoU of 0
    if x2 < x1 or y2 < y1:
        return 0.0
    
    # Calculate the areas of the two boxes
    area_box1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area_box2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    # Calculate the area of overlap
    intersection_area = (x2 - x1) * (y2 - y1)
    
    # Calculate the area of union
    union_area = area_box1 + area_box2 - intersection_area
    
    # Calculate the IoU
    iou = intersection_area / union_area
    
    return iou


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


# function to detect midpoint of image and assign bboxes to left or right side depending on their positions in regard to the midpoint
# RETURNS: left / right (list of tuples (bbox, class)
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
            left.append((box, classes[idx]))
        elif x_start > midpoint[0] and x_end > midpoint[0]:
            right.append((box, classes[idx]))
    return left, right



def calculate_parking(predictions, img_type):
    parking_dict = dict()

    if img_type == "cyclo":
        class_dict = {0: 'parallel', 1: 'diagonal/senkrecht', -1: 'kein Auto'}
    elif img_type == "air":
        class_dict = {0: 'diagonal/senkrecht', 1: 'parallel', 2: 'baumscheibe', 3:'sperrflaeche', 4:'zebrastreifen', -1: 'kein Auto'}

    for iteration_number in predictions.keys():
        parking_dict[iteration_number] = {}
        # all_left = reduce(lambda a,b: a+b, predictions[iteration_number]['left'])
        # all_right = reduce(lambda a,b: a+b, predictions[iteration_number]['right'])

        #METHOD TO ADD ONLY THE BEST DETECTION PERCENTAGE
        # most_common(1) chooses only the first most common item
        # Extract the second item from each tuple (class) and count their occurrences
        num_left_most_common = Counter(item[1] for sublist in predictions[iteration_number]['left'] for item in sublist).most_common(1)[0][1]
        class_left_most_common = Counter(item[1] for sublist in predictions[iteration_number]['left'] for item in sublist).most_common(1)[0][0]
        left_percentage = num_left_most_common/len(predictions[iteration_number]['left'])*100
        parking_dict[iteration_number]['left'] = ((class_dict[class_left_most_common], round(left_percentage,2)))

        num_right_most_common = Counter(item[1] for sublist in predictions[iteration_number]['right'] for item in sublist).most_common(1)[0][1]
        class_right_most_common = Counter(item[1] for sublist in predictions[iteration_number]['right'] for item in sublist).most_common(1)[0][0]
        right_percentage = num_right_most_common / len(predictions[iteration_number]['right'])*100
        parking_dict[iteration_number]['right'] = ((class_dict[class_right_most_common], round(right_percentage,2)))


    # METHOD TO ADD ALL DETECTION PERCENTAGES
    # full_percentage = 100
    # for i in range(0,3):
    #     num_left_most_common = Counter(all_left).most_common(i+1)[i][1]
    #     class_left_most_common = Counter(all_left).most_common(i+1)[i][0]
    #     left_percentage = num_left_most_common/len(all_left)*100
    #     full_percentage = full_percentage - left_percentage
    #     parking_dict['left'].append((class_dict[class_left_most_common], round(left_percentage,2)))

    #     #print(f"left: {i+1}. run")
    #     #print(f"Class: {class_dict[class_left_most_common]} dominates {round(left_percentage,2)} % on left side.")
    #     if left_percentage >= 51 or full_percentage <= 25:
    #         break
    
    # full_percentage = 100
    # for i in range(0,3):
        
    #     num_right_most_common = Counter(all_right).most_common(i+1)[i][1]
    #     class_right_most_common = Counter(all_right).most_common(i+1)[i][0]
    #     right_percentage = num_right_most_common / len(all_right)*100
    #     full_percentage = full_percentage - right_percentage
    #     parking_dict['right'].append((class_dict[class_right_most_common], round(right_percentage,2)))
        
    #     #print(f"right: {i+1}. run")
    #     #print(f"Class: {class_dict[class_right_most_common]} dominates {round(right_percentage,2)} % on right side.")
    #     if right_percentage >= 51 or full_percentage <= 25:
    #         break

    return parking_dict

# img_path_and_position_list = (imgpath, (recording_lat, recording_lon))
def run_detection(img_path_and_position_list, img_type, iter_information_dict):
    print("[i] Running parking detection")

    if img_type == "air":
        predictor = load_air_predictor()
    elif img_type == "cyclo":
        predictor = load_cyclo_predictor()
    else:
        print("[!] invalid img type - cannot load predictor")

    predictions = dict()
    for iteration_number, iteration_poly in iter_information_dict.items():
        print("iteration number: ", iteration_number)
        
        #if type is cyclo, have to find the recordings first that lie within the iteration box
        if img_type == "cyclo":
            iteration_record_id_list = [img_path for img_path, (recording_lat, recording_lon) in img_path_and_position_list if is_point_within_polygon((recording_lat, recording_lon), iteration_poly)]
            print(iteration_record_id_list)
            for img_path in iteration_record_id_list:
                im = cv2.imread(img_path)
                if im is not None:
                    im = add_no_detection_area_for_cyclo(im)
                    outputs = predictor(im)
                    instances = outputs["instances"].to("cpu")
                    bboxes = instances.pred_boxes.tensor.cpu().numpy()
                    classes = instances.pred_classes.cpu().numpy()
                    left, right = assign_left_right(im, bboxes, classes)

        if img_type == "air":
            img_path = img_path_and_position_list[0][0]
            str_pts = img_path_and_position_list[0][1]
            angle = find_angle_to_y(str_pts)
            outputs = predictor(img_path)
            instances = outputs["instances"].to("cpu")
            if len(instances) > 2:
                instances = remove_unparked_cars_for_air(instances)

            bboxes = instances.pred_boxes.tensor.cpu().numpy()
            classes = instances.pred_classes.cpu().numpy()
            left, right = assign_left_right(im, bboxes, classes)

            #rotate image back to get the underlaying cooridnates for each bounding box
            left = (rotate_image_and_bboxes(img_path, angle, left), left[1])
            right = (rotate_image_and_bboxes(img_path, angle, right), right[1])

            #check which bboxes overlay with the current iteration window
            left = [(bbox, pred_class) for bbox, pred_class in left if calculate_iou(bbox, iteration_poly) >= 0.5]
            right = [(bbox, pred_class) for bbox, pred_class in right if calculate_iou(bbox, iteration_poly) >= 0.5]

        # add [-1] if no cars were detected 
        # if len(left) == 0:
        #     if iteration_number in predictions.keys():
        #         predictions[iteration_number]['left'].append([-1])
        #     else:
        #         predictions[iteration_number]['left'][-1]
        # else: 
        #     if iteration_number in predictions.keys():
        #         predictions[iteration_number]['left'].append(left)
        #     else:
        #         predictions[iteration_number]['left'][left]

        # if len(right) == 0:
        #     if iteration_number in predictions.keys():
        #         predictions[iteration_number]['right'].append([-1])
        #     else:
        #         predictions[iteration_number]['right'][-1]
        # else:
        #     if iteration_number in predictions.keys():
        #         predictions[iteration_number]['right'].append(right)
        #     else:
        #         predictions[iteration_number]['right'][right]
        
        if iteration_number in predictions.keys():
            if len(left) == 0:
                predictions[iteration_number]['left'].append([-1])
            else:
                predictions[iteration_number]['left'].append(left)

            if len(right) == 0:
                predictions[iteration_number]['right'].append([-1])
            else:
                predictions[iteration_number]['right'].append(right)
        else:
            predictions[iteration_number] = {
                'left': [[-1]] if len(left) == 0 else [left],
                'right': [[-1]] if len(right) == 0 else [right]
            }
        
    print(predictions)
                    
    parking_dict =  calculate_parking(predictions, img_type)

    print(parking_dict)      
        # return parking_dict


   #     continue
        # Create a Matplotlib figure and axis
        # poly = Polygon(poly)
        # x, y = poly.exterior.xy
        # fig, ax = plt.subplots()
        # ax.plot(x, y)
        # ax.plot(rec_lat, rec_lon, "ro")
        # plt.show()

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