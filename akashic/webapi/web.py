from flask import Flask, jsonify, request, Response
from flask_pymongo import PyMongo
from flask_cors import CORS

from bson.json_util import dumps
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from akashic.arules.transpiler import Transpiler
from akashic.ads.data_provider import DataProvider
from akashic.ads.env_provider import EnvProvider

from akashic.exceptions import AkashicError, ErrType

from enum import Enum
from datetime import datetime

class RespType(Enum):
    def __str__(self):
        return str(self.name)

    SUCCESS = 1
    INFO = 2
    ERROR = 3


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["MONGO_URI"] = "mongodb://admin:devdevdev@127.0.0.1:27017/akashic?authSource=admin&readPreference=primary&appname=MongoDB%20Compass&ssl=false"
mongo = PyMongo(app)


## INIT ENV SECTION
#######################################################

@app.before_first_request
def init_akashic():
    global env_provider
    global dsd_providers_dict

    env_provider = EnvProvider()
    dsd_providers_dict = {}

    # Load DSDs

    # Load rules


def get_time():
    now = datetime.now()
    return now.strftime("%m/%d/%Y, %H:%M:%S")

def resp(data, message, ln, col, resp_type):
    status_code = 400
    if resp_type in [RespType.SUCCESS, RespType.INFO]:
        status_code = 200
    
    resp_json = dumps({
        "data": data,
        "meta": {
            "text": message,
            "ln": ln,
            "col": col,
            "type": str(resp_type),
            "timestamp": get_time()
        }
    })
    return Response(
        resp_json, 
        status=status_code, 
        mimetype='application/json'
    )


## DSDS SECTION
#######################################################

@app.route('/dsds', methods=['GET'])
def get_dsds():
    cursors = mongo.db.dsds.find({})
    dsds = list(cursors)

    message = "List of DSDs is successfully loaded."
    return resp(dsds, message, 0, 0, RespType.SUCCESS)



@app.route('/dsds', methods=['POST'])
def create_dsd():
    # Get JSON data
    akashic_dsd = request.json

    # Check is this even exists, prevent: 
    # ---NoneType' object is not subscriptable---

    # Check if DSD with given model-id already exists
    if mongo.db.dsds.count_documents(
            {'model-id': { '$eq': akashic_dsd['model-id']}}) > 0:

        message = "DSD with given model-id already exists."
        return resp(None, message, 0, 0, RespType.ERROR)

    # Create DSD provider -> syntactic and semnatic check
    data_provider = DataProvider()

    try:
        data_provider.load(dumps(akashic_dsd, indent=True))
        data_provider.setup()
    except AkashicError as e:
        return resp(None, e.message, e.line, e.col, RespType.ERROR)
    
    # Add new DSD provider to dict
    dsd_providers_dict[akashic_dsd['model-id']] = data_provider

    # Generate CLIPS tempalte and add it to CLIPS enviroment
    clips_template = data_provider.generate_clips_template()
    env_provider.define_template(clips_template)

    # Add to mongo database
    dsd_entry = {}
    dsd_entry['dsd-name'] = akashic_dsd['data-source-definition-name']
    dsd_entry['model-id'] = akashic_dsd['model-id']
    dsd_entry['active'] = True
    dsd_entry['dsd'] = akashic_dsd
    dsd_entry['clips_code'] = clips_template
    mongo.db.dsds.insert_one(dsd_entry)

    message = "New DSD with model-id '{0}' " \
              "is successfully created." \
              .format(akashic_dsd['model-id'])
    return resp(dsd_entry, message, 0, 0, RespType.SUCCESS)



@app.route('/dsds/<string:old_model_id>', methods=['PUT'])
def update_dsd(old_model_id):
    # Get JSON data
    akashic_dsd = request.json

    # Check if DSD with given model-id exists
    foundDSD = mongo.db.dsds.find_one(
                {'model-id': {'$eq': old_model_id}})

    if not foundDSD:
        message = "DSD with given model-id does not exists."
        return resp(None, message, 0, 0, RespType.ERROR)

    # Create DSD provider -> syntactic and semnatic check
    data_provider = DataProvider()
    data_provider.load(dumps(akashic_dsd))
    data_provider.setup()
    dsd_providers_dict[akashic_dsd['model-id']] = data_provider

    # Remove old DSD provider from dict
    try:
        dsd_providers_dict.pop(old_model_id)    
    except KeyError:
        message = "E345: dsd_providers_dict - " \
                  "entity with given key not found."
        return resp(None, message, 0, 0, RespType.ERROR)

    # Add new DSD provider to dict
    dsd_providers_dict[akashic_dsd['model-id']] = data_provider

    # Remove old CLIPS template from CLIPS env
    env_provider.undefine_template(old_model_id)

    # Generate CLIPS tempalte and add it to CLIPS enviroment
    clips_template = data_provider.generate_clips_template()
    env_provider.define_template(clips_template)
        
    # Create DSD db-entry
    dsd_entry = {}
    dsd_entry['dsd-name'] = akashic_dsd['data-source-definition-name']
    dsd_entry['model-id'] = akashic_dsd['model-id']
    dsd_entry['active'] = foundDSD['active']
    dsd_entry['dsd'] = akashic_dsd

    # Repalce old db-entry
    mongo.db.dsds.replace_one({"model-id": old_model_id}, dsd_entry)

    message = "DSD with model-id '{0}' is successfully updated." \
              .format(old_model_id)
    return resp(dsd_entry, message, 0, 0, RespType.SUCCESS)



