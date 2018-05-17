from flask import Flask, request, Response
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.json_util import dumps
from flask_cors import CORS, cross_origin
import os, sys, logging, json
import logging
import boto3

# Make app
print('Making app: ' + __name__)
app = Flask(__name__)
CORS(app)

client = MongoClient(
    os.environ.get('MONGO_HOST') or None,
    username = os.environ.get('MONGO_USER') or None,
    password = os.environ.get('MONGO_PASS') or None
)

DB = 'mab-survey'

# DO SOME AUTOMATED MTURK SHIT
# @app.route('/foo', methods=['GET'])
# def foo():
#     session = boto3.Session(profile_name='bgse-us') # get rid of profile...
#     client = session.client('mturk')
#     res = client.list_hits()
#     return Response(json.dumps(res), mimetype='application/json')

@app.route('/submit', methods=['POST'])
def submit():
    dat = request.json
    collection = client[DB].trial
    res = collection.insert_one(dat)
    res = { 'code': str(res.inserted_id) }
    return Response(json.dumps(res), mimetype='application/json')
