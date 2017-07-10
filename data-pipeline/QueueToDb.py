#!/usr/bin/env python3

# QueueToDb.py
import os
import sys
sys.path.append(os.path.abspath('../'))
sys.path.append("/usr/lib/waggle/")
sys.path.append("/usr/lib/waggle/beehive-server")

import argparse
import binascii
from cassandra.cluster import Cluster
from cassandra.query import BatchStatement
from cassandra import ConsistencyLevel
from cassandra.cqlengine.columns import Ascii
from cassandra.cqlengine.usertype import UserType
from config import *
import datetime
import json
import logging 
from multiprocessing import Process, Manager
import pika
import time
#logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.CRITICAL)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DataProcess(Process):
    """
        This process handles all data submissions
        whichData specifies either 'raw', 'decoded' or 'node-metrics'
    """

    def __init__(self, whichData, verbosity = 0):
        """
            Starts up the Data handling Process
        """
        super(DataProcess,self).__init__()
        
        if whichData == 'raw':
            self.input_exchange = 'data-pipeline-in'
            self.queue          = 'db-raw'
            self.statement = "INSERT INTO    sensor_data_raw   (node_id, date, plugin_name, plugin_version, plugin_instance, timestamp, parameter, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            self.function_ExtractValuesFromMessage = self.ExtractValuesFromMessage_raw
            credentials = pika.PlainCredentials('queue_to_db_raw', 'waggle')
        elif whichData == 'decoded':  
            self.input_exchange = 'plugins-out'
            self.queue          = 'db-decoded'
            self.statement = "INSERT INTO    sensor_data_decoded   (node_id, date, ingest_id, meta_id, timestamp, data_set, sensor, parameter, data, unit) VALUES (?, ?, ?, ?, ?,   ?, ?, ?, ?, ?)"
            self.function_ExtractValuesFromMessage = self.ExtractValuesFromMessage_decoded
            credentials = pika.PlainCredentials('queue_to_db_decoded', 'waggle')
        elif whichData == 'node-metrics':
            self.input_exchange = 'node-metrics'
            self.queue          = 'node-metrics'
            self.statement = "INSERT INTO    node_metrics_date   (date, timestamp, node_id, data) VALUES (?, ?, ?, ?)"
            self.function_ExtractValuesFromMessage = self.ExtractValuesFromMessage_node_metrics
            credentials = pika.PlainCredentials('node-metrics', 'waggle')
        else:
            print('ERROR: unsupported value for <whichData>:  ', whichData)
            
        logger.info("Initializing DataProcess")
        
        # Connect to rabbitMQ
        while True:
            try:
                parameters = pika.ConnectionParameters('beehive-rabbitmq', credentials=credentials)
                self.connection = pika.BlockingConnection(parameters)
                
            except Exception as e:
                logger.error("QueueToDb: Could not connect to RabbitMQ server: %s" % (e))
                time.sleep(1)
                continue
            break
            
    
        logger.info("Connected to RabbitMQ server")
        self.verbosity = verbosity
        self.numInserted = 0
        self.numFailed = 0
        self.session = None
        self.cluster = None
        self.prepared_statement = None
        
        self.cassandra_connect()
        
        
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)
        
        # Declare and bind this process's queue - should already be done in initialization script
        #self.channel.queue_declare(self.queue, durable=True)
        #self.channel.queue_bind(exchange = self.input_exchange, queue = self.queue)
        
        try: 
            self.channel.basic_consume(self.callback, queue=self.queue)
        except KeyboardInterrupt:
           logger.info("exiting.")
           sys.exit(0)
        except Exception as e:
           logger.error("error: %s" % (str(e)))

    def callback(self, ch, method, props, body):
        #TODO: this simply drops failed messages, might find a better solution!? Keeping them has the risk of spamming RabbitMQ
        if self.verbosity > 1:
            print('######################################')
            print('method = ', method)
            print('props = ', props)
            print('body = ', body)
        '''EXAMPLE: 
            props =  <BasicProperties(['app_id=coresense:3', 'content_type=b', 'delivery_mode=2', 'reply_to=0000001e06107d97', 'timestamp=1476135836151', 'type=frame'])>
        '''
        try:
            for iValues, values in enumerate(self.function_ExtractValuesFromMessage(props, body)):
                # Send the data off to Cassandra
                if self.verbosity > 1: 
                    print('iValues =', iValues)
                    print(' values =',  values)
                self.cassandra_insert(values)
        except Exception as e:
            values = None
            self.numFailed += 1
            logger.error("Error inserting data: %s" % (str(e)))
            logger.error(' method = {}'.format(repr(method)))
            logger.error(' props  = {}'.format(repr(props)))
            logger.error(' body   = {}'.format(repr(body)))
            ch.basic_ack(delivery_tag = method.delivery_tag)
            return

        ch.basic_ack(delivery_tag = method.delivery_tag)
        if values:
            self.numInserted += 1
            if self.numInserted % 1000 == 0:
                logger.debug('  inserted {} / {} raw samples of data'.format(self.numInserted, self.numInserted + self.numFailed))

    # Parse a message of sensor data and convert to the values to be inserted into a row in the db.  NOTE: this is a generator - because the decoded messages produce multiple rows of data.
    def ExtractValuesFromMessage_raw(self, props, body):
        if self.verbosity > 0: print('props.app_id =', props.app_id)
        versionStrings  = props.app_id.split(':')
        sampleDatetime  = datetime.datetime.utcfromtimestamp(float(props.timestamp) / 1000.0)
        sampleDate      = sampleDatetime.strftime('%Y-%m-%d')
        node_id         = props.reply_to
        #ingest_id       = props.ingest_id ##props.get('ingest_id', 0)
        #print('ingest_id: ', ingest_id)
        plugin_name     = versionStrings[0]
        plugin_version  = versionStrings[1]
        plugin_instance = '0' if (len(versionStrings) < 3) else versionStrings[2]
        timestamp       = int(props.timestamp)
        parameter       = props.type
        data            = str(binascii.hexlify(body))

        values = (node_id, sampleDate, plugin_name, plugin_version, plugin_instance, timestamp, parameter, data)

        if self.verbosity > 0:
            print('   node_id = ',          node_id         )
            print('   date = ',             sampleDate      )
            #print('   ingest_id = ',        ingest_id       )
            print('   plugin_name = ',      plugin_name     )
            print('   plugin_version = ',   plugin_version  )
            print('   plugin_instance = ',  plugin_instance )
            print('   timestamp = ',        timestamp       )
            print('   parameter = ',        parameter       )
            print('   data = ',             data            )
        yield values
                
    def ExtractValuesFromMessage_decoded(self, props, body):
        #(node_id, date, meta_id, timestamp, data_set, sensor, parameter, data, unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"

        dictData = json.loads(body.decode())
        
        # same for each parameter:value pair
        sampleDatetime  = datetime.datetime.utcfromtimestamp(float(props.timestamp) / 1000.0)
        node_id         = props.reply_to
        sampleDate      = sampleDatetime.strftime('%Y-%m-%d')
        ingest_id       = 0 # props.ingest_id ##props.get('ingest_id', 0)
        #print('ingest_id: ', ingest_id)
        meta_id         = 0 #props.meta_id
        timestamp       = int(props.timestamp)
        data_set        = props.app_id
        sensor          = props.type
        unit            = 'NO_UNIT' #props.unit
        
        for k in dictData.keys():
            parameter      = k
            data           = str(dictData[k])

            values = (node_id, sampleDate, ingest_id, meta_id, timestamp, data_set, sensor, parameter, data, unit)

            if self.verbosity > 0:
                print('   node_id = ',          node_id     )
                print('   date = ',             sampleDate  )
                print('   ingest_id = ',        ingest_id   )
                print('   meta_id = ',          meta_id     )
                print('   timestamp = ',        timestamp   )
                print('   data_set = ',         data_set    )
                print('   sensor = ',           sensor      )
                print('   parameter = ',        parameter   )
                print('   data = ',             data        )
                print('   unit = ',             unit        )
            yield values

    def ExtractValuesFromMessage_node_metrics(self, props, body):

        dictData = json.loads(body.decode())
        
        # same for each parameter:value pair
        node_id         = props.reply_to
        sampleDate      = sampleDatetime.strftime('%Y-%m-%d')
        timestamp       = int(props.timestamp)
        
        for k in dictData.keys():
            parameter      = k
            data           = str(dictData[k])

            values = (node_id, sampleDate, ingest_id, meta_id, timestamp, data_set, sensor, parameter, data, unit)

            if self.verbosity > 0:
                print('   date = ',             sampleDate  )
                print('   timestamp = ',        timestamp   )
                print('   node_id = ',          node_id     )
                print('   data = ',             data        )
            yield values
            
    def cassandra_insert(self, values):
    
        if not self.session:
            self.cassandra_connect()
            
        if not self.prepared_statement:
            try: 
                self.prepared_statement = self.session.prepare(self.statement)
            except Exception as e:
                logger.error("Error preparing statement: (%s) %s" % (type(e).__name__, str(e)) )
                raise
        
        if self.verbosity > 1: logger.debug("inserting: %s" % (str(values)))
        try:
            bound_statement = self.prepared_statement.bind(values)
        except Exception as e:
            logger.error("QueueToDb: Error binding cassandra cql statement:(%s) %s -- values was: %s" % (type(e).__name__, str(e), str(values)) )
            raise

        connection_retry_delay = 1
        while True :
            # this is long term storage    
            try:
                self.session.execute(bound_statement)
            except TypeError as e:    
                 logger.error("QueueToDb: (TypeError) Error executing cassandra cql statement: %s -- values was: %s" % (str(e), str(values)) )
                 break
            except Exception as e:
                logger.error("QueueToDb: Error (type: %s) executing cassandra cql statement: %s -- values was: %s" % (type(e).__name__, str(e), str(values)) )
                if "TypeError" in str(e):
                    logger.debug("detected TypeError, will ignore this message")
                    break
                
                self.cassandra_connect()
                time.sleep(connection_retry_delay)
                if connection_retry_delay < 10:
                    connection_retry_delay += 1
                continue
            
            break

    def cassandra_connect(self):
        bDone = False
        iTry = 0
        while not bDone and (iTry < 5):
            if self.cluster:
                try:
                    self.cluster.shutdown()
                except:
                    pass
                    
            self.cluster = Cluster(contact_points=[CASSANDRA_HOST])
            self.session = None
            
            iTry2 = 0
            while not bDone and (iTry2 < 5):
                iTry2 += 1
                try: # Might not immediately connect. That's fine. It'll try again if/when it needs to.
                    self.session = self.cluster.connect('waggle')
                    if self.session:
                        bDone = True
                except:
                    logger.warning("QueueToDb: WARNING: Cassandra connection to " + CASSANDRA_HOST + " failed.")
                    logger.warning("QueueToDb: The process will attempt to re-connect at a later time.")
                if not bDone:
                     time.sleep(3)

    def run(self):
        self.cassandra_connect()
        self.channel.start_consuming()

    def join(self):
        super(DataProcess,self).terminate()
        self.connection.close(0)
        if self.cluster:
            self.cluster.shutdown()
            
   
if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument('database', choices = ['raw', 'decoded'], 
        help = 'which database the data is flowing to')
    argParser.add_argument('--verbose', '-v', action='count')
    args = argParser.parse_args()
    whichData = args.database
    verbosity = 0 if not args.verbose else args.verbose
    
    p = DataProcess(whichData, verbosity)
    p.start()
    
    print(__name__ + ': created process ', p)
    time.sleep(10)   
    
    while p.is_alive():
        time.sleep(10)
        
    print(__name__ + ': process is dead, time to die')
    p.join()    
