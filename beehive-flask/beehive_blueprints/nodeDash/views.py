from . import nodeDash
from flask import Flask, render_template, url_for, request, Response
import time
import json
import requests
import csv
import datetime

api_url = 'http://127.0.0.1:4000'  # The url of the API for the node dashboard.
key_list = ["id", "location", "alive", "lastupdate"]  # A list of keys of relevant incoming JSON data.
fieldNames = ["time", "< One Minute", "< Five Minutes", "< Thirty Minutes", "< One Hour", "< Six Hours",
              "< One Day", "> One Day"]


def apirequest(url):
    # TODO: Add a function that changes the input data to properly formatted data.
    """
    This function sends a request to an api, and then converts the received data into JSON.
    :param url: The url of the chosen api.
    :return: The received data in JSON format.
    """
    req = requests.get(url)
    json_data = req.json()
    # return jsonformat(json_data, 1800)  # bin length is in seconds. from 1800- 100000

    # print(json_data)
    return json_data


def jsonformat(json_data, binlength):
    # TODO: document this! It's like the most important part!

    # First we build the bins
    # -----------------------
    stamplist = []
    timeDict = {}
    timeMax = 0
    timeMin = 0
    for line in json_data:
        timestamp = float(line)
        if timeMax == 0:
            timeMin = timestamp
        if timestamp > timeMax:
            timeMax = timestamp
        if timestamp < timeMin:
            timeMin = timestamp
    duration = timeMax - timeMin
    binNum = duration // binlength
    binlength = duration / binNum
    endpoint = timeMin
    for bin in range(int(binNum)):
        tempList = []
        for timestamp in json_data:
            convtimestamp = float(timestamp)
            if endpoint <= convtimestamp < (endpoint + binlength):
                tempList.append(json_data.get(timestamp))
        timeDict[endpoint] = tempList
        endpoint = endpoint + binlength

    # Then we give each node just one value in each bin
    # -------------------------------------------------
    for bin in timeDict:
        nodeDict = {}
        for group in timeDict.get(bin):
            for node in group:
                nodeDict.get(node)
                nodeDict[node] = {'uptime': group.get(node).get('uptime')}
                # print(node)
                # print(group.get(node).get('uptime'))
        # print(nodeDict)
        timeDict[bin] = nodeDict
    # print(timeDict)
    return timeDict


@nodeDash.route('/')
def nodeDash_root():
    location = str(request.args.get('location'))
    status = str(request.args.get('status'))
    cat = str(request.args.get('cat'))
    # table = dashtable(apirequest(api_url), location, status, cat)
    apidata = [
        {
            'alive': 1, "location": 'Chicago', 'id': 100001, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'New York', 'id': 100010, "lastupdate": "Mon Aug 10 09:17:11 2016"
        },
        {
            'alive': 1, "location": 'Minneapolis', 'id': 100011, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Los Angeles', 'id': 100100, "lastupdate": "Thurs May 2 22:01:57 2017"
        },
        {
            "location": "Munich", "id": 100101, "alive": 1, "lastupdate": str(time.asctime())
        },
        {
            "alive": 1, "id": 100110, "location": "Budapest", "lastupdate": str(time.asctime())
        },
        {
            'alive': 1, "location": 'Phoenix', 'id': 100111, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Kansas City', 'id': 101000, "lastupdate": "Mon Aug 10 09:17:11 2016"
        },
        {
            'alive': 1, "location": 'Saint Paul', 'id': 101001, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Boston', 'id': 101010, "lastupdate": "Thurs May 2 22:01:57 2017"
        },
        {
            "location": "Dallas", "id": 101011, "alive": 1, "lastupdate": str(time.asctime())
        },
        {
            "alive": 1, "id": 101100, "location": "Toronto", "lastupdate": str(time.asctime())
        },
        {
            'alive': 1, "location": 'Chicago', 'id': 100001, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'New York', 'id': 100010, "lastupdate": "Mon Aug 10 09:17:11 2016"
        },
        {
            'alive': 1, "location": 'Minneapolis', 'id': 100011, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Los Angeles', 'id': 100100, "lastupdate": "Thurs May 2 22:01:57 2017"
        },
        {
            "location": "Munich", "id": 100101, "alive": 1, "lastupdate": str(time.asctime())
        },
        {
            "alive": 1, "id": 100110, "location": "Budapest", "lastupdate": str(time.asctime())
        },
        {
            'alive': 1, "location": 'Phoenix', 'id': 100111, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Kansas City', 'id': 101000, "lastupdate": "Mon Aug 10 09:17:11 2016"
        },
        {
            'alive': 1, "location": 'Saint Paul', 'id': 101001, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Boston', 'id': 101010, "lastupdate": "Thurs May 2 22:01:57 2017"
        },
        {
            "location": "Dallas", "id": 101011, "alive": 1, "lastupdate": str(time.asctime())
        },
        {
            "alive": 1, "id": 101100, "location": "Toronto", "lastupdate": str(time.asctime())
        },
        {
            'alive': 1, "location": 'Chicago', 'id': 100001, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'New York', 'id': 100010, "lastupdate": "Mon Aug 10 09:17:11 2016"
        },
        {
            'alive': 1, "location": 'Minneapolis', 'id': 100011, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Los Angeles', 'id': 100100, "lastupdate": "Thurs May 2 22:01:57 2017"
        },
        {
            "location": "Munich", "id": 100101, "alive": 1, "lastupdate": str(time.asctime())
        },
        {
            "alive": 1, "id": 100110, "location": "Budapest", "lastupdate": str(time.asctime())
        },
        {
            'alive': 1, "location": 'Phoenix', 'id': 100111, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Kansas City', 'id': 101000, "lastupdate": "Mon Aug 10 09:17:11 2016"
        },
        {
            'alive': 1, "location": 'Saint Paul', 'id': 101001, "lastupdate": str(time.asctime())
        },
        {
            'alive': 0, "location": 'Boston', 'id': 101010, "lastupdate": "Thurs May 2 22:01:57 2017"
        },
        {
            "location": "Dallas", "id": 101011, "alive": 1, "lastupdate": str(time.asctime())
        },
        {
            "alive": 1, "id": 101100, "location": "Toronto", "lastupdate": str(time.asctime())
        }
    ]
    datatable = dashtable(apidata, location, status, cat)
    return render_template('dashboard.html', dashtable=datatable)


