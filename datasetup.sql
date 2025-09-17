-- create our quick_park database:
CREATE DATABASE IF NOT EXISTS quick_park;

-- switch to using the quick_park database:
USE quick_park;

-- dropping tables may be useful if you want to clean up:
drop table IF EXISTS quick_park.parking_spot_alert;
drop table IF EXISTS quick_park.parking_spot;
drop table IF EXISTS quick_park.spot_hourly_rate;
drop table IF EXISTS quick_park.parking_spot_types;
drop table IF EXISTS quick_park.garage;
drop table IF EXISTS quick_park.location;

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

-- where do the garages live?
CREATE TABLE IF NOT EXISTS quick_park.location(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   country_name string not null,
   state_name string not null,
   city_name string not null
);

-- parking spots live in garages...
CREATE TABLE IF NOT EXISTS quick_park.garage(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   location_id UUID NOT NULL REFERENCES quick_park.location(pk)
);

-- NB: A separate spot_reservation table would be a more normalized solution, however the goal (as of March 2025) is to not 
-- over-complicate things and focus on the transaction management aspect of this app
-- create the parking_spot table:
CREATE TABLE IF NOT EXISTS quick_park.parking_spot (
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   garage_id UUID NOT NULL REFERENCES quick_park.garage(pk),
   spot_id char(4) NOT NULL CHECK (spot_id <> ''),
   type_id SMALLINT REFERENCES quick_park.parking_spot_types(id),
   available boolean NOT NULL DEFAULT true CHECK (available in(true,false)),
   reserve_start timestamp,
   reserve_end TIMESTAMP CHECK (reserve_end > reserve_start OR reserve_end IS NULL),
   license_plate_holding_reservation CHAR(30) UNIQUE,
   UNIQUE (garage_id, spot_id)
);


-- create the parking_spot_alert table:
CREATE TABLE IF NOT EXISTS quick_park.parking_spot_alert(
  pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reserve_end timestamp NOT NULL,
  garage_id UUID NOT NULL,
  spot_id CHAR(4) NOT NULL,
  exceeded_time BOOLEAN NOT NULL DEFAULT false CHECK (exceeded_time IN (true, false)),
  license_plate_holding_reservation CHAR(30),
  UNIQUE (garage_id, spot_id, exceeded_time),
  FOREIGN KEY (garage_id) REFERENCES quick_park.garage(pk),
  FOREIGN KEY (garage_id, spot_id) REFERENCES quick_park.parking_spot(garage_id, spot_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_parking_spot_alert
  ON quick_park.parking_spot_alert (garage_id, spot_id, reserve_end, exceeded_time);

SHOW TABLES;

-- add some initial data to establish the starting point

-- locations:
INSERT INTO quick_park.location
   (country_name,state_name,city_name) values
   ('USA','California','Los Angeles'),('USA','New York','Manhattan'),('Canada','British Columbia','Vancouver'),('Canada','Ontario','Toronto');


-- for now: one garage in each of the locations:
INSERT INTO garage
   (location_id) 
   select pk from quick_park.location;

SELECT * from garage;

-- what types of spots exist?
INSERT into parking_spot_types (type,id) values ('small_car',1), ('regular_car',2),('truck',3),('electric',4);

SELECT * from parking_spot_types;

-- how much does each spot type cost per hour?
INSERT into spot_hourly_rate (type_id,hourly_rate) VALUES (1,4.99),(2,5.99),(3,6.99),(4,7.99);

SELECT * from spot_hourly_rate;

-- what spots exist?
-- let's give each garage the same number and type of spots for now
--INSERT into parking_spot (spot_id,type_id) values('1A',2),('1B',2),('1C',1),('1D',1),('1E',4),('2A',2),('2B',2),('2C',3),('2D',3),('3A',4),('3B',4),('3C',4);
INSERT INTO parking_spot (garage_id, spot_id, type_id)
SELECT
  g.pk,
  t.spot_id,
  t.type_id
FROM
  garage g
CROSS JOIN
  (VALUES
    ('1A', 2), ('1B', 2), ('1C', 1), ('1D', 1), ('1E', 4),
    ('2A', 2), ('2B', 2), ('2C', 3), ('2D', 3),
    ('3A', 4), ('3B', 4), ('3C', 4)
  ) AS t(spot_id, type_id);

-- reserve a spot as a test:
INSERT INTO parking_spot (
    garage_id, spot_id, reserve_start, reserve_end,
    available, license_plate_holding_reservation
) 
SELECT
    pk,                -- randomly selected garage_id
    '1E',              -- spot_id
    now(),             -- reserve_start
    now() + INTERVAL '5 minute',
    false,
    'DFD-7651'
FROM (SELECT pk FROM garage ORDER BY random() LIMIT 1)
ON CONFLICT (garage_id, spot_id)
DO UPDATE SET
    reserve_start = now(),
    reserve_end = now() + INTERVAL '5 minute',
    available = false,
    license_plate_holding_reservation = 'DFD-7651';

SELECT * from parking_spot;