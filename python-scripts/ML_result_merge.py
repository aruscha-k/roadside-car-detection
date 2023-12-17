from DB_helpers import open_connection
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER
from collections import Counter
import psycopg2

import os


global parking_segment_result_table
global parking_iteration_result_table
global parking_cyclo_fetch_table
global parking_air_fetch_table


def populate_db_result_dict(db_results, img_type, result_dict):
    """ HELPER method to create the parking result dict for both DB calls (cyclo and air); is beeing appended from empty to air DB call to cyclo DB call

    Args:
        db_results (list): results from the DB call
        img_type (str): cyclo or air
        result_dict (dict): dict at its current state 

    Returns:
        dict: key = dict (key segmentation_number): (dict (key iteration number) (dict (key parking side) list))
        {<segmentation_number>: {iteration_number: {'left': [{'cyclo': ('parallel', percentage)}, {'air': ('kein Auto', 100.0)}], 'right': [{'cyclo': ('parallel', 100.0)}]}, iteration_number+1: {...}
    """
    for item in db_results:
        segmentation_number = item[0]
        iteration_number = item[1]
        parking_side = item[2]
        parking_value = item[3]
        parking_percentage = item[4]

        if segmentation_number not in result_dict:
            result_dict[segmentation_number] = {}

        if iteration_number not in result_dict[segmentation_number]:
            result_dict[segmentation_number][iteration_number] = {}

        if parking_side not in result_dict[segmentation_number][iteration_number]:
            result_dict[segmentation_number][iteration_number][parking_side] = []

        result_dict[segmentation_number][iteration_number][parking_side].append({img_type: (parking_value, parking_percentage)})

    return result_dict


def fetch_parking_results_per_segment(cursor, segment_id:int, img_type: str):
    """ HELPER method to fetch ML results for each iteration within one segment

    Args:
        cursor (DB cursor): 
        segment_id (int): segment_id to fetch results for
        img_type (string): if only onetype of images should be used pass either air / cyclo, if both should be used pass empty string

    Returns:
        dict: key = dict (key segmentation_number): (dict (key iteration number) (dict (key parking side) list))
        {<segmentation_number>: {iteration_number: {'left': [{'cyclo': ('parallel', percentage)}, {'air': ('kein Auto', 100.0)}], 'right': [{'cyclo': ('parallel', 100.0)}]}, iteration_number+1: {...}
    """
    cyclo, air = [], []
    result_dict = dict()

    if img_type == "" or img_type == "cyclo":
        cursor.execute("""SELECT segmentation_number, iteration_number, parking_side, value, percentage FROM {} WHERE segment_id = %s ORDER BY segmentation_number ASC""".format(parking_cyclo_fetch_table), (segment_id, ))
        cyclo = cursor.fetchall()
        #print("cyclo result:", cyclo)

    if img_type == "" or img_type == "air":
        cursor.execute("""SELECT segmentation_number, iteration_number, parking_side, value, percentage FROM {} WHERE segment_id = %s ORDER BY segmentation_number ASC""".format(parking_air_fetch_table), (segment_id, ))
        air = cursor.fetchall()
        #print("air result ", air)

    # check that both tables have the same number of entries for all iterations
    if len(air) != len(cyclo):
        print("[!] Not same amount of entries in cyclo and air in segmet id: Len air:", len(air), "len cyclo:", len(cyclo))
       # if img_type != "":
            #TODO LOG

    result_dict = {}
    if len(air) != 0:
        result_dict = populate_db_result_dict(air, "air", result_dict)
    if len(cyclo) != 0:
        result_dict = populate_db_result_dict(cyclo, "cyclo", result_dict)

    return result_dict


def apply_weights(parking_value, percentage):
    """ some classes should weigh less in calculation, for no car subtract 30 percent

    Args:
        parking_value (str): the parking value class
        percentage (float): the percentage for that class

    Returns:
        str, float: class with new percentage
    """
    if parking_value == "kein Auto":
        percentage -= 30

    return parking_value, percentage


