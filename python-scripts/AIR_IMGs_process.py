import rasterio
import rasterio.mask
import cv2

import numpy as np
import folium
from shapely.geometry import Point, Polygon


def load_tiff(geotiff_path):
    """load a geotif

    Args:
        geotiff_path (string): filepath

    Returns:
        rgba_image: np array of image
        transform: the matrix of the geotif with information to transform px <-> coordinates
    """
    
    with rasterio.open(geotiff_path) as dataset:
        transform = dataset.transform
        meta = dataset.meta

        red_band = dataset.read(1)
        green_band = dataset.read(2)
        blue_band = dataset.read(3)
        alpha = dataset.read(4)
        rgba_image = np.dstack((blue_band, green_band, red_band, alpha))
        
    return rgba_image, transform, meta


def get_perspective_transform(image, corners):
    """ for an image / its corner points get the transformation matrix the new width and height

    Args:
        image (tiff image): 
        corners (list): of points of street segment in ordner for transform

    Returns:
        matrix: for perspective transform (to transform pts etc)
        widh, height: new width height for image
    """
    top_l, top_r, bottom_r, bottom_l = corners

    width_A = np.sqrt(((bottom_r[0] - bottom_l[0]) ** 2) + ((bottom_r[1] - bottom_l[1]) ** 2))
    width_B = np.sqrt(((top_r[0] - top_l[0]) ** 2) + ((top_r[1] - top_l[1]) ** 2))
    width = max(int(width_A), int(width_B))

    height_A = np.sqrt(((top_r[0] - bottom_r[0]) ** 2) + ((top_r[1] - bottom_r[1]) ** 2))
    height_B = np.sqrt(((top_l[0] - bottom_l[0]) ** 2) + ((top_l[1] - bottom_l[1]) ** 2))
    height = max(int(height_A), int(height_B))

    dimensions = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    
    corners = np.array(corners, dtype="float32")
    matrix = cv2.getPerspectiveTransform(np.array(corners, dtype="float32"), dimensions) # dimensions = dst

    return matrix, width, height


def sort_corners_for_transform(bbox):
    """ sort the corners of the bounding box of the geotif so that they are in the right order for perspective transform
        transform needs clockwise alignment of corners, starting in top left 

    Args:
        bbox (list): of points of street segment, bbox = [start_left, end_left, end_right, start_right]

    Returns:
        list: ordered points for perspective transform
    """
    top_l, top_r, bottom_r, bottom_l = bbox[1], bbox[2], bbox[3], bbox[0]
    return (top_l, top_r, bottom_r, bottom_l)


def transform_coordinates_to_pixel(coordinates, matrix):
    """ for geotif transform the coordinate values to px values

    Args:
        coordinates (list): list of tuples of coordiante point
        matrix (transformation matrix): of geotif

    Returns:
        list: of points in px
    """
    pixel_coordinates = [rasterio.transform.rowcol(matrix, coord[0], coord[1]) for coord in coordinates]
    return [[point[1], point[0]] for point in pixel_coordinates]


def transform_points(points, matrix):
    """ transform any point that lies within an image wit hthe same matrix as the one the images was transformed with

    Args:
        points (tuple): points to transform
        matrix (array): matrix to transform the points with

    Returns:
        tuple: transformed points
    """
    points = np.array(points, dtype="float32")
    transformed_points = cv2.perspectiveTransform(points.reshape(-1, 1, 2), matrix)
    return transformed_points


