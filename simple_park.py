import logging
import os
import random
import time
import threading
from argparse import ArgumentParser, RawTextHelpFormatter
import psycopg
from psycopg.errors import SerializationFailure, Error
from psycopg_pool import ConnectionPool
from collections import namedtuple
import urllib.parse as urlparse

# this example expects the db url to be set in the runtime environment
# you will do something like this before running the program:
# export DATABASE_URL='postgresql://root@192.168.1.20:26000/quick_park?sslmode=disable'
# cd /Users/devload/wip/python/quick_park
# source qp_env/bin/activate
# when starting this example you can add the following commandline arguments: 
# -v (for debug-level logging) 
# -min <minimum-number-of-pooled-connections>
# -max <maximum-number-of-pooled-connections>
# -ltms <acceptable_latency_in_millis>
# sample start command: (after ensuring the URL is set in the env)
# python3 qp_app.py -v -min 2 -max 8
class QuickPark:
    def __init__(self):
        self.exit_event = threading.Event()  # Initialize the event for thread coordination
        parser = ArgumentParser(description="Simple RDBMS Transaction Example")
        parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose/logging output to screen")
        parser.add_argument("--minpoolsize", "-min", type=int, default=2, help="What is minimum size of connection Pool to DB?")
        parser.add_argument("--maxpoolsize", "-max", type=int, default=20, help="What is maximum size of connection Pool to DB?")
        parser.add_argument("--latencythresholdms", "-ltms", type=int, default=1000, help="Below this threashold in milliseconds no need to log latency for SQL activities.")
        
        args = parser.parse_args()
        self.verbose = args.verbose
        self.latency_threshold_millis = args.latencythresholdms
        
        logging.basicConfig(level=logging.DEBUG if self.verbose else logging.INFO)
        logging.info(f"ARGS set to: verbose == {self.verbose}")
                # ANSI colors
        self.GREEN = "\033[92m"
        self.RED = "\033[91m"
        self.RESET = "\033[0m"    


        env_url = os.environ.get("DATABASE_URL")
        db_url = urlparse.urlparse(env_url)
        dbname = db_url.path[1:]
        user = db_url.username
        password = db_url.password
        host = db_url.hostname
        port = db_url.port
        application_name="quick_park_demo"
        port = str(port)
        if password =='':
            self.conn_string = f"dbname={dbname} user={user} host={host} port={port} application_name={application_name}"
        else:
            self.conn_string = f"dbname={dbname} user={user} password={password} host={host} port={port} application_name={application_name}"
        
        self.pool = ConnectionPool(self.conn_string, min_size=args.minpoolsize, max_size=args.maxpoolsize)

    ## this function displays the commandline menu to the user
    ## it offers the ability to end the program by typing 'end'
    def display_menu(self):
        # This string is used to separate areas of command line output: 
        spacer = "\n**********************************************"
        print(spacer)
        print('\tType: END   and hit enter to exit the program...\n')
        print('\tCommandline Instructions: \nTYPE your preferred action from this list:')
        print('(only hit enter for the purpose of submitting your selection)')
        print(spacer)
        # get user input/prompt/question:
        user_text = input('\nYour Options:\nMake single reservation (mr)\nquery parking space state (qs)\nloop with threads (loop)\nend program (END) :\t')
        if user_text.lower() =="end":
            print('\nYOU ENTERED --> \"END\" <-- QUITTING PROGRAM!!')
            exit(0)
        print()
        return (user_text)

    def get_connection(self):
        """Gets a connection from the pool."""
        conn = self.pool.getconn()
        if conn is None:
            raise Exception("Error: No database connection available")
        return conn

    def put_connection(self, conn):
        """Returns a connection to the pool."""
        self.pool.putconn(conn)
    
    def show_parking_spot_data(self,row_count):
        sql_query='''SELECT 
                ROW_NUMBER() OVER(),
                COUNT(pst.type) OVER(PARTITION BY pst.type) AS SPOTS_OF_TYPE,
                ps.spot_id,pst.type,available
                FROM parking_spot ps
                JOIN parking_spot_types pst
                ON ps.type_id = pst.id
                LIMIT %s;
                '''
        conn = self.get_connection()
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(sql_query,(row_count,))
                rows = cur.fetchall()
                if rows:
                    print(f"{' row':>5}  {'SPOTS_OF_TYPE':>14}  {'spot_id':<9}  {'type':<13}  {'available':<5}")
                    print("-" * 60)
                    for row in rows:
                        available = bool(row[4])
                        available_str = f"{self.GREEN}True{self.RESET}" if available else f"{self.RED}False{self.RESET}"
                        print(f"{row[0]:>3}  {row[1]:>14}  {row[2]:<10}  {row[3]:<10}  {available_str:<9}")
                else:
                    print(f"No info on parking found")
        self.put_connection(conn) # return the connection OUTSIDE of the TX block

    # gets connection from the pool:
    def add_parking_reservation(self,license_plate, spot_type_id, duration_in_hours):
        logging.debug(f"\nAdding reservation for {license_plate} {spot_type_id} {duration_in_hours}...")        
        query = f'''WITH AvailableSpot AS (
        SELECT ps.spot_id
        FROM parking_spot ps
        JOIN parking_spot_types pst ON ps.type_id = pst.id
        WHERE ps.available = true AND pst.id = %s
        LIMIT 1
        FOR UPDATE
        )
        UPDATE parking_spot
        SET
        reserve_start = now(),
        reserve_end = now() + INTERVAL '{duration_in_hours} hours',
        available = false,
        license_plate_holding_reservation = %s
        WHERE spot_id = (SELECT spot_id FROM AvailableSpot) AND available = true;'''
        
        conn = self.get_connection()
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(query, (spot_type_id, license_plate))
                logging.debug(f"[add_parking_reservation]--> {cur.rowcount} rows updated")
        self.put_connection(conn) # return the connection OUTSIDE of the TX block                

    # here we prepare the args for adding a reservation:
    def make_reservation(self):
        logging.debug(f"Simulating Reservations (client behavior) --> :START")
        #license_plate, spot_type_id, duration_in_hours
        license_plate = 'NXT'+str(random.randint(1024,9999))
        spot_type_id = round(time.time()%4)
        hours = round(time.time()%12)
        self.add_parking_reservation(license_plate,spot_type_id,hours)
        logging.debug("Simulating Reservation (client behavior) --> COMPLETED")  
    
    # now we see the need for a spot_reservation table!
    # updating is not deleting! 
    # TODO: adjust schema and logic to utilize spot_reservation table
    def cancel_parking_reservation(self):
        logging.debug(f"\nDeleting a reservation (actually updating parking_spot table)...")
        query = '''WITH ReservedSpot AS (
        SELECT spot_id
        FROM parking_spot
        WHERE available = false
        LIMIT 1
        FOR UPDATE
        )
        UPDATE parking_spot
        SET available = true, 
        reserve_start = null,
        reserve_end = null,
        license_plate_holding_reservation = null 
        WHERE spot_id = (SELECT spot_id FROM ReservedSpot);'''
        conn = self.get_connection()
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(query)
                # we should really clean up the other columns: reservation_start, reservation_end, license_plate
                logging.debug("Updated reservation for {spot_id}.\n")
        self.put_connection(conn) # return the connection OUTSIDE of the TX block

    # reserving and cancelling reservations:
    def do_loop(self,thread_name,count):
        print(f"{thread_name} --> STARTING LOOP ")
        x=0 
        
        while x<count:
            start_time=int(time.time() * 1000)
            x+=1
            # wrapping function call in retry logic:
            self.handle_errors(lambda _: self.make_reservation())
            # former code:        
            #self.make_reservation()
            if x%2==0:
                self.cancel_parking_reservation()
                time.sleep(0.025) # sleep for 25 millis 
            if (int(time.time() * 1000) > start_time+self.latency_threshold_millis):
                logging.warning(f'Loop iteration took {int(time.time() * 1000) - start_time} ms')
    #this loop will end when exit_event is set
    def spot_check_loop(self):
        while not self.exit_event.is_set():
            self.spot_check()
            time.sleep(10) # sleep for 10 seconds

    # checks for reservations that are within 10 min of expiring
    # also checks for reservations that have expired
    # adds them to the parking_spot_alert table
    def spot_check(self):
        logging.debug("*** EXECUTING SPOT_CHECK FOR: quick_park.parking_spot_alert ***")
        query = '''INSERT INTO quick_park.parking_spot_alert 
        (reserve_end, spot_id, license_plate_holding_reservation, exceeded_time) 
        SELECT reserve_end, spot_id, license_plate_holding_reservation, 
        CASE WHEN reserve_end BETWEEN  now() - INTERVAL '10 minutes' AND now() THEN false 
        WHEN reserve_end > now() THEN true 
        ELSE false 
        END
        FROM quick_park.parking_spot 
        WHERE reserve_end > now() - INTERVAL '10 minutes' 
        AND reserve_end IS NOT NULL 
        AND spot_id NOT IN (SELECT spot_id from quick_park.parking_spot_alert); 
        '''
        conn = self.get_connection()
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(query)
                # we should really clean up the other columns: reservation_start, reservation_end, license_plate
                logging.debug("Updated Alert Table.\n")
        self.put_connection(conn) # return the connection OUTSIDE of the TX block


    def start_spot_check_thread(self):
        logging.debug("Starting spot_check_thread ")
        thread1 = threading.Thread(target=self.spot_check_loop, args=())
        thread1.start() 
        
    def start_x_threads(self,how_many_threads,iterations):
        logging.info(f"{int(time.time() * 1000)} Starting {how_many_threads} threads with {iterations} iterations each...\n")
        all_threads = []
        for i in range(how_many_threads):
            thread = threading.Thread(target=self.do_loop, args=(f'T H R E A D #{i}',iterations))
            all_threads.append(thread)
            thread.start()
        
        for thread in (all_threads):
            thread.join()

        logging.info(f"{int(time.time() * 1000)} {how_many_threads} threads finished")

    # signalling the SPOT_CHECK thread to stop
    def stop(self):
        self.exit_event.set()
        time.sleep(.1) # sleep for 100 millis

    # if lamda function which wraps a DB operation fails
    # either retry or quietly report the error allowing 
    # program to continue
    def handle_errors(self,lamfun):
        retry_flag = True
        retry_count=1
        while retry_flag and retry_count < 3 :
            try:
                lamfun(self)
                retry_flag = False
            except SerializationFailure as e:
                logging.error(f"{int(time.time() * 1000)} SerializationFailure . . .\n{e}")
                retry_count+=1
                time.sleep(.1) # sleep for 100 millis
            except psycopg.errors.UniqueViolation as e:
                logging.error(f"{int(time.time() * 1000)} UniqueViolation . . .\n{e}")
                retry_count+=1
                time.sleep(.525) # sleep for 525 millis
            except Exception as e:
                logging.error(f"{int(time.time() * 1000)} Unexpected Exception: {e}")
                retry_count=3

def main():
    try:
        qp = QuickPark()
        qp.start_spot_check_thread()
        while True:
            usr_action=qp.display_menu()
            if(usr_action.strip().lower()=='qs'):
                qp.show_parking_spot_data(20) 
            if(usr_action.strip().lower()=='mr'):
                qp.make_reservation()
            if(usr_action.strip().lower()=='loop'):
                count=input("How many times should each thread loop? (25): ")
                count=int(count)
                if count<1 or count > 10000:
                    print(f"You entered: {count} that's a bit silly --> adjusting to 25")
                    count=25
                how_many=input("How many threads to start? (2): ")
                how_many=int(how_many)
                if how_many<2 or how_many > 100:
                    print(f"You entered: {count} that's a bit silly --> adjusting to 5")
                    how_many=5

                qp.start_x_threads(how_many,count)
            if (usr_action.strip().lower()!='mr') and (usr_action.strip().lower()!='qs') and (usr_action.strip().lower()!='loop'):
                print(f"OPTION {usr_action} NOT IMPLEMENTED YET...")
            
            input('\n\thit enter to continue...\n')
    finally:
        print("CLEANING UP AS PROGRAM EXITS...")
        qp.stop()

if __name__ == "__main__":
    main()