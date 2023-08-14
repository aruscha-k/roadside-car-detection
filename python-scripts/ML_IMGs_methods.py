import numpy as np
import cv2
import os
import torch
from sklearn.cluster import KMeans
from collections import Counter
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg

from PATH_CONFIGS import RES_FOLDER_PATH, CYCLO_DETECTION_MODEL, AIR_DETECTION_MODEL, CYCLO_IMG_FOLDER_PATH, AIR_CROPPED_ROTATED_FOLDER_PATH, AIR_TEMP_CROPPED_FOLDER_PATH
from helpers_coordiantes import is_point_within_polygon
from AIR_IMGs_process import get_coordinates_from_px, get_rotation_angle_for_img, draw_on_geotiff

from matplotlib import pyplot as plt
from matplotlib import patches


# JONAS trained net
# def load_air_predictor():
    # air_cfg = get_cfg()
    # if not torch.cuda.is_available():
    #     print('not using gpu acceleration')
    #     air_cfg.MODEL.DEVICE = 'cpu'
    # air_cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    # air_cfg.MODEL.WEIGHTS = os.path.join(RES_FOLDER_PATH, AIR_DETECTION_MODEL)
    # air_cfg.MODEL.ROI_HEADS.NUM_CLASSES = 5
    # air_cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.90
    # predictor = DefaultPredictor(air_cfg)
    # return predictor


# July 23 trained net
def load_air_predictor():
    air_cfg = get_cfg()
    if not torch.cuda.is_available():
        print('not using gpu acceleration')
        air_cfg.MODEL.DEVICE = 'cpu'
    air_cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    air_cfg.MODEL.WEIGHTS = os.path.join(RES_FOLDER_PATH, AIR_DETECTION_MODEL)
    air_cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2
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


# takes the rotated image and recalculates the detected bounding boxes for the unrotated image
# PARAMS:
#  img_filename: the img_filename
#  angle_degrees: the rotation angle of the rotated image in degrees
#  boxes_and_classes: the detected boxes and corresponding detected class
# RETURNS:
#  box_center_and_class (list) of tuples ((boxcenter1, boxcenter2), class)
def rotate_image_and_boxes(img_filename, boxes_and_classes, angle_degrees):

    north_rotated_image = cv2.imread(os.path.join(AIR_CROPPED_ROTATED_FOLDER_PATH, img_filename))
    cropped_out_image = cv2.imread(os.path.join(AIR_TEMP_CROPPED_FOLDER_PATH, img_filename))
    height, width = cropped_out_image.shape[:2]
    center = (width / 2, height / 2)
    
    rotation_matrix = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
    # Apply rotation to the image
    rotated_image = cv2.warpAffine(north_rotated_image, rotation_matrix, (width, height))

    # Rotate bounding box coordinates
    rotated_boxes_and_classes = []
    box_center_and_class = []
    boxes_px = [] #for debugging  
    for box, pred_class in boxes_and_classes:

        upper_left_x, upper_left_y = box[0], box[1]
        lower_right_x, lower_right_y = box[2], box[3]
        #assign new:
        upper_right_x, upper_right_y = box[2], box[1]
        lower_left_x, lower_left_y = box[0], box[3]

       # Append 1 to the coordinates to convert them into homogeneous coordinates (x, y, 1)
        upper_left_homogeneous = np.array([upper_left_x, upper_left_y, 1])
        lower_right_homogeneous = np.array([lower_right_x, lower_right_y, 1])
        upper_right_homogeneous = np.array([upper_right_x, upper_right_y, 1])
        lower_left_homogeneous = np.array([lower_left_x, lower_left_y, 1])
        
        # Transform the points using the 2x3 rotation matrix
        upper_left_rotated = np.dot(rotation_matrix, upper_left_homogeneous)
        lower_right_rotated = np.dot(rotation_matrix, lower_right_homogeneous)
        upper_right_rotated = np.dot(rotation_matrix, upper_right_homogeneous)
        lower_left_rotated = np.dot(rotation_matrix, lower_left_homogeneous)

        # Append the transformed points to the rotated_boxes list (upper_left is now rotated and is in bottom right corner)
        rotated_boxes_and_classes.append(([(upper_left_rotated[0], upper_left_rotated[1]), (upper_right_rotated[0], upper_right_rotated[1]), (lower_right_rotated[0], lower_right_rotated[1]), (lower_left_rotated[0], lower_left_rotated[1])], pred_class))
        box_center = ((upper_left_rotated[0] + lower_right_rotated[0]) / 2, (upper_left_rotated[1] + lower_right_rotated[1]) / 2)
        boxes_px.append(box_center)

        
        # read the original geotif and extract the underlying coordinates from the pixel values
        center_lon, center_lat = get_coordinates_from_px(os.path.join(AIR_TEMP_CROPPED_FOLDER_PATH, img_filename), box_center[0], box_center[1])
        box_center_and_class.append(((center_lon, center_lat), pred_class))
    

    # -- FOR DEBUGGING --
    
    
    #print("Shape of second rotated image: ", rotated_image.shape)
    fig, ax = plt.subplots()
    im = ax.imshow(rotated_image)
    #for box, p_class in rotated_boxes:
    for pt in boxes_px:
        #rect = patches.Polygon(box, closed=True, edgecolor='r', linewidth=2)
        #ax.add_patch(rect)
        ax.plot(pt[0], pt[1], 'ro')
    plt.show()
    # -- END --
    print("box centers and classes: ", box_center_and_class)
    return box_center_and_class


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
    left, right = [], []
    if len(boxes) == 0:
        return left, right
    
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


