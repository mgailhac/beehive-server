CREATE KEYSPACE IF NOT EXISTS waggle
  WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 2 };

USE waggle;

-- This table is for v1 data, which is deprecated, and only used in the original beehive1 server.  
-- This table should exist as long as the webserver looks for v1 data.
CREATE TABLE IF NOT EXISTS waggle.sensor_data (
    node_id         ascii,
    date            ascii,
    plugin_id       ascii,
    plugin_version  int,
    plugin_instance ascii,
    timestamp       timestamp,
    sensor          ascii,
    data            list<ascii>,
    sensor_meta     ascii,
    PRIMARY KEY ((node_id, date), plugin_id, plugin_version, plugin_instance, timestamp, sensor)
);

CREATE TABLE IF NOT EXISTS sensor_data_raw (
    node_id         ascii,    
    date            ascii,    
    ingest_id       int,
    plugin_name     ascii,
    plugin_version  ascii,
    plugin_instance ascii,
    timestamp       TIMESTAMP,      -- milliseconds from epoch, integer
    parameter       ascii,          -- parameter name (eg. temperature, humidity)
    data            ascii,          -- data from sensor, encoded to hex
    PRIMARY KEY  ((node_id, date), plugin_name, plugin_version, plugin_instance, timestamp, parameter)
);

CREATE TABLE IF NOT EXISTS sensor_data_decoded (
    node_id         ascii,
    date            ascii,
    ingest_id       int,
    meta_id         int,            -- foreign key into node_meta table
    timestamp       TIMESTAMP,      -- milliseconds from epoch, integer
    data_set        ascii,          -- distinguish between identical sensors on same node
    sensor          ascii,          -- eg. TMP112
    parameter       ascii,          -- parameter name (eg. temperature, humidity)
    data            ascii,          -- data from sensor, decoded / human-readable
    unit            ascii,
    PRIMARY KEY ((node_id, date), meta_id, sensor, parameter, timestamp, data_set, ingest_id, unit)
);

CREATE TABLE IF NOT EXISTS admin_messages (
    node_id         ascii,
    date            ascii,
    ingest_id       int,
    meta_id         int,            -- foreign key into node_meta table
    timestamp       TIMESTAMP,      -- milliseconds from epoch, integer
    data_set        ascii,          -- distinguish between identical sensors on same node
    sensor          ascii,    
    parameter       ascii,          -- parameter name (eg. temperature, humidity)
    data            ascii,          -- data from sensor, encoded to hex
    unit            ascii,
    PRIMARY KEY ((node_id, date), meta_id, sensor, parameter, timestamp, data_set, ingest_id, unit)
);

CREATE TABLE IF NOT EXISTS nodes_last_data (
    node_id         ascii,
    last_update     TIMESTAMP,      -- milliseconds from epoch, integer
    PRIMARY KEY     (node_id)
);

CREATE TABLE IF NOT EXISTS nodes_last_log (
    node_id         ascii,
    last_update     TIMESTAMP,      -- milliseconds from epoch, integer
    PRIMARY KEY     (node_id)
);

CREATE TABLE IF NOT EXISTS nodes_last_ssh (
    node_id         ascii,
    last_update     TIMESTAMP,      -- milliseconds from epoch, integer
    PRIMARY KEY     (node_id)
);