def transform_geotif_to_north(in_tif, out_file, out_file_type, bbox):
    """ transforms input geotif so that it "points towards north" and writes the image to disk

    Args:
        in_tif (string): filepath of cropped out street segment from district geotif
        out_file (string): filepath for output image save without file typ
        out_file_type (string): filetype for out_file - can be ".tif" or ".jpg"
        bbox (_type_): the bbox of the street segment, with points ordered like [start_left, end_left, end_right, start_right]

    Returns:
        transform_matrix: matrix of the perspective transform
        tiff_matrix: matrix of the geotif pixel to coordinates transform
    """
    img, tiff_matrix, meta = load_tiff(in_tif)
    pixel_bbox = transform_coordinates_to_pixel(bbox, tiff_matrix)
    corners = sort_corners_for_transform(pixel_bbox)
    transform_matrix, w, h = get_perspective_transform(img, corners)
    transformed_image = cv2.warpPerspective(img, transform_matrix, (w, h))
    
    if out_file_type == ".tif":
        save_transformed_tiff(transformed_image, out_file, meta)

    elif out_file_type == ".jpg":
        cv2.imwrite(out_file, transformed_image)

    return transform_matrix, tiff_matrix


def save_transformed_tiff(opencv_image, out_file, meta):
    """ take a numpy image array and save it as tiff

    Args:
        opencv_image (np array): image
        out_file (string): output tif filepath
        meta (?): meta information of tif like transform etc [!!!!!!] THIS WILL BE WRONG SINCE IT WAS NOT TRANSFORMED
    """
    out_meta = meta.copy()
    img = cv2.cvtColor(opencv_image.copy(), cv2.COLOR_RGB2BGRA)
    out_meta.update({"driver": "GTiff",
                    "height": img .shape[0],
                    "width": img .shape[1],
                    "count": img .shape[2]})

    with rasterio.open(out_file, "w", **out_meta) as dest:
        data = np.moveaxis(img, -1, 0)
        dest.write(data)


def cut_out_shape(bbox, out_tif, in_tif):
    """ method to cut out the calculated shape from the GEOTIF and saves the cutout img as file

    Args:
        bbox (list): of bbox to cut out street segment; bbox has to be a closed shape
        out_tif (string): filepath
        in_tif (string): filepath

    Returns:
        bool: return True, if cut out was successful, else False
    """
    poly = Polygon(bbox)
    with rasterio.open(in_tif) as src:
        try:
            out_image, out_transform = rasterio.mask.mask(src, [poly], crop=True)
            out_meta = src.meta
        except ValueError as e:
            print(e)
            return False, e

    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})

    with rasterio.open(out_tif, "w", **out_meta) as dest:
        dest.write(out_image)
    return True, "success"


def is_car_within_polygon(car_bbox, polygon_coordinates):
    """ for air images calculate if a car (bbox) lies within the iteration poly

    Args:
        car_bbox (np array): detection bbox of 1 car
        polygon_coordinates (list): of iteration poly points

    Returns:
        bools: True if point in polygon, else False
    """
    car_bbox = car_bbox.tolist()
    width = car_bbox[2] - car_bbox[0]
    height = car_bbox[3] - car_bbox[1] 
    midpoint_bbox = (car_bbox[0] + (width / 2), car_bbox[1] + (height / 2))
    point = Point(midpoint_bbox)
    polygon = Polygon(polygon_coordinates)
    #print(f"point lies within: {polygon.contains(point)} ")
    
    return polygon.contains(point)



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
def draw_on_geotiff(plot_title, geotiff_path, pts, iter_poly):
    from matplotlib import pyplot as plt

    if len(pts) != 0:
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

        # Plot the GeoTIFF data
        plt.imshow(data, extent=[transform[2], transform[2] + transform[0] * dataset.width,
                                 transform[5] + transform[4] * dataset.height, transform[5]], cmap='viridis')
        plt.colorbar()
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title(plot_title)

        if len(pts) != 0:
            # Plot the points on the same plot as the GeoTIFF
            lon, lat = zip(*pts)  # Assuming 'pts' is a list of (longitude, latitude) tuples
            plt.scatter(lon, lat, color='red', s=5)
            polyx, polyy = zip(*iter_poly)
            plt.scatter(polyx, polyy, color="blue", s=8)
            plt.show()
        else:
            "[!] No detections to plot!"


# ---------- end helper methods for debugging ------------------ #


#if __name__ == "__main__":
