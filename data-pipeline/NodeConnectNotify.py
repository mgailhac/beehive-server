#!/usr/bin/env python3

import argparse
import datetime
import json
import logging
import requests
import subprocess
import sys
import time
#logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.CRITICAL)

logger = logging.getLogger('beehive-node-control-notify')
logger.setLevel(logging.DEBUG)

""" Check last update of all nodes - update OFFLINE info
    infer a state from that (recently communicating or not)
    when the state changes, send a slack message and log the message to a node-specific file
"""
#_______________________________________________________________________
# Run a command and capture it's output
def Cmd(command, bPrint = False):
    if bPrint:
        print(' CMD:  ', command)
        
    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  shell = True,
                                  universal_newlines = True)
    #return iter(p.stdout.readline, b'')
    return p.stdout
#_______________________________________________________________________
if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument('--verbose', '-v', action = 'count')
    argParser.add_argument('-debug', action = 'store_true')
    argParser.add_argument('-q', '--quiet', action = 'store_true', help = 'does not transmit messages to slack or to logfile')
    args = argParser.parse_args()
    verbosity = 0 if not args.verbose else args.verbose
    if verbosity: print('args =', args)

    if args.debug: # debug values for rapid iteration
        timedeltaDataMax = datetime.timedelta(seconds = 10)
        timedeltaSshMax = datetime.timedelta(seconds = 13)
        sleepSeconds = 10
        web_url = 'http://beehive1.mcs.anl.gov/'   # for running from outside machine
        #web_url = 'http://localhost:/'      # for on beehive server
        logFilePath = '/home/wcatino/node-logs/'
    else:
        timedeltaDataMax = datetime.timedelta(minutes = 10)
        timedeltaSshMax = datetime.timedelta(minutes = 30)
        sleepSeconds = 300
        web_url = 'http://localhost:/'
        logFilePath = '/mnt/beehive/node-logs/'
        
    stateCurrent = {}
    statePrev = {}

    # all the types of last_update information and the api call to get them
    dataSets = [('lastData', 'nodes_last_data'), ('lastSsh', 'nodes_last_ssh'), ('offline', 'nodes_offline')]
    events = {
        'data' : {
            True :  (':white_check_mark: :chart_with_upwards_trend:', 
                       'data up  :   Node {}'),
            False : (':x: :chart_with_upwards_trend:', 
                       'data down:   Node {}')
        },
        'ssh' : {
            True :  (':white_check_mark: :shell:', 
                        'SSH up  :   Node {}'),
            False : (':x: :shell:', 
                        'SSH down:   Node {}')
        },
        'online' : {
            True :  (':white_check_mark: :electric_plug:', 
                        'ONline   :  Node {}'),
            False : (':x: :electric_plug:', 
                        'OFFline  :  Node {}')
        }
    }
    
    # make sure the directory full of logfiles exists
    Cmd('mkdir -p ' + logFilePath)
    
    bFirstIteration = True
    while True:
        tStart = datetime.datetime.utcnow()
        tStartString = tStart.strftime("%Y-%m-%d %H:%M:%S")
        if verbosity: print('starting node status at UTC', tStartString)

        statePrev = stateCurrent
        stateCurrent = {}

        notifications = []  # list of notifications
        
        # load the list of nodes
        r = requests.get(web_url + 'api/1/nodes')
        node_full_info = json.loads(r.text)['data']
        nodes_list = {x : node_full_info[x].get('name', '') for x in node_full_info}
        if verbosity > 1: print(json.dumps(nodes_list, indent = 4))
        
        # load the webpage just to force the update of the OFFLINE state
        webpage = Cmd('curl ' + web_url)
        for line in webpage:
            pass            # consume every line, or don't move on
       
        D = {}  # capital 'D' for Dictionary, the big one with all the data in it!
        
        # load all the last_update information
        for ds in dataSets:
            url = '{}api/1/{}/'.format(web_url, ds[1])
            r = requests.get(url)
            D[ds[0]] = json.loads(r.text)
            
        if verbosity > 1: print(json.dumps(D, indent = 4))
        
        # convert all timestamps to datetime's
        for dataSet in D:
            d = D[dataSet]
            for node in d:
                d[node] = datetime.datetime.utcfromtimestamp(float(d[node]) / 1000.0)
                if verbosity > 1: print(dataSet, node, d[node])

        # compute current state of things
        for node_id in nodes_list:
            if verbosity > 1: print(node_id)
            stateCurrent[node_id] = d = {}
                            
            # compute state of data flow:
            if node_id not in D['lastData'] or tStart - D['lastData'][node_id] > timedeltaDataMax:
                d['data'] = False   # data not flowing
            else:
                d['data'] = True    # data is flowing
                
            # compute state of ssh:
            if node_id not in D['lastSsh'] or tStart - D['lastSsh'][node_id] > timedeltaSshMax:
                d['ssh'] = False   # ssh not connected
            else:
                d['ssh'] = True    # ssh is connected
            
            # compute state of OFFLINE - use True to mean ONline:
            if node_id in D['offline']:
                d['online'] = False   # NOT online
            else:
                d['online'] = True    # online

        # compare the current state to the previous state, and queue up the appropriate notifications
        for node_id in nodes_list:
        
            nodeNotifications = []
            bHaveNotifications = False
            # if the node does not exist in the previousState, put it there with all False's
            if node_id not in statePrev:
                statePrev[node_id] = {'data' : False, 'ssh' : False, 'online' : False}

            for et in events:
                if statePrev[node_id][et] != stateCurrent[node_id][et]:
                    cur = stateCurrent[node_id][et]   # True or False - the current state
                    nodeNotifications.append((et,cur))
                    bHaveNotifications = True
                    
            # send all notifications for this node
            if bHaveNotifications and not bFirstIteration:
                # slack
                msgLines = []
                for n in nodeNotifications:
                    e = events[n[0]][n[1]]
                    strNode = "'{}' ({})".format(node_id, nodes_list[node_id])
                    msgLines.append('"{} {}  at {}"'.format(e[0], e[1].format(strNode), tStartString))  # concatenate the emoji and the text
                msg = '\n'.join(msgLines)
                if not args.quiet: 
                    Cmd('/bin/slack-ops ' + msg)
                if verbosity: print('SLACK: ' + msg)
                
                # log-file
                msgLines = []
                for n in nodeNotifications:
                    e = events[n[0]][n[1]]
                    strNode = '{} ({})'.format(node_id, nodes_list[node_id])
                    msgLines.append(tStartString + '  ' + e[1].format(strNode) + '\n')  # send just the text
                msg = ''.join(msgLines)
                if verbosity: print('LOGFILE: ' + msg)
                
                if not args.quiet: 
                    with open(logFilePath + node_id, 'a') as f:
                        f.write(msg)
        
        tEnd = datetime.datetime.utcnow()
        dtProcess = tEnd - tStart
        if verbosity: print('finished an iteration of notifications in ', dtProcess)
        if verbosity: print(tEnd, '  sleeping {}s ...'.format(sleepSeconds))
        
        time.sleep(sleepSeconds)
        bFirstIteration = False
        
