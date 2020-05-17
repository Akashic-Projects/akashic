from flask import Flask, jsonify, request 
from flask_pymongo import PyMongo
from flask_cors import CORS

from bson.json_util import dumps
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from akashic.arules.transpiler import Transpiler
from akashic.ads.data_provider import DataProvider
from akashic.ads.env_provider import EnvProvider


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["MONGO_URI"] = "mongodb://admin:devdevdev@127.0.0.1:27017/akashic?authSource=admin&readPreference=primary&appname=MongoDB%20Compass&ssl=false"
mongo = PyMongo(app)


## DSDS SECTION
#######################################################

@app.route('/dsds', methods=['GET'])
def get_dsds():
  cursors = mongo.db.dsds.find({})
  rules = list(cursors)
  return dumps(rules)

@app.route('/dsds', methods=['POST'])
def create_dsd():
  akashic_dsd = request.json
  # TODO: Syntactic and semnatic check

  # Check if DSD with gven model name already exists
  if mongo.db.dsds.find({'model-name': { '$eq': akashic_dsd['model-name']}}).count() > 0:
    return dumps({"error": "DSD with given model name already exists."})

  dsd_entry = {}
  dsd_entry['dsd-name'] = akashic_dsd['data-source-definition-name']
  dsd_entry['model-name'] = akashic_dsd['model-name']
  dsd_entry['active'] = False
  dsd_entry['dsd'] = akashic_dsd

  mongo.db.dsds.insert_one(dsd_entry)
  return dumps(dsd_entry)

@app.route('/dsds/<string:name>', methods=['PUT'])
def update_dsd(name):
  akashic_dsd = request.json
  dsd_entry = {}
  dsd_entry['dsd-name'] = akashic_dsd['data-source-definition-name']
  dsd_entry['model-name'] = akashic_dsd['model-name']
  dsd_entry['active'] = False
  dsd_entry['dsd'] = akashic_dsd

  mongo.db.dsds.replace_one({"model-name": name}, 
                            dsd_entry)
  return dumps(dsd_entry)

@app.route('/dsds/enable/<string:name>', methods=['PUT'])
def enable_dsd(name):
  result = mongo.db.dsds.find_one_and_update({"model-name": name}, 
                                             {"$set": {"active": True}},
                                             return_document=ReturnDocument.AFTER)
  return dumps(result)

@app.route('/dsds/disable/<string:name>', methods=['PUT'])
def disable_dsd(name):
  result = mongo.db.dsds.find_one_and_update({"model-name": name}, 
                                             {"$set": {"active": False}},
                                             return_document=ReturnDocument.AFTER)
  return dumps(result)

@app.route('/dsds/<string:name>', methods=['DELETE'])
def remove_dsd(name):
  result = mongo.db.dsds.delete_one({"model-name": name})              
  return dumps({"message": "Ok."})


## RULE SECTION
#######################################################

@app.route('/rules', methods=['GET'])
def get_rules():
  cursors = mongo.db.rules.find({})
  rules = list(cursors)
  return dumps(rules)


@app.route('/rules', methods=['POST'])
def create_rule():
  akashic_rule = request.json

  # TODO: Syntactic and semnatic check

  # Check if rule with gven name already exists
  if mongo.db.rules.find({'rule-name': { '$eq': akashic_rule['rule-name']}}).count() > 0:
    return dumps({"error": "Rule with given name already exists."})

  rule_entry = {}
  rule_entry['rule-name'] = akashic_rule['rule-name']
  rule_entry['active'] = False
  rule_entry['rule'] = akashic_rule
  rule_entry['clips_code'] = ""

  mongo.db.rules.insert_one(rule_entry)
  return dumps(rule_entry)

@app.route('/rules/<string:name>', methods=['PUT'])
def update_rule(name):
  akashic_rule = request.json
  rule_entry = {}
  rule_entry['rule-name'] = akashic_rule['rule-name']
  rule_entry['active'] = False
  rule_entry['rule'] = akashic_rule
  rule_entry['clips_code'] = ""

  mongo.db.rules.replace_one({"rule-name": name}, 
                            rule_entry)
  return dumps(rule_entry)

@app.route('/rules/enable/<string:name>', methods=['PUT'])
def enable_rule(name):
  result = mongo.db.rules.find_one_and_update({"rule-name": name}, 
                                             {"$set": {"active": True}},
                                             return_document=ReturnDocument.AFTER)
  return dumps(result)

@app.route('/rules/disable/<string:name>', methods=['PUT'])
def disable_rule(name):
  result = mongo.db.rules.find_one_and_update({"rule-name": name}, 
                                             {"$set": {"active": False}},
                                             return_document=ReturnDocument.AFTER)
  return dumps(result)

@app.route('/rules/<string:name>', methods=['DELETE'])
def remove_rule(name):
  result = mongo.db.rules.delete_one({"rule-name": name})              
  return dumps({"message": "Ok."})


app.run(debug=True)