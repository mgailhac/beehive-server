#!/usr/bin/env python3
import argparse
from binascii import unhexlify
import datetime
import json
import logging
import os
import pika
import re
import subprocess
import sys
import time

global verbosity

""" Stream data to a beehive just like a node.

    ./soft-node.py  10.10.10.183  000002000000ffff  /home/wcatino/node0

"""

# pika - let's make it verbose...
logging.getLogger('pika').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#_______________________________________________________________________
# Run a command, return its output as a single string
def CmdString(command):
    print('cmd = ', command)
    return subprocess.getoutput(command)

#_______________________________________________________________________
# Run a command, return the output as a list of strings
def CmdList(command, bDebug = True):
    strResult = subprocess.getoutput(command)
    if bDebug:
        print('CmdList:   command = ', command,'\n   strResult = ', strResult)
    if len(strResult):
        result = strResult.split('\n')
    else:
        result = []
    return result

#_______________________________________________________________________
# Run a command and capture it's output
def Cmd0(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
    return iter(p.stdout.readline, b'')

#_______________________________________________________________________
# Run a command and capture it's output - return iterable like result of open()
def Cmd1(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  shell = True,
                                  universal_newlines = True)
    #return iter(p.stdout.readline, b'')
    return p.stdout
 
#_______________________________________________________________________
def GetPortFromNode(nodeId):
    nodeId = nodeId.lower()
    dictNodeToPort = GetDictNodeToPort()
    port = None
    if nodeId in dictNodeToPort:
        port = dictNodeToPort[nodeId]
    return port

    
#_______________________________________________________________________
def DatetimeFromString(strTime):
    if len(strTime) == 19:
        result = datetime.datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")
    else:
        result = datetime.datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S.%f")
    return result
#_______________________________________________________________________
def DatetimeToString(t):
    return t.strftime("%Y-%m-%d %H:%M:%S.%f")
#_______________________________________________________________________
def DatetimeToDateString(t):
    return t.strftime("%Y-%m-%d")

    
    
#_______________________________________________________________________
# adapted from nodecontroller/registration-service
#_______________________________________________________________________
def run_registration_command(registration_key, cert_server, command):
  ssh_command =\
    ["ssh", cert_server,
     "-p", "20022",
     "-i", registration_key,
     "-o", "StrictHostKeyChecking no",
     command]
  logger.debug("Executing:", str(ssh_command))
  p = subprocess.Popen(
    ssh_command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
  return p.stdout.read().decode()

#_______________________________________________________________________
# adapted from nodecontroller/registration-service
#_______________________________________________________________________
def read_file( str ):
    print("read_file: "+str)
    if not os.path.isfile(str) :
        return ""
    with open(str,'r') as file_:
        return file_.read().strip()
    return ""



#_______________________________________________________________________
# adapted from nodecontroller/registration-service
#_______________________________________________________________________
def create_dir_for_file(file):
    file_dir = os.path.dirname(file)
    logger.debug("create_dir_for_file:", str(file_dir))
    if not os.path.exists(file_dir):
        try:
            os.makedirs(file_dir)
        except Exception as e:
            logger.error("Could not create directory '%s' : %s" % (file_dir,str(e)) )
            sys.exit(1)


#_______________________________________________________________________
# adapted from nodecontroller/registration-service
#_______________________________________________________________________
def get_certificates(dir):
    cert_server = ""
    #with open("/etc/waggle/server_host") as cert_server_file:
    with open(dir + "/server_host") as cert_server_file:
        cert_server = cert_server_file.readline().rstrip()
    node_id = ""
    #with open("/etc/waggle/node_id") as node_id_file:
    with open(dir + "/node_id") as node_id_file:
        node_id = node_id_file.readline().rstrip()
        
    #registration_key = "/root/id_rsa_waggle_aot_registration"
    registration_key =  dir + "/id_rsa_waggle_aot_registration"
    
    #reverse_ssh_port_file = '/etc/waggle/reverse_ssh_port'
    reverse_ssh_port_file = dir + '/reverse_ssh_port'
    
    #ca_root_file = "/usr/lib/waggle/SSL/waggleca/cacert.pem"
    ca_root_file = dir + "/cacert.pem"
    
    #client_key_file = "/usr/lib/waggle/SSL/node/key.pem"
    client_key_file = dir + "/node/key.pem"
    
    #client_cert_file = "/usr/lib/waggle/SSL/node/cert.pem"
    client_cert_file = dir + "/node/cert.pem"

    loop=-1
    while True:
        loop=(loop+1)%20
        ca_root_file_exists = os.path.isfile(ca_root_file) and os.stat(ca_root_file).st_size > 0
        client_key_file_exists = os.path.isfile(client_key_file) and os.stat(client_key_file).st_size > 0
        client_cert_file_exists = os.path.isfile(client_cert_file) and os.stat(client_cert_file).st_size > 0
        reverse_ssh_port_file_exists = os.path.isfile(reverse_ssh_port_file) and os.stat(reverse_ssh_port_file).st_size > 0

        #check if cert server is available
        if not (ca_root_file_exists and client_key_file_exists and client_cert_file_exists and reverse_ssh_port_file_exists):

            if not (os.path.isfile(registration_key) and os.stat(registration_key).st_size > 0):
                logger.error("Registration file '{}' not found.".format(registration_key))
        
            if (loop == 0):
                if not ca_root_file_exists:
                    logger.info("File '%s' not found." % (ca_root_file))
                if not client_key_file_exists:
                    logger.info("File '%s' not found." % (client_key_file))
                if not client_cert_file_exists:
                    logger.info("File '%s' not found." % (client_cert_file))
                if not reverse_ssh_port_file_exists:
                    logger.info("File '%s' not found." % (reverse_ssh_port_file))

            try:
                html = run_registration_command(registration_key, cert_server, "")
            except Exception as e:
                if (loop == 0):
                    logger.error('Have not found certificate files and can not connect to certificate server (%s): %s' % (cert_server, str(e)))
                    logger.error('Either copy certificate files manually or activate certificate sever.')
                    logger.error('Will silently try to connect to certificate server in 30 second intervals from now on.')

                time.sleep(30)
                continue

            if html != 'This is the Waggle certificate server.':
                if (loop == 0):
                    logger.error(''.join(("Unexpected response from certificate server: ", html)))
                time.sleep(5)
                continue
        else:
            logger.info("All certificate files found.")
            if os.path.isfile(registration_key):
                #os.remove(registration_key)
                # we'll save it in a special subdirectory instead of deleting it, for convenience
                CmdString('mkdir -p {}/registered'.format(dir))
                CmdString('mv {}  {}/registered'.format(registration_key, dir))
            break

        # make sure certficate files exist.
        if not ca_root_file_exists:
            create_dir_for_file(ca_root_file)
            logger.info("trying to get server certificate from certificate server %s..." % (cert_server))
            try:
                html = run_registration_command(registration_key, cert_server, "certca")
            except Exception as e:
                logger.error('Could not connect to certificate server: '+str(e))
                time.sleep(5)
                continue

            if html.startswith( '-----BEGIN CERTIFICATE-----' ) and html.endswith('-----END CERTIFICATE-----'):
                logger.info('certificate downloaded')
            else:
                logger.error('certificate parsing problem')
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('content: '+str(html))
                time.sleep(5)
                continue

            with open(ca_root_file, 'w') as f:
                f.write(html)
            f.close()

            logger.debug("File %s written." % (ca_root_file))

        if not (client_key_file_exists and client_cert_file_exists):
            create_dir_for_file(client_key_file)
            create_dir_for_file(client_cert_file)
            logger.info("trying to get node key and certificate from certificate server %s..." % (cert_server))
            try:
                html = run_registration_command(registration_key, cert_server, "node?%s" % node_id)
            except Exception as e:
                logger.error('Could not connect to certificate server: '+str(e))
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('content: '+str(html))
                time.sleep(5)
                continue
            if 'error: cert file not found' in html:
              raise Exception(''.join(('Node ID ', node_id, ' is already registered but the associated SSL credentials were not found.')))

            priv_key_start = "-----BEGIN RSA PRIVATE KEY-----"
            position_rsa_priv_key_start = html.find(priv_key_start)
            if position_rsa_priv_key_start == -1:
                logger.error("Could not parse PEM data from server. (position_rsa_priv_key_start)")
                time.sleep(5)
                continue
            logger.info("position_rsa_priv_key_start: "+str(position_rsa_priv_key_start))

            priv_key_end = "-----END RSA PRIVATE KEY-----"
            position_rsa_priv_key_end = html.find(priv_key_end)
            if position_rsa_priv_key_end == -1:
                logger.error("Could not parse PEM data from server. (position_rsa_priv_key_end)")
                time.sleep(5)
                continue
            logger.info("position_rsa_priv_key_end: "+str(position_rsa_priv_key_end))

            position_cert_start = html.find("-----BEGIN CERTIFICATE-----")
            if position_cert_start == -1:
                logger.error("Could not parse PEM data from server. (position_cert_start)")
                time.sleep(5)
                continue
            logger.info("position_cert_start: "+str(position_cert_start))

            end_cert = "-----END CERTIFICATE-----"
            position_cert_end = html.find(end_cert)
            if position_cert_end == -1:
                logger.error("Could not parse PEM data from server. (position_cert_end)")
                time.sleep(5)
                continue
            logger.info("position_cert_end: "+str(position_cert_end))

            html_tail = html[position_cert_end+len(end_cert):]

            client_key_string = html[position_rsa_priv_key_start:position_rsa_priv_key_end+len(priv_key_end)]+"\n"
            client_cert_string = html[position_cert_start:position_cert_end+len(end_cert)]+"\n"


            # find port for reverse ssh tunnel
            port_number = re.findall("PORT=(\d+)", html_tail)[0]

            rsa_public_key, rsa_public_key_comment = re.findall("(ssh-rsa \S*)( .*)?", html_tail)[0]

            logger.debug("client_key_file: "+client_key_string)
            logger.debug("client_cert_file: "+client_cert_string)

            logger.debug("PORT: "+str(port_number))


            # write everything to files
            with open(client_key_file, 'w') as f:
                f.write(client_key_string)
            f.close()
            logger.info("File '%s' has been written." % (client_key_file))
            if False:
                subprocess.call(['chown', 'rabbitmq:rabbitmq', client_key_file])
            else:
                print('skipping chown!!!!!!!!!!!!!!')
            os.chmod(client_key_file, 0o600)

            with open(client_cert_file, 'w') as f:
                f.write(client_cert_string)
            f.close()
            if False:
                subprocess.call(['chown', 'rabbitmq:rabbitmq', client_cert_file])
            else:
                print('skipping chown!!!!!!!!!!!!!!')

            os.chmod(client_cert_file, 0o600)

            logger.info("File '%s' has been written." % (client_cert_file))

            with open(reverse_ssh_port_file, 'w') as f:
                f.write(str(port_number))
            f.close()

            logger.info("File '%s' has been written." % (reverse_ssh_port_file))

    # build the ssl_options here while we have them
    ssl_options={'ca_certs':ca_root_file,
        'certfile':client_cert_file,
        'keyfile':client_key_file}
    return ssl_options
    
def DataSerialize(data):
    if isinstance(data, int):
        content_type = 'i'
        body = str(data).encode()
    elif isinstance(data, float):
        content_type = 'f'
        body = str(data).encode()
    elif isinstance(data, str):
        content_type = 's'
        body = data.encode()
    elif isinstance(data, bytearray):
        content_type = 'b'
        body = bytes(data)
    elif isinstance(data, bytes):
        content_type = 'b'
        body = data
    elif isinstance(data, dict) or isinstance(data, list):
        content_type = 'j'
        body = json.dumps(data).encode()
    else:
        raise ValueError('unsupported data type')

    return content_type, body
    
#_______________________________________________________________________
#_______________________________________________________________________
if __name__ == '__main__':
    global verbosity
    
    print('###################################\n')

    # get args
    argParser = argparse.ArgumentParser()
    argParser.add_argument('beehive_url', help = 'url of the beehive to connect')
    argParser.add_argument('node_id', help = 'id of node, eg. 000002000000ffff')
    argParser.add_argument('dir', help = 'directory for storing id files and credentials')
    argParser.add_argument('-create', action='store_true', help = 'creates the directory for credentials')
    argParser.add_argument('--verbose', '-v', action='count')
    args = argParser.parse_args()
    
    verbosity = args.verbose
    beehive_url = args.beehive_url
    node_id = args.node_id
    dir = args.dir
    
    if verbosity: print('args = ', args)
    
    # node_id must be of the form (without spaces)
    #    00 00 02 00 00 00 xx xx
    bValidNodeId = False
    if node_id and len(node_id) == 16:
        node_id = node_id.lower()
        if re.match('^000002000000[0-9a-f]{4}$', node_id):
            print('VALID node_id = {}'.format(node_id))
            bValidNodeId = True
    if not bValidNodeId:
        print('INVALID node_id = {}'.format(node_id))
        sys.exit()
    
    print('args.create = ', args.create)
    if args.create:
        # create directory
        CmdString('mkdir -p {}\n'.format(dir))

        # create server host file
        with open(dir + "/server_host", 'w') as cert_server_file:
            cert_server_file.write(beehive_url + '\n')
            
        # create node_id file
        with open(dir + "/node_id", 'w') as node_id_file:
            node_id_file.write(node_id + '\n')
    
    else:
        # dir must contain the necessary credential files
        bValidDir = False
        if os.path.exists(dir):
            print('dir exists: {}'.format(dir))
            
            # check for all necessary files
            
            bValidDir = True
            
        if not bValidDir:
            print('INVALID dir: {}'.format(dir))
            sys.exit()
    
    # get all the necessary certificate files, etc.
    ssl_options = get_certificates(dir)

    # open a connection
    # URI:    amqps://node:waggle@beehive1.mcs.anl.gov:23181?cacertfile=/usr/lib/waggle/SSL/waggleca/cacert.pem&certfile=/usr/lib/waggle/SSL/node/cert.pem&keyfile=/usr/lib/waggle/SSL/node/key.pem&verify=verify_peer"
    
    credentials = pika.credentials.PlainCredentials('node', 'waggle')
    if False:
        ssl_options={'ca_certs':ca_root_file,
            'certfile':client_cert_file,
            'keyfile':client_key_file}
        
    print('ssl_options = ', ssl_options)
    params = pika.ConnectionParameters(host=beehive_url, 
                    port=23181, 
                    credentials=credentials, 
                    ssl=True, 
                    ssl_options=ssl_options,
                    retry_delay=10,
                    socket_timeout=10)

    print('params = ', params)
    connection = pika.BlockingConnection(params)
    print('connection = ', connection)
    
    channel = connection.channel()
    print('channel = ', channel)
    
    
    if False:   # test message
        properties = pika.BasicProperties(timestamp=int(time.time()))
        print('properties = ', properties)
        
        channel.basic_publish(exchange='logs', 
                        routing_key='', 
                        body='hello world', 
                        properties=properties)
        print('basic_publish completed')
        
    else:   # coresense data
        # TODO get it from a file
        #with open(filename, 'r') as f:
        #   for line in f:
        nSamples = 1
        
        # headers = {'node_id' : node_id}
        for x in range(0, nSamples):
            testData = unhexlify(b'aa40d1fd886442582f336ee9ab008600001814c40e01821a2a02841a292248038201a304851a1401457005820356068202cc078880008100800101000882033809821a450a8680b2809e82a40b842a0e1c220c8200ea0d8252e30e82573f0f827a46108226681382265720860004a3e2b5a11d840a7311b51e850ab201460f1f8602131e626d3415830000001a830051f31c8300015c1983003a6a188380026717830009271b830016b721820a3022820a4b23820a7b24820aa725820ab82689805f03d7004e00000027890000000a800b0000002f55')

            if False:
                content_type, body = DataSerialize(testData)
                print('content_type = ', content_type)
                print('body = ', body)
            else:
                if False:
                    content_type, body = DataSerialize({'test' : x})
                else:
                    content_type, body = DataSerialize(testData)
                    print('content_type = ', content_type)
                    print('body = ', body)

                properties = pika.BasicProperties(
                        reply_to=node_id,   # node_id goes here
                        #headers=headers,
                        delivery_mode=2,
                        timestamp=int(time.time() * 1000),
                        content_type=content_type,
                        type='frame', #sensor,  for raw coresense data, it's "frame"
                        app_id='coresense:3')   # plugin id goes here too

                channel.basic_publish(properties=properties,
                                           exchange='data-pipeline-in',
                                           routing_key=properties.app_id,  # plugin id goes here too
                                           body=body)
    
    print('>>> program ended !!!!')
    
    
    
    
    
    
    
    