def dashtable(data, argloc, argstat, argcat):
    """
    This function generates a table based on the JSON data received from the api.
    The table headers must be updated manually to match any new figures.
    :param data: This is JSON data passed in the DASHBOARD function from the APIREQUEST function.
    :param argloc: location arg
    :param argstat: status arg (1 or 0 >> Alive or Dead)
    :return: A string of HTML code that generates a readable table of data.
    """

    # print(argloc)
    # print(argcat)
    testData = filterdata(data, argloc, argstat, argcat)
    # testData = data
    tbl = []

    # This section generates the table headers.
    # This must be manually updated when new columns are to be introduced.
    tbl.append("<tr>")
    tbl.append("<th style='cursor: pointer;'>Node ID</th>")
    tbl.append("<th style='cursor: pointer;'>Location</th>")
    tbl.append("<th style='cursor: pointer;'>Status</th>")
    tbl.append("<th style='cursor: pointer;'>Last Update</th>")
    tbl.append("</tr>")

    # This section generates a table that has as many rows as there are nodes, and as many columns as there are elements
    # in the KEY_LIST variable instantiated at the top of the file.
    for i in testData:
        tbl.append("<tr>")
        for j in key_list:
            if j == "alive":
                if i.get(j) == 0:
                    tbl.append("<td bgcolor='red'>")
                    tbl.append("Dead")
                else:
                    tbl.append("<td bgcolor='green'>")
                    tbl.append("Alive")
            else:
                tbl.append("<td>")
                tbl.append(str(i.get(j)))
            tbl.append("</td>")
        tbl.append("</tr>")
    return ''.join(tbl)  # This returns a single string of HTML code, which will produce the table.


def filterdata(data, location, status, cat):
    # TODO: Make this function actually usefully filter the data in a way the user may want.
    """
    The purpose of this function is to filter the data being provided to the table so that only the data chosen by the
    the user is displayed
    :param data: raw, unfiltered JSON data used to populate the table
    :param location: location specification
    :param status: 1 or 0 corresponds to alive and dead.
    :return: filtered data
    """
    fildata = data
    # for row in fildata:
    #     # TODO: For some reason, I can't filter out cat if it's equal to None.
    #     if cat != "" and cat != "None" and cat is not None:
    #         cat = int(cat)
    #         print(cat)
    #         if cat == 1:
    #             print("cat1")
    #         elif cat == 2:
    #             print("cat2")
    #         elif cat == 3:
    #             print("cat3")
    #         elif cat == 4:
    #             print("cat4")
    #         elif cat == 5:
    #             print("cat5")
    #         elif cat == 6:
    #             print("cat6")
    #         if cat == 7:
    #             print("cat7")
    #     if status != "" and status != "None" and status is not None:
    #         if status == "alive":
    #             if row.get('alive') == 1 or row.get("alive") == 1:
    #                 print(row)
    #                 fildata.remove(row)
    #
    #     if int(row.get('id')) == 1000010:
    #
    #         fildata.remove(row)
    return fildata


@nodeDash.route('/server')
def server():
    global binlength
    binlength = request.args.get('bin', 30, int)*60
    if 1800 > binlength:
        binlength = 1800
    elif binlength > 86400:
        binlength = 86400
    # serverTable = servertable()
    return render_template('serverdash.html', serverlog=serverlog())


def serverlog():
    tbl = []
    for x in range(100, 0, -1):
        tbl.append("<tr>")
        tbl.append("<td> Data Received " + str(x) + "</td>")
        tbl.append("</tr>")
    return ''.join(tbl)


@nodeDash.route('/data.tsv')
def data():
    return open("beehive_blueprints/" + url_for('nodeDash.static', filename='temp.csv')).read()
    # return open('/usr/lib/waggle/beehive-server/beehive-flask/beehive_blueprints/nodeDash/static/temp.csv').read()


@nodeDash.route('/documentation')
def documentation():
    return render_template('documentation.html')


@nodeDash.route('/node/<nodeID>')
def showNodePage(nodeID):
    nodeTable = []
    # nodeTable.append(<tr)
    for x in range(100):
        nodeTable.append("<tr><td>" + str(x) + "</td></tr>")
    joinedTbl = ''.join(nodeTable)
    return render_template('base.html', nodeTable=joinedTbl)