# for all the predicted classes, calculate for each iteration, which predicted class was most often and calculate its percentage of all items in the predictions
# predictions = {iteration_number: {'left': [0, 0, 0, 0, -1], 'right': [0, 1, 0, 0]}
def calculate_parking(predictions, img_type):
   
    parking_dict = dict()

    if img_type == "cyclo":
        class_dict = {0: 'parallel', 1: 'diagonal/senkrecht', -1: 'kein Auto'}
    elif img_type == "air":
        class_dict = {0: 'parallel', 1: 'diagonal/senkrecht', -1: 'kein Auto'}

    for iteration_number in predictions.keys():
        print(predictions[iteration_number])
        parking_dict[iteration_number] = {}
        # if no predictions were found in an iteration
        if len(predictions[iteration_number]) == 0:
            parking_dict[iteration_number]['left'] = (class_dict[-1], 100.00)
            parking_dict[iteration_number]['right'] = (class_dict[-1], 100.00)
            continue

        #METHOD TO ADD ONLY THE BEST DETECTION PERCENTAGE
        # most_common(1) chooses only the first most common item
        left_counts = Counter(predictions[iteration_number]['left'])  # returns Counter object of Counter({class: count, ...})
        right_counts = Counter(predictions[iteration_number]['right'])

        counts_left_most_common = left_counts.most_common(1)[0][1]
        class_left_most_common = left_counts.most_common(1)[0][0]
        left_percentage = counts_left_most_common/len(predictions[iteration_number]['left'])*100
        parking_dict[iteration_number]['left'] = (class_dict[class_left_most_common], round(left_percentage,2))

        counts_right_most_common = right_counts.most_common(1)[0][1]
        class_right_most_common = right_counts.most_common(1)[0][0]
        right_percentage = counts_right_most_common / len(predictions[iteration_number]['right'])*100
        parking_dict[iteration_number]['right'] = (class_dict[class_right_most_common], round(right_percentage,2))


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


