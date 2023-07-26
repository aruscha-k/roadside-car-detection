from PIL import Image
import rasterio
import rasterio.mask
from rasterio.transform import Affine
import cv2

import numpy as np
import folium
import math 
from shapely import geometry
from matplotlib import pyplot as plt
from matplotlib import patches

import PATH_CONFIGS as PATHS
from helpers_geometry import find_angle_to_x, calculate_start_end_pt

                # lat, #lon
                #316823.5441658454 5688228.192294073
test_str_start = (51.3158290612, 12.3714331051)


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
# bbox has to be a closed shape!
# return True if successfull, else False
def cut_out_shape(bbox, out_tif, in_tif):

    poly = geometry.Polygon(bbox)
    with rasterio.open(in_tif) as src:
        try:
            out_image, out_transform = rasterio.mask.mask(src, [poly], crop=True)
            out_meta = src.meta
        except ValueError as e:
            print(e)
            return False

    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})

    with rasterio.open(out_tif, "w", **out_meta) as dest:
        dest.write(out_image)
    return True


# calculate lon, lat coordinates from pixel coordinates
# PARAMS:
#  img_path: path to the GEOTIFF
#  x,y : pixel values to get lon, lat values for
# RETURNS:
#  lon, lat values
def get_coordinates_from_px(img_path, x, y):
    with rasterio.open(img_path) as src:
        data = src.read()
        # Get the geotransform parameters
        transform = src.transform
        # Apply the geotransform to get the geospatial coordinates from pixel values (row = y, columns = x)
        lon, lat = transform * (x, y)

    return lon, lat

    
def crop_and_rotate_geotiff(input_file, output_file, bbox, rotation_angle):
    was_success = True
    # Open the input GeoTIFF
    with rasterio.open(input_file) as src:
        # Define the geometry and transform for the cropping operation
        poly = geometry.Polygon(bbox)
        transform = src.transform

        # Perform the crop; check for value error. can occur, when Streets overlap two districts
        try:
            cropped, out_transform = rasterio.mask.mask(src, [poly], crop=True)
        except ValueError:
            print("[!] Input shapes do not overlap raster.")
            was_success = False
            return was_success

         # Save the cropped GeoTIFF (Optional)
        cropped_meta = src.meta.copy()
        cropped_meta.update({"driver": "GTiff",
                             "height": cropped.shape[1],
                             "width": cropped.shape[2],
                             "transform": out_transform})

        # Specify the output file for the cropped image
        cropped_output_file = PATHS.AIR_TEMP_CROPPED_FOLDER_PATH + output_file

        with rasterio.open(cropped_output_file, "w", **cropped_meta) as cropped_dest:
            cropped_dest.write(cropped)

        # Rotate the cropped image by the specified angle
        # Convert the cropped image to a PIL Image object
        cropped_image = Image.fromarray(cropped.transpose(1, 2, 0)) 

        # Rotate the cropped image by the specified angle
        rotated_image = rotate_with_matrix(cropped_image, rotation_angle)
        #rotated_image = rotate_img(cropped_image, rotation_angle)

        # Convert the rotated image back to a numpy array
        rotated_image = np.array(rotated_image).transpose(2, 0, 1)


        # Update the transformation matrix to include rotation
        rotation_transform = Affine.rotation(rotation_angle)
        updated_transform = rotation_transform * out_transform

        # Update the metadata for the rotated GeoTIFF
        out_meta = src.meta.copy()
        out_meta.update({"driver": "GTiff",
                         "height": rotated_image.shape[1],
                         "width": rotated_image.shape[2],
                         "transform": updated_transform})

        rotated_output_file = PATHS.AIR_CROPPED_ROTATED_FOLDER_PATH + output_file
        # Save the rotated GeoTIFF
        with rasterio.open(rotated_output_file, "w", **out_meta) as dest:
            dest.write(rotated_image)

        return was_success


# TODO: old - delete?
# rotate the image for training with neural network, so that all images have 90degrees rotation from x axis (anticloclwise)
# save to new file
# def rotate_img(image, angle):
#     print(f"rotation angle: {angle}")
#     #expand 1 is used to keep the image from beeing cropped when rotated >90
#     rotated_img = image.rotate(angle=angle, expand=1)

#     #rotate_img.save(out_tif_folder + file_name)    
#     return rotated_img


# calculate rotation matrix by using center and an angle in degrees; 
# PARAMS:
#  image: the to be rotated image as PIL image
#  angle_degrees: the rotation angle in degrees
# RETURNS;
#  rotated_image: the rotated image as numpy array
def rotate_with_matrix(image, angle_degrees):
    image = np.array(image)
    # Get the height and width of the cropped image
    height, width = image.shape[:2]
    center = (width / 2, height / 2)
    
    # Get the rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
    # Perform the rotation using warpAffine
    rotated_image = cv2.warpAffine(image, rotation_matrix, (width, height))

    if len(rotated_image.shape) == 2:
        rotated_image = cv2.cvtColor(rotated_image, cv2.COLOR_GRAY2RGB)
    
    return rotated_image



# ---------- helper methods for debugging ------------------ #
def plot_order(coords,bboxes):

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


# debugging method to plot the iteration poly and the points on a geotif
def draw_on_geotiff(geotiff_path, pts, iter_poly):
    pts, classes = map(list, zip(*pts))
    # Open the GeoTIFF file using rasterio
    with rasterio.open(geotiff_path) as dataset:
    
        # Read the data and the corresponding geographic information
        data = dataset.read(1)  # Assuming it's a single-band raster (change index if needed)
        transform = dataset.transform


        # Print the boundaries
        # Get the corner coordinates in lat/lon
        # lon_min, lat_min = transform * (0, 0)
        # lon_max, lat_max = transform * (dataset.width, dataset.height)
        # print("Min Latitude:", lat_min)
        # print("Max Latitude:", lat_max)
        # print("Min Longitude:", lon_min)
        # print("Max Longitude:", lon_max)

        # Plot the GeoTIFF data
        plt.imshow(data, extent=[transform[2], transform[2] + transform[0] * dataset.width,
                                 transform[5] + transform[4] * dataset.height, transform[5]], cmap='viridis')
        plt.colorbar()
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title('GeoTIFF with Points')

        # Plot the points on the same plot as the GeoTIFF
        lon, lat = zip(*pts)  # Assuming 'pts' is a list of (longitude, latitude) tuples
        plt.scatter(lon, lat, color='red', s=5)
        polyx, polyy = zip(*iter_poly)
        plt.scatter(polyx, polyy, color="blue", s=8)
        plt.show()



# ---------- end helper methods for debugging ------------------ #


#if __name__ == "__main__":
