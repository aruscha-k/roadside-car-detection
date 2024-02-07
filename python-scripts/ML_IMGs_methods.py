import numpy as np
import cv2
import os
import torch

from collections import Counter
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer

from PATH_CONFIGS import RES_FOLDER_PATH, CYCLO_DETECTION_MODEL, AIR_DETECTION_MODEL, CYCLO_IMG_FOLDER_PATH, AIR_CROPPED_ROTATED_FOLDER_PATH, AIR_CROPPED_ITERATION_FOLDER_PATH, DEMO_AIR_DETECTION_FOLDER_PATH, DEMO_CYCLO_DETECTION_FOLDER_PATH
from helpers_coordiantes import is_point_within_polygon
from AIR_IMGs_helper_methods import transform_geotif_to_north


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

# Nov trained net with 3 classes: {'parallel': 0, 'senkrecht': 1, 'diagonal': 2}
def load_air_predictor():
    air_cfg = get_cfg()
    if not torch.cuda.is_available():
        print('not using gpu acceleration')
        air_cfg.MODEL.DEVICE = 'cpu'
    air_cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    air_cfg.MODEL.WEIGHTS = os.path.join(RES_FOLDER_PATH, AIR_DETECTION_MODEL)
    air_cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3
    air_cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.90
    predictor = DefaultPredictor(air_cfg)
    return predictor


def load_cyclo_predictor():
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    cfg.DATASETS.TRAIN = ("test_set",)
    cfg.DATASETS.TEST = ()
    cfg.DATALOADER.NUM_WORKERS = 2
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml")  #
    cfg.SOLVER.IMS_PER_BATCH = 2
    cfg.SOLVER.BASE_LR = 0.0025  #
    cfg.SOLVER.MAX_ITER = 1500    
    cfg.SOLVER.STEPS = []      
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 1500  
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2 
    cfg.MODEL.DEVICE = 'cpu'
    cfg.MODEL.WEIGHTS = os.path.join(RES_FOLDER_PATH, CYCLO_DETECTION_MODEL)  #
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.90   
    predictor = DefaultPredictor(cfg)
    return predictor



def transform_air_img(img_file_name, img_bbox, out_file_type):
    """ method to run all methods to transform a tif file towards the north direction with perspective trasnform

    Args:
        img_file_name (string): file path of in image, ! without extension
        img_bbox (list): of corner points of street segment
        out_file_type (string): ".jpg" / ".tif"

    Returns:
        transform_matrix (matrix) transform matrix of perspective transform
        tiff_matrix (matrix): transform matrix of tif (coordinates <> px)
        out_file (string): filepath of output file
    """
    
    in_tif = AIR_CROPPED_ITERATION_FOLDER_PATH + img_file_name + ".tif"
    if not os.path.exists(in_tif):
        print("[!] ERROR when tranforming air img: path not found for in_tif")
        # TODO LOG
        return
    out_file = AIR_CROPPED_ROTATED_FOLDER_PATH + img_file_name + out_file_type
    
    transform_matrix, tiff_matrix = transform_geotif_to_north(in_tif= in_tif, out_file= out_file, out_file_type = out_file_type, bbox = img_bbox)
    return transform_matrix, tiff_matrix, out_file


def add_no_detection_area_for_cyclo(im):
    """ method to add a black triangle in the middle of the image, kind of the viewing range of the driving car to rule out driving cars in front of the car

    Args:
        im (numpy array): cv2 image

    Returns:
        im (numpy array): cv2 image with black triangle
    """
    im_width = im.shape[1]
    im_height = im.shape[0]
    
    mid_line = (int(im_width/2), int(im_height/2)-50)
    mid_line_y = mid_line[1]
    mid_line_x = mid_line[0]
    mid_point = (mid_line_x, int(im_height))
    
    # car sight area
    left = (int(im_width/3)-50, mid_line_y)
    right = ((2*int(im_width/3)+50), mid_line_y)
    points = np.array([[left, mid_point, right]])
    im = cv2.fillPoly(im, pts=[points], color=(0, 0, 0))
    return im


def add_no_detection_area_for_air(im):

    percentage = 0.18
    
    im_width = im.shape[1]
    im_height = im.shape[0]
    midpoint_x = int(im_width/2)

    left_boundary_x = int((midpoint_x+10) - percentage * (im_width/2))
    right_boundary_x = int((midpoint_x-10) + percentage * (im_width/2))

    poly = [[left_boundary_x, im_height], [left_boundary_x, 0], [right_boundary_x, 0], [right_boundary_x, im_height]]
    #bbox_centers = instances.pred_boxes.get_centers().cpu().numpy()
    #outliers = [pt for pt in bbox_centers if is_point_within_polygon(pt, poly)]
    
    polygon_vertices = np.array([poly], dtype=np.int32)
    cv2.fillPoly(im, pts=polygon_vertices, color=(0, 0, 0))

    return im


def assign_left_right(im, boxes, classes):
    """ function uses the midpoint of image (x axis) and assign bboxes to left or right side depending on their positions in regard to the midpoint

    Args:
        im (np array): open cv image
        boxes (list of np array): list of all predicted boxes in image
        classes (list): list of all predicted classes (index corresponding to boxes)

    Returns:
        list, list: lists of (box, class) tuple is on which parking side
    """
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


