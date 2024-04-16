import os

from PATH_CONFIGS import LOG_FILES


def log(execution_file, img_type, logstart, logtime, message: str):
    """ function to log if something didnt work

    Args:
        img_type (str): air / cyclo
        logstart (python time): start time of run
        logtime (python time): time of error
        message (str): message specified by user
    """
    if img_type:
        log_file_name = str(logstart) + "__" + str(execution_file) + "__" + str(img_type) + ".txt"
    else:
        log_file_name = str(logstart) + "__" + str(execution_file) + ".txt"

    log_file = os.path.join(LOG_FILES, log_file_name)
    if os.path.exists(log_file):
        with open(log_file, 'a') as lfile:
            lfile.write(logtime.strftime('%Y-%m-%d %H:%M:%S')  + ' ' + message + '\n')
    else:
        with open(log_file, 'w') as lfile:
            lfile.write(logtime.strftime('%Y-%m-%d %H:%M:%S')  + ' ' + message +  '\n')