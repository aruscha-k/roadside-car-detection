from DB_helpers import open_connection
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER
from collections import Counter

import os


def populate_db_result_dict(db_results, img_type, result_dict):

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


# method to fetch ML results for each iteration for one segment
# PARAMS:
#  cursor: DB cursor
#  segment_id: segment_id to fetch results for
# RETURN:
#  result_dict (dict) {<segmentation_number>: {iteration_number: {'left': [{'cyclo': ('parallel', percentage)}, {'air': ('kein Auto', 100.0)}], 'right': [{'cyclo': ('parallel', 100.0)}]}, iteration_number+1: {...}
def fetch_results(cursor, segment_id:int):
    
    result_dict = dict()
    cursor.execute("""SELECT segmentation_number, iteration_number, parking, value, percentage FROM parking_cyclomedia WHERE segment_id = %s ORDER BY segmentation_number ASC""", (segment_id, ))
    cyclo = cursor.fetchall()

    cursor.execute("""SELECT segmentation_number, iteration_number, parking, value, percentage FROM parking_air WHERE segment_id = %s ORDER BY segmentation_number ASC""", (segment_id, ))
    air = cursor.fetchall()

    # check that both tables have the same number of entries for all iterations
    if len(air) != len(cyclo):
        print("[!] Not same amount of entries in cyclo and air in segmet id: Len air:", len(air), "len cyclo:", len(cyclo))
        #TODO LOG

    result_dict = {}
    if len(air) != 0:
        result_dict = populate_db_result_dict(air, "air", result_dict)
    if len(cyclo) != 0:
        result_dict = populate_db_result_dict(cyclo, "cyclo", result_dict)

    return result_dict


def apply_weights(parking_value, percentage):
    # WEIGH NO CAR DETECTIONS LESS; SUBTRACT 30 % FROM PERCENTAGE
    if parking_value == "kein Auto":
        percentage -= 30

    return parking_value, percentage


# RETURN
#  value, percentage of parking
def compare_iteration_result_per_image_type(results_per_side):

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

        # compare parking_values
        if cyclo_parking_value == air_parking_value:
            avg_percentage = (cyclo_parking_percentage + air_parking_percentage)/2
            return cyclo_parking_value, avg_percentage

        else:
            if cyclo_parking_percentage > air_parking_percentage:
                return cyclo_parking_value, cyclo_parking_percentage
            
            elif air_parking_percentage > cyclo_parking_percentage:
                return air_parking_value, air_parking_percentage

            
    # if there is only one result for one image type
    if len(results_per_side) == 1:
      
        parking_value = list(results_per_side[0].values())[0][0]
        parking_percentage = list(results_per_side[0].values())[0][1]
        parking_value, parking_percentage = apply_weights(parking_value, parking_percentage)

        return parking_value, parking_percentage



def calculate_average_percentage(result_list, parking_value):
    percentage_list = [percentage for value, percentage in result_list if value == parking_value]
    avg_percentage = sum(percentage_list) / len(percentage_list)
    # print("avg_percentage", round(avg_percentage, 1))
    return round(avg_percentage, 1)


def compare_iteration_values(segmentation_result_dict, parking_side):

    iteration_comparison_results = []
    # compare per iteration the "two images"
    for iteration_number, values in segmentation_result_dict.items():
        # print("in", parking_side, values[parking_side])
        parking_value, parking_percentage = compare_iteration_result_per_image_type(values[parking_side])
        iteration_comparison_results.append((parking_value, parking_percentage))

    # print("results of comparison:", iteration_comparison_results)

    # merge all iteration results to one big result for the whole segment
    counter = Counter([item[0] for item in iteration_comparison_results])

    most_common_parking_value, most_common_count = counter.most_common(1)[0]# show the most common item (1) (=tuple) and choose it ([0])
    next_most_common_count = counter.most_common(2)[1][1] if len(counter) > 1 else 0
    has_duplicates = most_common_count == next_most_common_count

    if not has_duplicates:
        avg_percentage = calculate_average_percentage(iteration_comparison_results, most_common_parking_value)
        return most_common_parking_value, avg_percentage
    else:
        # if there are values with the same number of counts, choose the one with the biggest percentage:
        # get the values from result list and calculate the average percentage of the duplicate items, choose the item with the highest percentage
        next_most_common_parking_value, next_most_common_count = counter.most_common(2)[1] #show the two most common items (2) (=tuples) and choose the second one of them ([1])
        most_common_avg = calculate_average_percentage(iteration_comparison_results, most_common_parking_value)
        next_most_common_avg = calculate_average_percentage(iteration_comparison_results, next_most_common_parking_value)

        if most_common_avg > next_most_common_avg:
            return most_common_parking_value, most_common_avg
        elif next_most_common_avg > most_common_avg:
            return next_most_common_parking_value, next_most_common_avg
        
        # if they have same avg percentage value, check if one of them is kein auto and if yes return the other
        elif most_common_avg == next_most_common_avg:
            if most_common_parking_value == "kein Auto":
                return next_most_common_parking_value, next_most_common_avg
            elif next_most_common_parking_value == "kein Auto":
                return most_common_parking_value, most_common_avg



def run(db_config, db_user, suburb_list):
    with open_connection(db_config, db_user) as con:
        cursor = con.cursor()

        for ot_name, ot_nr in suburb_list:

            cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
            segment_ids = [item[0] for item in cursor.fetchall()]

            for idx, segment_id in enumerate(segment_ids):
                print("----segment id: ",segment_id, " - Number", idx+1, "of ", len(segment_ids))

                merged_results = fetch_results(cursor, segment_id)
                if merged_results != {}:
                    for segmentation_number in merged_results.keys():
        
                        left_most_common_value, left_avg_percentage = compare_iteration_values(merged_results[segmentation_number], 'left')
                        cursor.execute("""INSERT INTO parking VALUES (%s, %s, %s, %s, %s)""", (segment_id, segmentation_number, "left", left_most_common_value, left_avg_percentage, ))

                        right_most_common_value, right_avg_percentage = compare_iteration_values(merged_results[segmentation_number], 'right')
                        cursor.execute("""INSERT INTO parking VALUES (%s, %s, %s, %s, %s)""", (segment_id, segmentation_number, "right", right_most_common_value, right_avg_percentage))
            
                        con.commit()

                    print("RESULT--------->", {'segment_id': segment_id, 'left': left_most_common_value, 'right': right_most_common_value})
                else:
                    print("[!] RESULT---------> no result, empty fetch")



# def suvo(db_config, DB_USER, suburb_list):

#     import pandas as pd
#     sides_df = pd.read_csv('/Users/aruscha/Desktop/segment_sides.csv')

#     with open_connection(db_config, DB_USER) as con:
#         cursor = con.cursor()

#         for ot_name, ot_nr in suburb_list:

#             cursor.execute("""SELECT id FROM segments WHERE ot_name = %s""", (ot_name, ))
#             segment_ids = [item[0] for item in cursor.fetchall()]

#             filtered_df = sides_df[sides_df['segment_id'].isin(segment_ids)]
#             filtered_df.to_csv('/Users/aruscha/Desktop/suedvo_segment_sides.csv')
            

if __name__ == "__main__":
    db_config = os.path.join(RES_FOLDER_PATH, DB_CONFIG_FILE_NAME)
    run(db_config, DB_USER, [("Südvorstadt", 40)])