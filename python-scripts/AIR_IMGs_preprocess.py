from PIL import Image
import rasterio
import rasterio.mask
from rasterio import Affine
import pickle
import folium
import math 
from shapely import geometry

import PATH_CONFIGS as PATHS
from helpers_geometry import calculate_slope, get_y_intercept, find_angle_to_x, calc_perpendicular, calc_interception_of_two_lines, calculate_start_end_pt
from helpers_coordiantes import convert_coords, sort_coords


                # lat, #lon
                #316823.5441658454 5688228.192294073
test_str_start = (51.3158290612, 12.3714331051)


# given two points andthe wanted width calculate two parallel lines and perpendiculars
# RETURNS:
# bouding_box (list) with points in order [upper_left, upper_right, lower_right, lower_left]
def calculate_bounding_box(str_pts, width):
   
    # slope and y intercept of original line, angle to x-axis of original line
    m_origin = calculate_slope(str_pts)
    b_origin = get_y_intercept(str_pts[0], m_origin) 
    x_angle = find_angle_to_x(str_pts)

    # calc perpendiculars for start point and endpoints
    m_perpendicular, b_perpend_start, b_perpend_end = calc_perpendicular(str_pts)

    # calc y intercept of parallel line: parallel line has slope of m_origin
    new_width = width/2 * math.sqrt((m_origin**2) + 1)
    b_parallel_below = (b_origin-new_width)
    b_parallel_above = (b_origin+new_width)

    print(f"original slope: {m_origin}, new width: {new_width}")

    if abs(math.degrees(x_angle)) <= 45:

        upper_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, m_origin, b_parallel_above)
        upper_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, m_origin, b_parallel_above)
        lower_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, m_origin, b_parallel_below)
        lower_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, m_origin, b_parallel_below)
    
    elif abs(math.degrees(x_angle)) >= 45:

        upper_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, m_origin, b_parallel_above)
        upper_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_end, m_origin, b_parallel_below)
        lower_right = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, m_origin, b_parallel_below)
        lower_left = calc_interception_of_two_lines(m_perpendicular, b_perpend_start, m_origin, b_parallel_above)

    bounding_box = [upper_left, upper_right, lower_right, lower_left]
    return bounding_box



# method calculates the rotation angle, the image has to be rotated with, 
# to contain an image that is leading in the direction of north
# PARAMS: str_pts (list) of 2 street points
# rotation_angle (float) angle in degrees
def get_rotation_angle_for_img(str_pts):
    x_angle = find_angle_to_x(str_pts)

    if abs(math.degrees(x_angle)) <= 45:
        rotation_angle = 90 - math.degrees(x_angle)
        if math.degrees(x_angle) < 0:
            rotation_angle = 90 + abs(math.degrees(x_angle))
    elif abs(math.degrees(x_angle)) > 45:
        rotation_angle = 90 - math.degrees(x_angle)
        if math.degrees(x_angle) < 0:
            rotation_angle = 90 + abs(math.degrees(x_angle))

    return rotation_angle


# method to cut out the calculated shape from the GEOTIF and saves the cutout img as file
# return True if successfull, else False
def cut_out_shape(bbox, out_tif, in_tif):

    poly = geometry.Polygon(bbox)
    with rasterio.open(in_tif) as src:
        try:
            out_image, out_transform = rasterio.mask.mask(src, [poly], crop=True)
            # check if the image contains only zeros
            if out_image[0].sum() == 0:
                #print('The cropped image contains only zeros')
                return False
            out_meta = src.meta
        except ValueError:
            #print('Error cropping image')
            return False

    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})
    print ('writing ' + out_tif)
    with rasterio.open(out_tif, "w", **out_meta) as dest:
        dest.write(out_image)
    return True


# rotate the image for training with neural network, so that all images have 90degrees rotation from x axis (anticloclwise)
# save to new file
def rotate_img_only(in_tif_folder, out_tif_folder, file_name, angle):
    
    print(f"rotation angle: {angle}")
    img = Image.open(in_tif_folder + file_name)
    #expand 1 is used to keep the image from beeing cropped when rotated >90
    rotate_img = img.rotate(angle=angle, expand=1)
    #rotate_img.show(out_tif)
    rotate_img.save(out_tif_folder + file_name)    


