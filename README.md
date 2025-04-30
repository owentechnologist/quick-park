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
4. Connect to your postges-compatible database and execute the DDL necessary to construct the tables used by this little application:
![ERD.png](./ERD.png)
### DDL, data model, and sample SQL for this mini-app is provided below:
``` 
-- the following statements can be executed from any SQL client for example you may use psql: (replace your user, port and host values to match your environment)

psql -U root -p 26000 -h 192.168.1.20

-- create our quick_park database:
CREATE DATABASE IF NOT EXISTS quick_park;

-- switch to using the quick_park database:
USE quick_park;

-- dropping tables may be useful if you want to clean up:
drop table quick_park.parking_spot;
drop table quick_park.parking_spot_alert;
drop table quick_park.spot_hourly_rate;
drop table quick_park.parking_spot_types;

-- look at what tables exist in your database:
SHOW tables;

-- create the parking_spot_types table:
CREATE TABLE IF NOT EXISTS quick_park.parking_spot_types(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   type CHAR(20) NOT NULL CHECK (type in ('small_car', 'regular_car','truck','electric')),
   id SMALLINT UNIQUE NOT NULL DEFAULT 2 CHECK (id BETWEEN 1 AND 4)
);

-- create the spot_hourly_rate table:
CREATE TABLE IF NOT EXISTS quick_park.spot_hourly_rate (
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   type_id SMALLINT REFERENCES quick_park.parking_spot_types(id),
   hourly_rate decimal(4,2)NOT NULL CHECK (hourly_rate>0.01)
);

-- NB: A separate spot_reservation table would be a more normalized solution, however the goal (as of March 2025) is to not over-complicate things and focus on the transaction management aspect of this app
-- create the parking_spot table:
CREATE TABLE IF NOT EXISTS quick_park.parking_spot (
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   spot_id char(4) UNIQUE NOT NULL CHECK (spot_id <> ''),
   type_id SMALLINT REFERENCES quick_park.parking_spot_types(id),
   available boolean NOT NULL DEFAULT true CHECK (available in(true,false)),
   reserve_start timestamp,
   reserve_end TIMESTAMP CHECK (reserve_end > reserve_start OR reserve_end IS NULL),
   license_plate_holding_reservation CHAR(30) UNIQUE
);

-- create the parking_spot_alert table:
CREATE TABLE IF NOT EXISTS quick_park.parking_spot_alert(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   reserve_end timestamp NOT NULL,
   spot_id char(4) NOT NULL REFERENCES quick_park.parking_spot(spot_id),
   exceeded_time boolean NOT NULL DEFAULT false CHECK (exceeded_time in(true,false)),
   license_plate_holding_reservation CHAR(30)
);

-- add some initial data to establish the starting point
-- what types of spots exist?
INSERT into parking_spot_types (type,id) values ('small_car',1), ('regular_car',2),('truck',3),('electric',4);

-- how much does each spot type cost per hour?
INSERT into spot_hourly_rate (type_id,hourly_rate) VALUES (1,4.99),(2,5.99),(3,6.99),(4,7.99);

-- NB: As of April 1st 2025 We are only focused on a single small garage, the model does not yet anticipate multiple garages
-- what spots exist?
INSERT into parking_spot (spot_id,type_id) values('1A',2),('1B',2),('1C',1),('1D',1),('1E',4),('2A',2),('2B',2),('2C',3),('2D',3),('3A',4),('3B',4),('3C',4);

-- reserve a spot as a test:
UPDATE parking_spot set reserve_start=now(), reserve_end = (now()+ INTERVAL '1 hour' ),available=false,license_plate_holding_reservation='DFD-7651' WHERE spot_id='1E';

-- look at the state of the parking situation:
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


