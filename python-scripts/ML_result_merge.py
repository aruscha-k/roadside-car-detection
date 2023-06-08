from DB_helpers import open_connection
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER


import os



def fetch_results(cursor, segment_id:int, street_side: str):
    cursor.execute("""SELECT * FROM parking_air WHERE segment_id = %s AND parking = %s""", (segment_id, street_side, ))
    air = cursor.fetchall()
    cursor.execute("""SELECT * FROM parking_cyclomedia WHERE segment_id = %s AND parking = %s""", (segment_id, street_side, ))
    cyclo = cursor.fetchall()

    return air, cyclo


def compare_one_on_one(air_result, cyclo_result):
    parking_air = air_result[2]
    percentage_air = air_result[3]

    parking_cyclo = cyclo_result[2]
    percentage_cyclo = cyclo_result[3]

    if parking_air == parking_cyclo:
        return parking_air, 100

    else:
        if percentage_air > percentage_cyclo:
            return parking_air, percentage_air
        
        elif percentage_air < percentage_cyclo:
            return parking_cyclo, percentage_cyclo
        
        else:
            return "not same value", -1


def run(db_config, db_user):
    with open_connection(db_config, db_user) as con:
        cursor = con.cursor()

        cursor.execute("""SELECT id FROM segments WHERE ot_name = 'Lindenau'""")
        segment_ids = [item[0] for item in cursor.fetchall()]

        for segment_id in segment_ids:

            air_left, cyclo_left = fetch_results(cursor, segment_id, "left")
            #print("air", air_left, "cyclo:", cyclo_left)
            if air_left != [] and cyclo_left != []:
                
                if len(air_left) == 1 and len(cyclo_left) == 1:
                    parking_left, percentage_left = compare_one_on_one(air_left[0], cyclo_left[0])
            
                else:
                    print("compare more than 1")
                    parking_left, percentage_left = "", -1
            else:
                parking_left, percentage_left = "no value", -1

            # write result for left to DB
            cursor.execute("""INSERT INTO parking VALUES (%s, %s, %s, %s)""", (segment_id, "left", parking_left, percentage_left))
            con.commit()

            air_right, cyclo_right = fetch_results(cursor, segment_id, "right")
            if air_right != [] and cyclo_right != []:
            
                if len(air_right) == 1 and len(cyclo_right) == 1:
                    parking_right, percentage_right = compare_one_on_one(air_right[0], cyclo_right[0])
                
                else:
                    print("compare more than 1")
                    parking_right, percentage_right = "", -1
            else:
                parking_right, percentage_right = "no value", -1
            
            #write result for right to DB
            cursor.execute("""INSERT INTO parking VALUES (%s, %s, %s, %s)""", (segment_id, "right", parking_right, percentage_right))
            con.commit()
                        
            print("RESULT--------->", {'segment_id': segment_id, 'left': parking_left, 'right': parking_right})

        

            

if __name__ == "__main__":
    db_config = os.path.join(RES_FOLDER_PATH, DB_CONFIG_FILE_NAME)
    run(db_config, DB_USER)