# PARAMS
# img_path_and_position_list = (imgpath, (recording_lat, recording_lon))
# img_type (string) "air"/"cyclo" depending on the input image
# iter_information_dict (dict) key = iteration_number, value = iteration_poly (bbox)
def run_detection(img_path_and_position_list, img_type, iter_information_dict):
    print("[i] Running parking detection")

    if img_type == "air":
        predictor = load_air_predictor()
    elif img_type == "cyclo":
        predictor = load_cyclo_predictor()
    else:
        print("[!] invalid img type - cannot load predictor")

    predictions = dict()

    # open segmented image and find detections. rotate image back and assign detection to the left and right side.
    if img_type == "air":
        img_file = img_path_and_position_list[0][0]
        str_pts = img_path_and_position_list[0][1]
        #print("Shape of cut out image from geotif: ", cv2.imread(os.path.join(AIR_TEMP_CROPPED_FOLDER_PATH, img_file)).shape)
        cropped_rotated_img = cv2.imread(os.path.join(AIR_CROPPED_ROTATED_FOLDER_PATH, img_file))
        angle_degrees = get_rotation_angle_for_img(str_pts=str_pts)
        outputs = predictor(cropped_rotated_img)
        instances = outputs["instances"].to("cpu")
        
        if len(instances) > 2:
            instances = remove_unparked_cars_for_air(instances)

        visualize_prediction(os.path.join(AIR_CROPPED_ROTATED_FOLDER_PATH, img_file), "air")
        bboxes = instances.pred_boxes.tensor.cpu().numpy()
        classes = instances.pred_classes.cpu().numpy()
        all_left, all_right = assign_left_right(cropped_rotated_img, bboxes, classes)
        right_rotated = rotate_image_and_boxes(img_file, all_right, -angle_degrees)
        left_rotated = rotate_image_and_boxes(img_file, all_left, -angle_degrees)

    for iteration_number, iteration_poly in iter_information_dict.items():
        #print("iter number and poly", iteration_number, iteration_poly)
        predictions[iteration_number] = {}
        
        if img_type == "cyclo":
            left, right = [], []
            # find the recordings that lie within the iteration box
            iteration_record_id_list = [img_file for img_file, (recording_lat, recording_lon) in img_path_and_position_list if is_point_within_polygon((recording_lat, recording_lon), iteration_poly)]

            # for each image make predictions, assign left and right side and save (bounding box, class) to each left and right
            for img_file in iteration_record_id_list:
                img = cv2.imread(os.path.join(CYCLO_IMG_FOLDER_PATH, img_file))
                if img is not None:
                    img = add_no_detection_area_for_cyclo(img)
                    outputs = predictor(img)
                    instances = outputs["instances"].to("cpu")
                    bboxes = instances.pred_boxes.tensor.cpu().numpy()
                    classes = instances.pred_classes.cpu().numpy()
                    im_left, im_right = assign_left_right(img, bboxes, classes) #list of tuples (box, class)
                    predictions[iteration_number] = assign_predictions_to_side_and_iteration(side = 'left', predicted_classes_for_side = [item[1] for item in im_left],  predictions = predictions[iteration_number])
                    predictions[iteration_number] = assign_predictions_to_side_and_iteration(side = 'right', predicted_classes_for_side = [item[1] for item in im_right], predictions = predictions[iteration_number])

        if img_type == "air":
            #check which detected bboxes => centerpoints lie within the current iteration window
            draw_on_geotiff("Right", os.path.join(AIR_TEMP_CROPPED_FOLDER_PATH, img_file), right_rotated, iteration_poly)
            print("right")
            right = [pred_class for center, pred_class in right_rotated if is_point_within_polygon(center, iteration_poly)]

            draw_on_geotiff("Left", os.path.join(AIR_TEMP_CROPPED_FOLDER_PATH, img_file), left_rotated, iteration_poly)
            print("left")
            left = [pred_class for center, pred_class in left_rotated if is_point_within_polygon(center, iteration_poly)]

            predictions[iteration_number] = assign_predictions_to_side_and_iteration(side = "left", predicted_classes_for_side = left, predictions = predictions[iteration_number])
            predictions[iteration_number] = assign_predictions_to_side_and_iteration(side = "right", predicted_classes_for_side = right, predictions = predictions[iteration_number])
                 

        # add side-assigned predictions classes to predictions dict; add [-1] if no cars were detected for a side/iteration window #TODO check if function assign_predictions_to_side_and_iteration workd for air then delete this
        # ONLY adds predicted class, not box
        # if 'left' in predictions[iteration_number].keys():
        #     if len(left) == 0:
        #         predictions[iteration_number]['left'].append(-1)
        #     else:
        #         predictions[iteration_number]['left'].append(left)
        # else: 
        # if len(left) == 0:
        #     predictions[iteration_number]['left'] = [-1]
        # else:
        #     predictions[iteration_number]['left'] = left
        # if 'right' in predictions[iteration_number].keys():
        #     if len(right) == 0:
        #         predictions[iteration_number]['right'].append(([], -1))
        #     else:
        #         predictions[iteration_number]['right'].append(right)
        # else:
        #     if len(right) == 0:
        #         predictions[iteration_number]['right'] = [([], -1)]
        #     else:
        #         predictions[iteration_number]['right'] = right
            
    # for all predictions, calculate the parking
    parking_dict =  calculate_parking(predictions, img_type)
    print("parking_dict:", parking_dict)      
    return parking_dict

# side = "left" / "right"
# predicted_classes_for_side (list of predicted classes)
# predictions = dict of collected predictions per iteration => predictions[iteration_number]
def assign_predictions_to_side_and_iteration(side, predicted_classes_for_side, predictions):
    
    if side in predictions.keys():
        if len(predicted_classes_for_side) == 0:
            predictions[side].extend([-1])
        else:
            predictions[side].extend(predicted_classes_for_side)
    else:
        if len(predicted_classes_for_side) == 0:
            predictions[side] = [-1]
        else: 
            predictions[side] = predicted_classes_for_side
    #print(predictions)
    return predictions

# -------- for debug only ----------------
# visualize prediction for 1 image
def visualize_prediction(filename, img_type):
    from detectron2.utils.visualizer import Visualizer

    if img_type == "air":
        predictor = load_air_predictor()
        metadata = {"thing_classes": ['parallel', 'diagonal/senkrecht']}
    elif img_type == "cyclo":
        predictor = load_cyclo_predictor()
        metadata = {"thing_classes": ['parallel', 'diagonal/senkrecht']}
    
    im = cv2.imread(filename)
    outputs = predictor(im)
    instances = outputs["instances"].to("cpu")
    
    v = Visualizer(im[:, :, ::-1], metadata=metadata, scale=0.5)
    out = v.draw_instance_predictions(instances)
    cv2.imshow('Prediction', out.get_image()[:, :, ::-1])
    cv2.waitKey(0)

# if __name__ == "__main__":
    

#     visualize_prediction()