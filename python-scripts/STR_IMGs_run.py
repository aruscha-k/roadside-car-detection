
from helpers_geometry import find_angle_to_x, find_angle_to_y, get_y_intercept, calculate_slope, calculate_start_end_pt
from helpers_coordiantes import convert_coords, sort_coords, calulate_distance_of_two_coords
from street_imgs_api_calls import list_nearest_recordings, get_recording_id, render_by_ID
import street_imgs_config as CONF
import path_configs as PATH
import math
import operator
import pickle
import os



def save_recording_IDs_for_street(segment_rec_dict, segment_id: int, rec_IDs: dict):
    segment_rec_dict[segment_id] = rec_IDs
    return segment_rec_dict


def save_recoding_IDs_to_file(segment_rec_dict:dict, file_path: str):
    with open(file_path, 'wb') as f:
        pickle.dump(segment_rec_dict, f)


# find length of adjacent to move pt along x+length_adjacent and with this new x value calculate y by using line equation
def shift_pt_along_street(origin_pt, x_angle, shift_length, slope, y_intercept):
    length_adjacent = (math.cos(x_angle) * shift_length)
    shifted_x = origin_pt[0] + length_adjacent
    shifted_y = (slope * shifted_x) + y_intercept
    return (shifted_x, shifted_y)


def get_street_properties(street_coords):
    converted_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in street_coords]
    str_start, str_end = calculate_start_end_pt(converted_coords)
    y_angle = find_angle_to_y([str_start, str_end])
    slope_origin = calculate_slope([str_start, str_end])

    return str_start, str_end, y_angle, slope_origin


def get_nearest_recordings_for_streep_pts(str_start: tuple, str_end:tuple, shift_length:int, slope_origin:float):
    print(f"[i] Getting nearest recordings for street route")
    x_angle = find_angle_to_x([str_start, str_end])
    b = get_y_intercept(str_start, slope_origin)

    nearest_recordings_response = list_nearest_recordings(CONF.cyclo_srs, str_start[0], str_start[1], {}, False)
    #print(nearest_recordings_response.text)
    first_nearest_rec_ID, start_rec_time = get_recording_id(nearest_recordings_response, index=0)
    # ! points are now shifted corresponding to the nearest recording position, not the start point of the street from data
    # _, x_start, y_start = render_by_ID(CONF.cyclo_srs, nearest_rec_ID, {}, False)
    print(f"start point: {str_start[0], str_start[1]}, recording id:  {first_nearest_rec_ID} - time: {start_rec_time}")
    x_shifted, y_shifted = shift_pt_along_street((str_start[0], str_start[1]), x_angle, shift_length, slope_origin, b)
    
    rec_IDs = dict()
    rec_IDs[first_nearest_rec_ID] = {'street_point': (str_start[0], str_start[1]), 'recording_point': ()}

    if slope_origin > 0:
        op = operator.lt
    if slope_origin < 0:
        op = operator.gt

    while op(y_shifted, str_end[1]):
        recording_index = 0
        nearest_recordings = list_nearest_recordings(CONF.cyclo_srs, x_shifted, y_shifted, {}, False)
        nearest_rec_ID, rec_time = get_recording_id(nearest_recordings, recording_index)

        t_delta = abs(((rec_time - start_rec_time).total_seconds()/60))
        while t_delta > 2:
            recording_index += 1
            
            nearest_rec_ID, rec_time = get_recording_id(nearest_recordings, recording_index)
            #TODO: was passiert, wenn durchlaufen ohne ergebnis???
            # if nearest_rec_ID == "":
            #     break
            
            t_delta = abs(((rec_time - start_rec_time).total_seconds()/60))
            
        # if nearest_rec_ID == "":
        #     return rec_IDs
        
        print(f"point: {x_shifted,y_shifted}, recording id:  {nearest_rec_ID} - time: {rec_time}")
        
        if nearest_rec_ID not in rec_IDs.keys():
            rec_IDs[nearest_rec_ID] = {'street_point': (x_shifted, y_shifted), 'recording_point': ()}
            
        x_shifted, y_shifted = shift_pt_along_street((x_shifted, y_shifted), x_angle, shift_length, slope_origin, b)
        start_rec_time = rec_time
 
    return rec_IDs


def get_image_IDs_from_cyclomedia(segment_id:any, rec_IDs:dict, slope_origin:float, y_angle:float, max_distance:int):
    print(f"[i] Getting image IDs from cyclo")

    # for the cyclomedia api the y_angle gives the deviation from north direction. for streets with falling slope
    # the y_angle is measured "on the other side" therefore it is not represention the deivation from north without adding 90
        
    if slope_origin < 0:
            y_angle = (90-math.degrees(y_angle)) + 90
    elif slope_origin > 0:
        y_angle = math.degrees(y_angle)

    max_dist_rec_IDs = []
    for idx, (rec_id, values) in enumerate(rec_IDs.items()):
        print(idx, rec_id)
        
        
        #direction 90/-90 would be on the right/left side of the car
        params = {'yaw': str(y_angle), 'hfov': '80'}
        response, recording_lat, recording_lon = render_by_ID(CONF.cyclo_srs, rec_id, params, False)
        values['recording_point'] = (recording_lat, recording_lon)

        # calc distance between streeet and recording point, if too large, cyclomedia didnt drive through the street
        distance = calulate_distance_of_two_coords(values['recording_point'], values['street_point'])

        if distance > max_distance:
            print("[!] MAX DIST not saving image")
            max_dist_rec_IDs.append(rec_id)
            continue    

        else:
            if response.status_code == 200:
                if idx < 10:
                    idx = "0" + str(idx)

                with open(PATH.cyclomedia_imgs + str(segment_id)+ "_" + str(idx) +  "__" + str(rec_id) + ".jpg", 'wb') as file:
                    file.write(response.content)
            
            else:
                print(f"[!] BAD STATUSCODE: for image with id: {rec_id}")

    #update rec_IDs dict. if no image was saves this deteles all keys from dict and returns None
    for rec_id in max_dist_rec_IDs:
        rec_IDs.pop(rec_id)

    return rec_IDs

