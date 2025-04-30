-- create our quick_park database:
CREATE DATABASE IF NOT EXISTS quick_park;

-- switch to using the quick_park database:
USE quick_park;

-- dropping tables may be useful if you want to clean up:
drop table IF EXISTS quick_park.parking_spot ;
drop table IF EXISTS quick_park.parking_spot_alert;
drop table IF EXISTS quick_park.spot_hourly_rate;
drop table IF EXISTS quick_park.parking_spot_types;

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
