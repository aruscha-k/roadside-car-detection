import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import xml.etree.ElementTree as ET
from datetime import datetime

import STR_IMGs_config as CONF

global global_base_url
global_base_url = 'https://atlas.cyclomedia.com/PanoramaRendering/'


# API request to get a list of nearest locations for a specific GPS coordinate
# output list is ordered according to the distance to the given address location
def list_nearest_recordings(srs, lat, lon, params, print_url):
    auth = (CONF.cyclo_user_aruscha, CONF.cyclo_pwd_aruscha)

    request_url = global_base_url + 'ListByLocation2D/' + srs + '/' + str(lat) + '/' + str(lon) + '?apiKey=' + CONF.cyclo_api_key + "&IncludeHistoricRecordings=false"

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

# API request to render a certain image by ID
# PARAMS:
# srs_name: !! put epsg: before the number
# recording_id: the recording ID to render the image of
def render_by_ID(srs_name, recording_id, params, print_url):
    auth = (CONF.cyclo_user_aruscha, CONF.cyclo_pwd_aruscha)
    request_url = global_base_url + 'Render/' + recording_id + '/?apiKey=' + CONF.cyclo_api_key + '&srsName=epsg:' + srs_name

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


# read metadata to get the position where the picture was taken from
# PARAMS:
# response: the response of a cyclomedia render_by_ID api call returning an image for a gps position
# RETURNS:
# recording_lat: latitude of camera position
# recording_lon: longitude of camera position
def extract_recording_location_from_meta(response):
    header_meta = response.headers
    # print(header_meta)
    recording_lat = float(header_meta['RecordingLocation-X'])
    recording_lon = float(header_meta['RecordingLocation-Y'])
    return recording_lat, recording_lon


# read metadata to get the position where the picture was taken from
# PARAMS:
# response: the response of a cyclomedia api call returning an image for a gps position
# RETURNS:
# recording_lat: latitude of camera position
# recording_lon: longitude of camera position
def extract_recording_location_from_meta(response):
    header_meta = response.headers
    # print(header_meta)
    recording_lat = float(header_meta['RecordingLocation-X'])
    recording_lon = float(header_meta['RecordingLocation-Y'])
    return recording_lat, recording_lon


# return the i-th element of all nearest recordings
# PARAMS:
# recordings_response: API response for list nearest recordings
# RETURNS:
# first_rec_id: the first recording_ID in the list
def get_recording_id(recordings_response, index):
    recordings_xml = ET.fromstring(recordings_response.text)
    try:
        first_elem = recordings_xml[index]
    except IndexError:
        return "", ""
    first_rec_id = first_elem.attrib['recording-id']
    time = datetime.strptime(first_elem.attrib['recording-date'], '%Y-%m-%dT%H:%M:%S.%fZ')

    return first_rec_id, time


# return the all nearest recording IDs
# PARAMS:
# recordings_response: API response for list nearest recordings
# RETURNS:
# rec_id_list: list of recording_IDs
def get_all_recording_ids(recordings_response):
    recordings_xml = ET.fromstring(recordings_response.text)
    rec_id_list = []
    for elem in recordings_xml:
        rec_id = elem.attrib['recording-id']
        rec_id_list.append(rec_id)
    return rec_id_list