# ---- load to DB ----
def check_for_existing(segment_id, cursor):
    result = cursor.execute("""
        SELECT EXISTS(select 1 FROM cyclomedia WHERE segment_id=%s)""",(segment_id,)
        )
    print(result)
    return result




if __name__ == "__main__":

    segments_recordings_pkl_file = PATH.testset + "segment_rec_ids.pkl"
    segments_file = PATH.testset + "testset_segments_df.pkl"


    # segment data from Leipzig as pandas DF
    with open(segments_file, 'rb') as f:
        segments_df = pickle.load(f)
        print(f"segments has {len(segments_df)} items")

    #open recording IDs of segments dict
    if os.path.exists(segments_recordings_pkl_file):
        with open(segments_recordings_pkl_file, 'rb') as f:
            segments_rec_dict = pickle.load(f)
            print(f"dict has {len(segments_rec_dict)} items")
    else:
        segments_rec_dict = dict()
    

    for idx, row in segments_df.iterrows():
        if idx %2 == 0 :
            save_recoding_IDs_to_file(segments_rec_dict, segments_recordings_pkl_file)

        coords = row['coords']
        segment_id = row['object_id']
        if segment_id in segments_rec_dict.keys():
            continue
        
        # if not segment_id == 282335:
        #     continue

        # if more than two coordinates, street has a bend => 
        # partition the segment further and extract every two pairs of coordinate
        if len(coords) > 2:
            print(f"[i] more than 2 coords: {segment_id}")
 
            converted_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in coords]
            str_start, str_end = calculate_start_end_pt(converted_coords)
            sorted_coords = sort_coords(converted_coords, str_start)
            
            shift_length = 3
            segmentation_counter = 1
     
            for i in range(0,len(sorted_coords)):
                if segmentation_counter < 10:
                    new_segment_id = str(segment_id) + "_" + "0" + str(segmentation_counter)
                else:
                    new_segment_id = str(segment_id) + "_" + str(segmentation_counter)
        
                try:
                    temp_coords = [sorted_coords[i], sorted_coords[i+1]]
                    print(f"segmentation counter: {segmentation_counter}, coords: {temp_coords}")
                    y_angle = find_angle_to_y(temp_coords)
                    slope_origin = calculate_slope(temp_coords)

                    if new_segment_id not in segments_rec_dict.keys():
                        rec_IDs = get_nearest_recordings_for_streep_pts(sorted_coords[i], sorted_coords[i+1], shift_length, slope_origin)
                        
                    elif segments_rec_dict[new_segment_id] == None:
                        continue
                    else:
                        rec_IDs = segments_rec_dict[new_segment_id]
                  
                    rec_IDs = get_image_IDs_from_cyclomedia(new_segment_id, rec_IDs, slope_origin, y_angle, 9)
                    segment_rec_dict = save_recording_IDs_for_street(segments_rec_dict, new_segment_id, rec_IDs)
               
                    segmentation_counter += 1

                except IndexError:
                    break    
        else:
 
            str_start, str_end, y_angle, slope_origin = get_street_properties(coords)
    
            shift_length = 5
            print(segment_id, str_start, str_end)

            if not segment_id in segments_rec_dict.keys():
                rec_IDs = get_nearest_recordings_for_streep_pts(str_start, str_end, shift_length, slope_origin)
            elif segments_rec_dict[segment_id] == None:
                continue
            else:
                rec_IDs = segments_rec_dict[segment_id]
            rec_IDs = get_image_IDs_from_cyclomedia(segment_id, rec_IDs, slope_origin, y_angle, 9)
            segment_rec_dict = save_recording_IDs_for_street(segments_rec_dict, segment_id, rec_IDs)
     
        # break







#https://atlas.cyclomedia.com/PanoramaRendering/Render/WE4IK5SE/?apiKey=2_4lO_8ZuXEBuXY5m7oVWzE1KX41mvcd-PQZ2vElan85eLY9CPsdCLstCvYRWrQ5&srsName=epsg:55567837&direction=0&hfov=80
#test_rec_IDs = ['WE4IK5OM', 'WE4IK5SO', 'WE4IK5SN', 'WE4IK5SM', 'WE4IK5SL', 'WE4IK5SK', 'WE4IK5SJ', 'WE4IK5SI', 'WE4IK5SH', 'WE4IK5SG', 'WE4IK5SF', 'WE4IK5SE', 'WE4IK5SD', 'WE4IK5SC', 'WE4IK5SB', 'WE4IK5SA', 'WE4IK5S9', 'WE4IK5S8', 'WE4IK5S7', 'WE4IK5S6', 'WE4IK5S5', 'WE4MDYHX', 'WE4IK5N8']