def calculate_parking(predictions, img_type):
    """ for all the predicted classes, calculate for each iteration, which predicted class was most often and calculate its percentage of all items in the predictions

    Args:
        predictions (dict): key = iteration number, value = dict: key = parking side, value = all predictions (list) e.g.  {iteration_number: {'left': [0, 0, 0, 0, -1], 'right': [0, 1, 0, 0]}
        img_type (string): "air" / "cyclo"

    Returns:
        dict: key = iteration_number, 2nd key = parking side value = (parking value, percentage) e.g. parking_dict[iteration_number]['right'] = (class_dict[class_right_most_common], round(right_percentage,2))
    """
    parking_dict = dict()

    if img_type == "cyclo":
        class_dict = {0: 'parallel', 1: 'diagonal/senkrecht', -1: 'kein Auto', -2: 'no image'}
    elif img_type == "air":
        class_dict = {0: 'parallel', 1: 'senkrecht', 2: 'diagonal', -1: 'kein Auto', -2: 'no image'}

    for iteration_number in predictions.keys():
        # print(predictions[iteration_number])
        parking_dict[iteration_number] = {}

        if len(predictions[iteration_number]) == 0: # if no predictions were found in an iteration, choose class no car
            parking_dict[iteration_number]['left'] = (class_dict[-1], 100.00)
            parking_dict[iteration_number]['right'] = (class_dict[-1], 100.00)
            continue

        if predictions[iteration_number]['left'] == [-2]: # if on one of the sides is "error code" its on both sides
            parking_dict[iteration_number]['left'] = (class_dict[-2], 0)
            parking_dict[iteration_number]['right'] = (class_dict[-2], 0)
            continue

        # METHOD TO ADD ONLY THE BEST DETECTION PERCENTAGE
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

        #TODO case not explicitly handled, that there are two classes occuring the same number of times.

    return parking_dict


def run_detection(img_filename_and_position_list, ot_name, img_type, iter_information_dict, filter_unparked_cars):
    """ run method: for one street segment, use all images to detect parking situation on

    Args:
        img_filename_and_position_list (list): containing the filename of image (without path) and a position information for cyclo: (imgpath, (recording_lat, recording_lon)), for air: (imgpath, segment_bbox)
        img_type (string): "air" / "cyclo"
        iter_information_dict (dict): key = iteration_number, value = iteration_poly (bbox)

    Returns:
        dict: key = iteration_number, 2nd key = parking side value = (parking value, percentage) e.g. parking_dict[iteration_number]['right'] = (class_dict[class_right_most_common], round(right_percentage,2))
    """
    print("[i] Running parking detection")

    if img_type == "air":
        predictor = load_air_predictor()
    elif img_type == "cyclo":
        predictor = load_cyclo_predictor()
    else:
        print("[!] invalid img type - cannot load predictor")
    predictions = dict()    
    # go through each iteration
    for idx, (iteration_number, iteration_poly) in enumerate(iter_information_dict.items()):
        #print("iter number and poly", iteration_number, iteration_poly)
        predictions[iteration_number] = {}
        
        if img_type == "cyclo":
            # find all recordings of the segment, that lie within the current iteration box
            iteration_record_id_list = [img_filename for img_filename, (recording_lat, recording_lon) in img_filename_and_position_list if is_point_within_polygon((recording_lat, recording_lon), iteration_poly)]
            iteration_record_id_list = list(set(iteration_record_id_list)) #TODO CHECK FOR DUPLICATES
            
            if iteration_record_id_list == []: #if there is no image add -2 for both sides
                predictions[iteration_number] = {"left": [-2], "right": [-2]}
                continue
            else:
                # for each image make predictions, assign left and right side and save (bounding box, class) to each left and right
                for img_filename in iteration_record_id_list:
                    folder_path = os.path.join(CYCLO_IMG_FOLDER_PATH, ot_name + "/")
                    img = cv2.imread(os.path.join(folder_path, img_filename))
                    if img is not None:
                        if filter_unparked_cars:
                            img = add_no_detection_area_for_cyclo(img)
                        outputs = predictor(img)
                        instances = outputs["instances"].to("cpu")
                        bboxes = instances.pred_boxes.tensor.cpu().numpy()
                        classes = instances.pred_classes.cpu().numpy()
                        im_left, im_right = assign_left_right(img, bboxes, classes) #list of tuples (box, class)
                        #print("im left: ", im_left, "im_right", im_right)
                        predictions[iteration_number] = assign_predictions_to_side_and_iteration(side = 'left', predicted_classes_for_side = [item[1] for item in im_left],  predictions = predictions[iteration_number])
                        predictions[iteration_number] = assign_predictions_to_side_and_iteration(side = 'right', predicted_classes_for_side = [item[1] for item in im_right], predictions = predictions[iteration_number])

                        demo_img_folder = os.path.join(DEMO_CYCLO_DETECTION_FOLDER_PATH, ot_name + "/")
                        if not os.path.exists(demo_img_folder):
                            os.mkdir(demo_img_folder)
                        visualize_and_save_prediction_img(img, instances, "cyclo", show_img = False, save_img = True, pred_img_filepath = demo_img_folder + img_filename) #for scads demo, save the image file with predictions
                #print("predictions", predictions)
        if img_type == "air":
            img_file_name = img_filename_and_position_list[idx][0]
            if img_file_name == "": #if there is no image add -2 for both sides
                predictions[iteration_number] = {"left": [-2], "right": [-2]}
                continue
            else:
                img_file_name = img_file_name[:-4]
                bbox = img_filename_and_position_list[idx][1]
                
                transform_matrix, tiff_matrix, out_img_path = transform_air_img(img_file_name, bbox, out_file_type=".tif")
                cropped_rotated_img = cv2.imread(out_img_path)
                
                if cropped_rotated_img is None:
                    print("[!] ERROR: CV2 could not open img file - RETURN empty dict")
                    #TODO LOG
                    return {}
                if filter_unparked_cars:
                    cropped_rotated_img = add_no_detection_area_for_air(cropped_rotated_img)
                outputs = predictor(cropped_rotated_img)
                instances = outputs["instances"].to("cpu")
        
                # if filter_unparked_cars and (len(instances) > 3):
                #     instances = remove_unparked_cars_for_air(instances)
                    

                bboxes = instances.pred_boxes.tensor.cpu().numpy()
                classes = instances.pred_classes.cpu().numpy()

                demo_img_folder = os.path.join(DEMO_AIR_DETECTION_FOLDER_PATH, ot_name + "/")
                if not os.path.exists(demo_img_folder):
                    os.mkdir(demo_img_folder)
                
                visualize_and_save_prediction_img(cropped_rotated_img, instances, "air", show_img = False, save_img = True, pred_img_filepath = demo_img_folder + img_file_name + ".jpg") #for scads demo, save the image file with predictions
                #find_best_line_through_boxes(cropped_rotated_img, instances)

                all_left, all_right = assign_left_right(cropped_rotated_img, bboxes, classes)
                #draw_assigned_classes_in_air_imgs(left, right, transformed_poly_points, out_img_path)
                predictions[iteration_number] = assign_predictions_to_side_and_iteration(side = "left", predicted_classes_for_side = [item[1] for item in all_left], predictions = predictions[iteration_number])
                predictions[iteration_number] = assign_predictions_to_side_and_iteration(side = "right", predicted_classes_for_side = [item[1] for item in all_right], predictions = predictions[iteration_number])
                                
    # for all predictions, calculate the parking
    parking_dict =  calculate_parking(predictions, img_type)
    #print(parking_dict)

    return parking_dict


