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


@nodeDash.route('/')
def nodeDash_root():
    location = str(request.args.get('location'))
    status = str(request.args.get('status'))
    cat = str(request.args.get('cat'))
    # table = dashtable(apirequest(api_url), location, status, cat)
    return render_template('base.html')


@nodeDash.route('/server')
def server():
    return render_template('base.html')


@nodeDash.route('/data.tsv')
def data():
    return None


@nodeDash.route('/documentation')
def documentation():
    return render_template('documentation.html')


@nodeDash.route("/test")
def route():
    return "route found."

