from flask import Flask, request, Response
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.json_util import dumps
from bson.objectid import ObjectId
from flask_cors import CORS, cross_origin
import os, sys, logging, json, random
import boto3
import xml.etree.ElementTree as ET

logging.basicConfig(level = logging.DEBUG)

# Make app
print('Making app: ' + __name__)
app = Flask(__name__)
CORS(app)

client = MongoClient(
    os.environ.get('MONGO_HOST') or None,
    username = os.environ.get('MONGO_USER') or None,
    password = os.environ.get('MONGO_PASS') or None
)

logging.info('STARTING WITH MONGO CLIENT: {}'.format(client))
DB = 'mab-survey'

# AWS MTURK CONSTANTS STUFF
# endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
# qualification_complete = '3NM2AQCBQ46EBVNZD083TJFHTYP55Y'
def get_mturk():
    endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'
    qualification_complete = '3UFT0YQ7M29DP46GHV3HV84IY48MSE'
    mturk = boto3.client('mturk', region_name='us-east-1', endpoint_url=endpoint_url)
    return mturk

def get_all_hits(mturk):
    ids = [hit['HITId'] for hit in mturk.list_hits()['HITs']]
    return ids

def get_workers_and_codes(mturk):
    ids = get_all_hits(mturk)
    assignments = [ass for i in ids
               for ass in mturk.list_assignments_for_hit(HITId=i)['Assignments']]
    answers = [a['Answer'] for a in assignments]
    codes = [ET.fromstring(a)[0][1].text for a in answers]
    worker_ids = [a['WorkerId'] for a in assignments]
    assignment_ids = [a['AssignmentId'] for a in assignments]
    return list(zip(worker_ids, codes, assignment_ids))

def get_bonus(collection, code):
    res = collection.find_one({'_id': ObjectId(code)})
    if not res:
        return 0
    box = res['boxes'][-1]
    wins = [1 if o['result'] == 'win' else 0 for o in box]
    return sum(wins)

def get_paid(mturk):
    ids = get_all_hits(mturk)
    bonuses = [mturk.list_bonus_payments(HITId = i)['BonusPayments']
               for i in ids]
    paid = [b['WorkerId'] for i in bonuses for b in i]
    return paid

def need_payment(mturk):
    paid = get_paid(mturk)

    li = [(w, c, a, get_bonus(client[DB].trial, c))
          for w, c, a in get_workers_and_codes(mturk)]

    li = [i for i in li if i[0] not in paid]
    return li

def pay_all(mturk):
    li = need_payment(mturk)
    return [pay_worker(amt,c,w,a) for w,c,a,amt in li]

def pay_worker(amt, code, worker_id, a_id):

    # approve assignment
    try:
        mturk.approve_assignment(AssignmentId=a_id)
    except Exception as e:
        logging.error(e)
        pass

    # associate_qualification_with_worker
    try:
        mturk.associate_qualification_with_worker(
            QualificationTypeId=qualification_complete,
            WorkerId=worker_id
        )
    except Exception as e:
        logging.error(e)
        pass

    # send_bonus
    if amt > 0:
        mturk.send_bonus(
            WorkerId=worker_id,
            BonusAmount='{}'.format(amt),
            AssignmentId=a_id,
            Reason='Survey Completed'
        )

    # Update in our db
    return client[DB].trial.find_one_and_update(
        { '_id': ObjectId(code)},
        {'$set': { 'bonus_paid': amt }}
    )

def needed_treatment(res):
    if not res:
        return random.choice(['a', 'b'])
    if len(res) > 1:
        treat = sorted(res, key = lambda t: t[1])[0][0]
    else:
        treat = 'b' if res[0][0] == 'a' else 'a'
    return treat

def get_next_treatment(collection, version):
    if float(version) >= 0.4:
        treat = '$treatment.ab'
    else:
        treat = '$treatment'
    res = collection.aggregate([
        { '$match': {'version': version}},
        { '$group': { '_id': { 'treatment': treat }, 'count': { '$sum': 1}}}
    ])
    res = [ (d['_id']['treatment'], d['count']) for d in res]
    print(res)
    return needed_treatment(res)

@app.route('/submit', methods=['POST'])
def submit():
    dat = request.json
    collection = client[DB].trial
    db_res = collection.insert_one(dat)
    code = str(db_res.inserted_id)
    res = { 'code': code }
    return Response(json.dumps(res), mimetype='application/json')

@app.route('/treatment', methods=['GET'])
def get_treatment():
    version = request.args.get('version', '0.1')
    collection = client[DB].trial
    treat = get_next_treatment(collection, version)
    res = { 'treatment': treat }
    return Response(json.dumps(res), mimetype='application/json')
