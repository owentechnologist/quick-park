## QUICK-PARK is a bit of SQL executed using python
## this is a simple aplication designed to showcase Transactional behavior while using an RDBMS

## The premise is a car parking app where there is competition for parking spots for various cars & trucks 

To run the example:

1. initialize the python virtual environment specific to this project:
``` 
python3 -m venv qp_env
``` 
2. activate the python environment:  [This step is repeated anytime you want this qp environment back]
``` 
source qp_env/bin/activate
``` 
3. Install the libraries: [only necesary to do this one time per environment]
```
pip3 install -r requirements.txt
```
4. Connect to your postgres-compatible database and execute the DDL necessary to construct the tables used by this little application:
![ERD.png](./ERD.png)

### FYI: Initial Data for this mini-app can be loaded using the sql commandline client provided with cockroachdb in the following manner: (assumes you started cockroachdb in insecure mode and are in the same directory as this readme and the datasetup.sql file)
```
$ cockroach sql --insecure --user=root --host=localhost --database=defaultdb -f datasetup.sql
```
### how to start a local single instance of cockroachdb suitable for lightweight testing/dev work:  (add a space and an ampersand at the end of the command if you want it to run in the background)
```
cockroach start-single-node \
  --insecure \
  --listen-addr=localhost:26257 \
  --http-addr=localhost:8080
```

### It may be helpful to read through the contents of the datasetup.sql file
### To understand the DDL / data model, and sample SQL for this mini-app

### In addition to the commands in the datasetup.sql file
### The following statements can be executed from any SQL client for example you may use psql: (replace your user, port and host values to match your environment)

``` 
psql -U root -p 26000 -h 192.168.1.20

-- look at what tables exist in your database:
SHOW tables;

-- check the state of the parking lot:
SELECT 
  ROW_NUMBER() OVER(),
  COUNT(pst.type) OVER(PARTITION BY pst.type) AS SPOTS_OF_TYPE,
  ps.spot_id,pst.type,available
FROM parking_spot ps
JOIN parking_spot_types pst
ON ps.type_id = pst.id;

-- check to see if an alert needs to be added (in a future version, alerts could be used to facilitate notifying management and clients, and tow trucks)
-- alerts come in two flavors: 
-- if a row exists and exceeded_time is false: the reservation is close to expiring (10 min warning)
-- if a row exists and exceeded time is true: the reservation has been exceeded, and some action may be necessary (calling a tow truck?) 

-- sample alert INSERT:
INSERT INTO quick_park.parking_spot_alert (reserve_end, spot_id, license_plate_holding_reservation, exceeded_time) 
SELECT reserve_end, spot_id, license_plate_holding_reservation, 
CASE WHEN reserve_end BETWEEN  now() - INTERVAL '10 minutes' AND now() THEN false 
  WHEN reserve_end < now() THEN true 
  ELSE false 
  END
FROM quick_park.parking_spot 
WHERE reserve_end IS NOT NULL 
AND spot_id NOT IN (SELECT spot_id from quick_park.parking_spot_alert); 

-- this next statement updates an alert after it is originally inserted: 

UPDATE quick_park.parking_spot_alert SET exceeded_time = true WHERE reserve_end > now(); 

-- what do we see in the alerts table?

select * from quick_park.parking_spot_alert;
```

## OK - now to run this little application:

5. Provide the url to your database as an env variable: (adjust your username, hostname, port, database name as is appropriate)
```
export DATABASE_URL='postgresql://root@192.168.1.20:26000/quick_park?sslmode=disable'
```
6. Execute the simple_park.py code from the project directory.
```
(qp_env) devload@devload quick_park % python3 simple_park.py -v -min 3 -max 5 -ltms 3000
```

|                                   argument                                     |                    explanation                          |
| ------------------------------------------------------------------------------ | ------------------------------------------------------- |
| -v                                              | turns on verbose logging (debug level)         |
| -min <some-number>                                          | change minimum # of connections in db pool (defaults to 2) |
| -max <some-number>                                | change maximum # of connections in db pool (defaults to 20)|
| -ltms <some-number> (defaults to 1000)             | latency threshold in milliseconds: below which, no performance-related logging occurs |


### When the app starts it offers 4 options for the user:
* mr (make a single parking spot reservation)
* qs (query the parking spots for latest state)
* loop (setup and run multiple threads that randomly fill and empty parking spots)
* end (quit the program - cleaning up the connections used)

### If you choose to run multiple threads in the loop option offered, you are likely to encounter an occassional exception caused by either a duplicate license plate number used when reserving a parking spot, or a failure of a TX (transaction) due to attempts by multiple threads to update the same row 