def compare_iteration_result_per_image_type(results_per_side):
    """ compare for one iteration step the two values of cyclo and air

    Args:
        results_per_side (list): of two dicts => [{'air': ('kein Auto', 100.0)}, {'cyclo': ('parallel', 100.0)}]

    Returns:
        str, float: parking_value, parking_percentage
    """
   
    if len(results_per_side) == 2:
        for dict_item in results_per_side:
            
            if "cyclo" in dict_item.keys():
                cyclo_parking_value = dict_item.get("cyclo")[0]
                cyclo_parking_percentage = dict_item.get("cyclo")[1]
                cyclo_parking_value, cyclo_parking_percentage = apply_weights(cyclo_parking_value, cyclo_parking_percentage)
           
            if "air" in dict_item.keys():
                air_parking_value = dict_item.get("air")[0]
                air_parking_percentage = dict_item.get("air")[1]
                air_parking_value, air_parking_percentage = apply_weights(air_parking_value, air_parking_percentage)

        # if both have same parking_value; air has seperate values for senkrecht/diagonal => more precise
        if air_parking_value in cyclo_parking_value:
        # if cyclo_parking_value == air_parking_value:
            avg_percentage = (cyclo_parking_percentage + air_parking_percentage)/2
            return air_parking_value, avg_percentage
        else:
            # if cyclo has higher percentage
            if cyclo_parking_percentage > air_parking_percentage:
                return cyclo_parking_value, cyclo_parking_percentage
            
            # if air has higher percentage
            elif air_parking_percentage > cyclo_parking_percentage:
                return air_parking_value, air_parking_percentage
            # if both have same percentage TODO
            elif air_parking_percentage == cyclo_parking_percentage:
                return "TIE: " + air_parking_value + "," + cyclo_parking_value, air_parking_percentage

    # if there is only one result from one image type, return it after applying weights
    if len(results_per_side) == 1:
      
        parking_value = list(results_per_side[0].values())[0][0]
        parking_percentage = list(results_per_side[0].values())[0][1]
        parking_value, parking_percentage = apply_weights(parking_value, parking_percentage)

        return parking_value, parking_percentage


def calculate_average_percentage(result_list, parking_value):
    """ HELPER for a specific parking value, calculate the average percentage for all values

    Args:
        result_list (list): of tuples (value, percentage)
        parking_value (str): the class value for parking

    Returns:
        float: average percentage
    """
    percentage_list = [percentage for value, percentage in result_list if value == parking_value]
    avg_percentage = sum(percentage_list) / len(percentage_list)
    # print("avg_percentage", round(avg_percentage, 1))
    return round(avg_percentage, 1)