def assign_predictions_to_side_and_iteration(side, predicted_classes_for_side, predictions):
    """ method to add prediction per image to side and iteration per iteration

    Args:
        side (string): parkign side "left" / "right"
        predicted_classes_for_side (list): list of predicted classes
        predictions (dict): dict of collected predictions per iteration => predictions[iteration_number]

    Returns:
        dict: extended dict with the new info from this iteration
    """
    
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


# -------- for debug and demo ----------------
# visualize prediction for 1 image
def visualize_and_save_prediction_img(cv2_image, instances, img_type, show_img, save_img, pred_img_filepath):
    
    if img_type == "air":
        #metadata = {"thing_classes": ['p', 'd/s']}
        metadata = {"thing_classes": ['p', 's', 'd']}
       
    elif img_type == "cyclo":
        metadata = {"thing_classes": ['parallel', 'diagonal/senkrecht']}

    v = Visualizer(cv2_image[:, :, ::-1], metadata=metadata, scale=1)
    out = v.draw_instance_predictions(instances)
    if show_img:
        cv2.imshow('Prediction', out.get_image()[:, :, ::-1])
        cv2.waitKey(0)
    if save_img:
        cv2.imwrite(pred_img_filepath, out.get_image()[:, :, ::-1])



def draw_assigned_classes_in_air_imgs(left, right, poly, img_path):
    from PIL import Image
    from matplotlib import pyplot as plt 

    image = Image.open(img_path)

    # Create a figure and axis
    fig, ax = plt.subplots()

    # Display the image
    ax.imshow(image)

    for pt in poly:
        ax.plot(pt[0], pt[1], "ro")

    for rect, pclass in right: 
        rect = rect.tolist()
        
        width = rect[2] - rect[0]
        height = rect[3] - rect[1] 
        midpoint_bbox = (rect[0] + (width / 2), rect[1] + (height / 2))
        ax.plot(midpoint_bbox[0], midpoint_bbox[1], color='green', marker='o')

    for rect, pclass in left: 
        rect = rect.tolist()
        width = rect[2] - rect[0]
        height = rect[3] - rect[1] 
        midpoint_bbox = (rect[0] + (width / 2), rect[1] + (height / 2))
        ax.plot(midpoint_bbox[0], midpoint_bbox[1], color='yellow', marker='o')

    # Show the plot
    plt.show()



# if __name__ == "__main__":
#     visualize_prediction()