def rotate_img_and_coords(in_tif_folder, out_tif_folder, file_name, angle):
    # Open the geotiff file
    with rasterio.open(in_tif_folder + file_name) as src:
        # Read the image data and affine transform matrix
        data = src.read()
        transform = src.transform

        # Calculate the affine transform matrix for the rotated image
        cos_angle = math.cos(math.radians(angle))
        sin_angle = math.sin(math.radians(angle))
        rotation_matrix = Affine(cos_angle, sin_angle, 0, -sin_angle, cos_angle, 0)

        # Calculate the new affine transform matrix by combining the rotation matrix and the original transform
        new_transform = transform * rotation_matrix

        # Create a new geotiff file for the rotated image
        with rasterio.open(out_tif_folder + file_name, 'w', driver='GTiff',
                           width=data.shape[2], height=data.shape[1], count=data.shape[0],
                           dtype=data.dtype, transform=new_transform) as dst:
            # Write the rotated image data and metadata to the new file
            dst.write(data)


# ---------- helper methods for debugging ------------------ #
def plot_order(coords,bboxes):
    # this is using "EPSG:4326"
    center = [51.322523347273126, 12.375431206686596]
    map_leipzig = folium.Map(location=center, zoom_start=16)
    for idx, pt in enumerate(coords):
        folium.Marker(pt, popup=str(idx)).add_to(map_leipzig)
        try:
            folium.Polygon(bboxes[idx], color="green", weight= 2).add_to(map_leipzig)
        except IndexError:
            break
    map_leipzig.save('index.html')


def plot_line(str: list, bbox: list):
    center = [51.322523347273126, 12.375431206686596]
    map_leipzig = folium.Map(location=center, zoom_start=16)

    folium.PolyLine(str, weight=5).add_to(map_leipzig)
    # folium.Marker(str[0], popup="start").add_to(map_leipzig)
    # folium.Marker(str[1], popup="end").add_to(map_leipzig)
    folium.Polygon(bbox, color="green", weight= 2).add_to(map_leipzig)
    # folium.Marker(bbox[0], popup="upper left").add_to(map_leipzig)
    # folium.Marker(bbox[1], popup="upper right").add_to(map_leipzig)
    # folium.Marker(bbox[2], popup="lower right").add_to(map_leipzig)
    # folium.Marker(bbox[3], popup="lower left").add_to(map_leipzig)

    map_leipzig.save('index.html')

# ---------- end helper methods for debugging ------------------ #


if __name__ == "__main__":

    # the TIF-file to cut out from
    tif_file = PATHS.testset + "Südvorstadt_TDOP_2022_RGB_10cm.tif"

    # segment data from Leipzig as pandas DF
    with open(PATHS.testset + "testset_segments_df.pkl", 'rb') as f:
        segments_df = pickle.load(f)

    # folders to save IMGs in
    cropped_folder = PATHS.img_folder + 'cropped_imgs/'
    rotated_folder = PATHS.img_folder + 'cropped_rotated/'

#   #iterate city data and get image for each segment
    # leave out streets of category "W"
    for idx, row in segments_df.iterrows():

        street_width = 20
        if row['cat'] == "W":
            continue
       
        print("--------", idx, str(row['object_id']))
        coords = row['coords']

        # if more than two coordinates, street has a bend => 
        # partition the segment further and extract every two pairs of coordinate:
        # calc start and end point of the whole street and resort the coords
        if len(coords) > 2: 
            converted_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in coords]
            str_start, str_end = calculate_start_end_pt(converted_coords)
            sorted_coords = sort_coords(converted_coords, str_start)
            
            segmentation_counter = 1
            for i in range(0,len(sorted_coords)):
                
                try:
                    img_file_name = str(row['object_id']) + "_" + str(segmentation_counter) + ".tif"
                    temp_coords = [sorted_coords[i], sorted_coords[i+1]]
                    bbox = calculate_bounding_box(temp_coords, street_width)
                    rotation_angle = get_rotation_angle_for_img(temp_coords)
                    cut_out_success = cut_out_shape(bbox, cropped_folder + img_file_name, tif_file)
                    if cut_out_success:
                        rotate_img_only(cropped_folder, rotated_folder, img_file_name, rotation_angle)
                        segmentation_counter += 1
                except IndexError:
                    break
        else:
                            
            converted_coords = [convert_coords("EPSG:4326", "EPSG:25833", pt[0], pt[1]) for pt in coords]
            str_start, str_end = calculate_start_end_pt(converted_coords)
            bbox = calculate_bounding_box([str_start, str_end], street_width)
            rotation_angle = get_rotation_angle_for_img([str_start, str_end])
            cut_out_success = cut_out_shape(bbox, cropped_folder + str(row['object_id']) + ".tif", tif_file)
            if cut_out_success:
                rotate_img_only(cropped_folder, rotated_folder, str(row['object_id']) + ".tif", rotation_angle)
            
        # if idx == 1:
        #     break