def write_parking_result_to_DB(con, segment_id, segmentation_number, iteration_number, parking_side, parking_value, parking_percentage):
    cursor = con.cursor()
    try:
        # write segmentation to DB, if no iteration number was specified
        if iteration_number == "":
            cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s, %s)""".format(parking_segment_result_table), (segment_id, segmentation_number, parking_side, parking_value, parking_percentage, ))
        else: #write iteration result to DB
            cursor.execute("""INSERT INTO {} VALUES (%s, %s, %s, %s, %s, %s)""".format(parking_iteration_result_table), (segment_id, segmentation_number, iteration_number, parking_side, parking_value, parking_percentage, ))
        
    except psycopg2.errors.UniqueViolation:
        con.rollback()
    con.commit()


def compare_iteration_values(db_con, segment_id, segmentation_number, segmentation_result_dict, parking_side):
    """ compare all iterations parking values for one parking side for both image types
        iterate iterations and compare parking side for both image types, save results to a temp list 
        use temp list to find the most common value which will be the result for the whole segment
        method implements the ability to check for same count of parking values (called duplicates)

    Args:
        segmentation_result_dict (dict): all parking results for segmentation
        parking_side (str): left / right

    Returns:
        str, float: parking_value, parking_percentage for the SEGMENT on the specified parking side
    """
    iteration_comparison_results = []

    # compare per iteration the "two images" and write to DB
    for iteration_number, values in segmentation_result_dict.items():
        # print("in", parking_side, values[parking_side])
        parking_value, parking_percentage = compare_iteration_result_per_image_type(values[parking_side])
        write_parking_result_to_DB(db_con, segment_id, segmentation_number, iteration_number, parking_side, parking_value, parking_percentage)
        iteration_comparison_results.append((parking_value, parking_percentage))
    # print("results of comparison:", iteration_comparison_results)


    # merge all iteration results to one big result for the whole segment and write to DB
    counter = Counter([item[0] for item in iteration_comparison_results])
    most_common_parking_value, most_common_count = counter.most_common(1)[0]# show the most common item (1) (=tuple) and choose it ([0])
    next_most_common_count = counter.most_common(2)[1][1] if len(counter) > 1 else 0
    has_duplicates = most_common_count == next_most_common_count #if two items with same probability

    if not has_duplicates:
        avg_percentage = calculate_average_percentage(iteration_comparison_results, most_common_parking_value)
        write_parking_result_to_DB(db_con, segment_id, segmentation_number, iteration_number="", parking_side=parking_side, parking_value=most_common_parking_value, parking_percentage=avg_percentage)
    else:
        # if there are parking values with the same number of counts, choose the one with the biggest percentage:
        # to do so get the values from result list and calculate the average percentage of the duplicate items, choose the item with the highest percentage
        next_most_common_parking_value, next_most_common_count = counter.most_common(2)[1] #show the two most common items (2) (=tuples) and choose the second one of them ([1])
        most_common_avg = calculate_average_percentage(iteration_comparison_results, most_common_parking_value)
        next_most_common_avg = calculate_average_percentage(iteration_comparison_results, next_most_common_parking_value)

        if most_common_avg > next_most_common_avg:
            write_parking_result_to_DB(db_con, segment_id, segmentation_number, iteration_number="", parking_side=parking_side, parking_value=most_common_parking_value, parking_percentage=most_common_avg)
            
        elif next_most_common_avg > most_common_avg:
            write_parking_result_to_DB(db_con, segment_id, segmentation_number, iteration_number="", parking_side=parking_side, parking_value=next_most_common_parking_value, parking_percentage=next_most_common_avg)
        
        # if they have same avg percentage value, check if one of them is kein auto and if yes return the other
        elif most_common_avg == next_most_common_avg:
            if most_common_parking_value == "kein Auto":
                write_parking_result_to_DB(db_con, segment_id, segmentation_number, iteration_number="", parking_side=parking_side, parking_value=next_most_common_parking_value, parking_percentage=next_most_common_avg)

            elif next_most_common_parking_value == "kein Auto":
                write_parking_result_to_DB(db_con, segment_id, segmentation_number, iteration_number="", parking_side=parking_side, parking_value=most_common_parking_value, parking_percentage=most_common_avg)
            else:
                #TODO if both have same avg percentage and none of them is "kein auto" which to chose?!
                write_parking_result_to_DB(db_con, segment_id, segmentation_number, iteration_number="", parking_side=parking_side, parking_value=most_common_parking_value, parking_percentage=most_common_avg)



def run(db_config, db_user, suburb_list, img_type):
    """ Method to merge parking results from cyclomedia and air images for a specific suburb (list):
        iterate all suburbs -> get all segment ids per suburb -> 

    Args:
        db_config (str): path to DB information
        db_user (str): path to DB user to log in 
        suburb_list (list): of tuples with ot_name, ot_nr

    """
     
    with open_connection(db_config, db_user) as con:
        cursor = con.cursor()

        if suburb_list == []:
             # get ortsteile and their number codes
            cursor.execute("""SELECT ot_name FROM ortsteile""")
            suburb_list = cursor.fetchall()

        for ot_name in suburb_list:

            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            segment_ids = [item[0] for item in cursor.fetchall()]

            for idx, segment_id in enumerate(segment_ids):
                print("----segment id: ",segment_id, " - Number", idx+1, "of ", len(segment_ids))

                segment_parking_results = fetch_parking_results_per_segment(cursor, segment_id, img_type)
                
                if segment_parking_results != {}:

                    # compare parking results per segmentation_number (of segment) first left side, then right
                    for segmentation_number in segment_parking_results.keys():
                        compare_iteration_values(con, segment_id, segmentation_number, segment_parking_results[segmentation_number], 'left')
                        compare_iteration_values(con, segment_id, segmentation_number, segment_parking_results[segmentation_number], 'right')
                else:
                    print("[!] RESULT---------> no result, empty fetch")



if __name__ == "__main__":
    
    parking_air_fetch_table = 'parking_air'
    parking_cyclo_fetch_table = 'parking_cyclomedia_newmethod'
    parking_segment_result_table = 'parking_segment_air'
    parking_iteration_result_table = 'parking_iteration_air'

    db_config = os.path.join(RES_FOLDER_PATH, DB_CONFIG_FILE_NAME)
    run(db_config, DB_USER, ['Südvorstadt'], img_type="air")