@app.route('/dsds/enable/<string:model_id>', methods=['PUT'])
def enable_dsd(model_id):
    result = mongo.db.dsds.find_one_and_update(
                {"model-id": model_id}, 
                {"$set": {"active": True}},
                return_document=ReturnDocument.AFTER
    )

    message = "DSD with model-id '{0}' is " \
              "successfully enabled.".format(model_id)
    return resp(result, message, 0, 0, RespType.SUCCESS)



@app.route('/dsds/disable/<string:model_id>', methods=['PUT'])
def disable_dsd(model_id):
    result = mongo.db.dsds.find_one_and_update(
                {"model-id": model_id}, 
                {"$set": {"active": False}},
                return_document=ReturnDocument.AFTER
    )

    message = "DSD with model-id '{0}' is " \
              "successfully disabled.".format(model_id)
    return resp(result, message, 0, 0, RespType.SUCCESS)



@app.route('/dsds/<string:model_id>', methods=['DELETE'])
def remove_dsd(model_id):
    result = mongo.db.dsds.delete_one({"model-id": model_id})
    
    message = "DSD with model-id '{0}' is " \
              "successfully deleted.".format(model_id)
    return resp(None, message, 0, 0, RespType.SUCCESS)



## RULE SECTION
#######################################################

@app.route('/rules', methods=['GET'])
def get_rules():
    cursors = mongo.db.rules.find({})
    rules = list(cursors)

    message = "List of rules is successfully loaded."
    return resp(rules, message, 0, 0, RespType.SUCCESS)



@app.route('/rules', methods=['POST'])
def create_rule():
    akashic_rule = request.json

    # TODO: Syntactic and semnatic check

    # Check if rule with gven name already exists
    if mongo.db.rules.count_documents(
            {'rule-name': { '$eq': akashic_rule['rule-name']}}) > 0:
        
        message = "Rule with given rule-name already exists."
        return resp(None, message, 0, 0, RespType.ERROR)

    rule_entry = {}
    rule_entry['rule-name'] = akashic_rule['rule-name']
    rule_entry['active'] = False
    rule_entry['rule'] = akashic_rule
    rule_entry['clips_code'] = ""

    mongo.db.rules.insert_one(rule_entry)
    
    message = "New rule with rule-name '{0}' is successfully created." \
              .format(akashic_rule['rule-name'])
    return resp(rule_entry, message, 0, 0, RespType.SUCCESS)



@app.route('/rules/<string:old_rule_name>', methods=['PUT'])
def update_rule(old_rule_name):
    # Get JSON data
    akashic_rule = request.json

    # Check if DSD with given model-id exists
    foundRule = mongo.db.rules.find_one({'rule-name': {'$eq': old_rule_name}})
    if not foundRule:

        message = "Rule with given rule-name does not exists."
        return resp(None, message, 0, 0, RespType.ERROR)

    # Create DSD db-entry
    rule_entry = {}
    rule_entry['rule-name'] = akashic_rule['rule-name']
    rule_entry['active'] = foundRule['active']
    rule_entry['rule'] = akashic_rule
    rule_entry['clips_code'] = ""

    # Replace old db-entry
    mongo.db.rules.replace_one({"rule-name": old_rule_name}, rule_entry)

    message = "Rule with rule-name '{0}' is successfully updated." \
              .format(old_rule_name)
    return resp(rule_entry, message, 0, 0, RespType.SUCCESS)



@app.route('/rules/enable/<string:rule_name>', methods=['PUT'])
def enable_rule(rule_name):
    result = mongo.db.rules.find_one_and_update(
                {"rule-name": rule_name}, 
                {"$set": {"active": True}},
                return_document=ReturnDocument.AFTER
    )

    message = "Rule with rule-name '{0}' is successfully enabled." \
              .format(rule_name)
    return resp(result, message, 0, 0, RespType.SUCCESS)



@app.route('/rules/disable/<string:rule_name>', methods=['PUT'])
def disable_rule(rule_name):
    result = mongo.db.rules.find_one_and_update(
                {"rule-name": rule_name}, 
                {"$set": {"active": False}},
                return_document=ReturnDocument.AFTER
    )

    message = "Rule with rule-name '{0}' is successfully disabled." \
              .format(rule_name)
    return resp(result, message, 0, 0, RespType.SUCCESS)



@app.route('/rules/<string:rule_name>', methods=['DELETE'])
def remove_rule(rule_name):
    result = mongo.db.rules.delete_one({"rule-name": rule_name})              
    
    message = "Rule with rule-name '{0}' is successfully deleted." \
              .format(rule_name)
    return resp(None, message, 0, 0, RespType.SUCCESS)


app.run(debug=True)