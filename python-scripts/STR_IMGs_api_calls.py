import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import xml.etree.ElementTree as ET
from datetime import datetime
import json

import STR_IMGs_config as CONF

global global_base_url_panorama
global global_base_url_atlas

# for rendering images
global_base_url_panorama = 'https://atlas.cyclomedia.com/PanoramaRendering/'

# for getting metadata
global_base_url_atlas = 'https://atlasapi.cyclomedia.com/recording/wfs?service=WFS&version=1.1.0&request=GetFeature'


def list_nearest_recordings(srs, lat, lon, params, print_url):
    """ API request to get a list of nearest locations for a specific GPS coordinate, the output list is ordered according to the distance to the given address location
        example URL: https://atlas.cyclomedia.com/PanoramaRendering/ListByLocation2D/55567837/316822.5120000001/5688438.680999999?apiKey=2_4lO_8ZuXEBuXY5m7oVWzE1KX41mvcd-PQZ2vElan85eLY9CPsdCLstCvYRWrQ5
    Args:
        srs (int): epsg number
        lat (float): lat position for api call
        lon (float): lon position for api call
        params (dict): parameters for the API call, can be found in cyclomedia API documentation
        print_url (bool): if the final URL should be printed

    Returns:
        http response: response of the api call
    """
    auth = (CONF.cyclo_user_aruscha, CONF.cyclo_pwd_aruscha)

    request_url = global_base_url_panorama + 'ListByLocation2D/' + srs + '/' + str(lat) + '/' + str(lon) + '?apiKey=' + CONF.cyclo_api_key + "&IncludeHistoricRecordings=false"

    if params:
        for key, value in params.items():
            request_url = request_url + '&' + key + '=' + value

    if print_url:
        print(request_url)

    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)

    response = http.get(url=request_url, auth=auth)
    return response


def render_by_ID(srs_name, recording_id, params, print_url):
    """ API request to render a certain image by ID

    Args:
        srs_name (int): the epsg number !! put epsg: before the number in url
        recording_id (_type_): the recording ID to render the image of
        params (dict): parameters for the API call, can be found in cyclomedia API documentation
        print_url (bool): if the final URL should be printed

    Returns:
        response: of the API request
        float: the lat, lon of the recording point image
    """
    auth = (CONF.cyclo_user_aruscha, CONF.cyclo_pwd_aruscha)
    request_url = global_base_url_panorama + 'Render/' + recording_id + '/?apiKey=' + CONF.cyclo_api_key + '&srsName=epsg:' + srs_name

    if params:
        for key, value in params.items():
            request_url = request_url + '&' + key + '=' + value

    if print_url:
        print(request_url)

    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)

    response = http.get(url=request_url, auth=auth)
    recording_lat, recording_lon = extract_recording_location_from_meta(response)

    return response, recording_lat, recording_lon 


def extract_recording_location_from_meta(response):
    """read metadata to get the position where the picture was taken from
    Args:
        response (http response): the response of a cyclomedia render_by_ID api call returning an image for a gps position

    Returns:
        float: latitude, longitude of camera position
    """
    header_meta = response.headers
    if response.status_code == 200:
   
        recording_lat = float(header_meta['RecordingLocation-X'])
        recording_lon = float(header_meta['RecordingLocation-Y'])

        return recording_lat, recording_lon
    else:
        return 0,0


def get_recording_id(recordings_response, index):
    """ return the i-th element of all nearest recordings

    Args:
        recordings_response (http response): API response for list nearest recordings
        index (int): the index of the list to get the recording for

    Returns:
        string: the i-th recording_ID element in the list
        datetime: the time of the recording
    """
    if recordings_response.status_code == 404:
        return "", ""
    
    recordings_xml = ET.fromstring(recordings_response.text)
    try:
        recording_elem = recordings_xml[index]
    except IndexError:
        return "", ""
    first_rec_id = recording_elem.attrib['recording-id']

    try:
        rec_date = datetime.strptime(recording_elem.attrib['recording-date'], '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        new_time = (recording_elem.attrib['recording-date'].replace("Z", "")) + ".00" + "Z"
        rec_date = datetime.strptime(new_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        
    return first_rec_id, rec_date


def get_viewing_direction(srs_name, recording_id):
    """ for a specific recording ID this Call returns the metadata including the viewing direction from the WFS Service of cyclomedia

    Args:
        srs_name (string): srs for the cyclomeda api 
        recording_id (string): recording id of the image to get metadata for
    Returns:
        recorder_direction (float): the direction in which the car was "looking" when taking the recordingimage
    """
    auth = (CONF.cyclo_user_aruscha, CONF.cyclo_pwd_aruscha)

    param_url = f"&srsname=EPSG:{srs_name}&typename=atlas:Recording&featureid={recording_id}&outputFormat=application/json"
    request_url = global_base_url_atlas + param_url

    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)

    response = http.get(url=request_url, auth=auth)
    data_json = json.loads(response.text)

    try:
        recorder_direction = data_json['features'][0]['properties']['recorderDirection']
    except KeyError:
        print("[!] No viewing direction")

    return float(recorder_direction, round = 2)


def get_all_recording_ids(recordings_response):
    """return the all nearest recording IDs

    Args:
        recordings_response (http response): API response for list nearest recordings

    Returns:
        list: list of recording_IDs
    """
    recordings_xml = ET.fromstring(recordings_response.text)
    rec_id_list = []
    for elem in recordings_xml:
        rec_id = elem.attrib['recording-id']
        rec_id_list.append(rec_id)
    return rec_id_list