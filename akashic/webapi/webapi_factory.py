import hashlib
from enum import Enum
from datetime import datetime

from flask import Flask, jsonify, request, Response
from flask_pymongo import PyMongo
from flask_cors import CORS

from bson.json_util import dumps, loads
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from akashic.arules.transpiler import Transpiler
from akashic.ads.data_provider import DataProvider
from akashic.ads.env_provider import EnvProvider

from akashic.exceptions import AkashicError, ErrType


class RespType(Enum):
    def __str__(self):
        return str(self.name)

    SUCCESS = 1
    INFO = 2
    ERROR = 3



def webapi_factory(mongo_uri, custom_bridges=[]):
    custom_bridges = custom_bridges

    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config["MONGO_URI"] = mongo_uri
    mongo = PyMongo(app)

    global env_provider
    env_provider = EnvProvider(custom_bridges)
    
    global all_templates_loaded
    global all_rules_loaded
    all_templates_loaded = False
    all_rules_loaded = False



    def get_time():
        now = datetime.now()
        return now.strftime("%d.%m.%Y. %H:%M:%S")



    def response(data, message, ln, col, resp_type):
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


### DSDS SECTION
#######################################################

    @app.route('/dsds', methods=['GET'])
    def get_dsds():
        cursors = mongo.db.dsds.find({})
        dsds = list(cursors)

        message = "List of DSDs is successfully queried."
        return response(dsds, message, 0, 0, RespType.SUCCESS)



    @app.route('/dsds', methods=['POST'])
    def create_dsd():
        # Get JSON data
        akashic_dsd = request.json

        # Check if DSD with given model-id already exists
        if mongo.db.dsds.count_documents(
        {'model-id': { '$eq': akashic_dsd['model-id']}}) > 0:
            message = "DSD with given model-id already exists."
            return response(None, message, 0, 0, RespType.ERROR)

        # Create DSD provider -> syntactic and semnatic check
        # Add data_provider to env_provider
        data_provider = DataProvider(env_provider)
        try:
            data_provider.load(dumps(akashic_dsd, indent=True))
            data_provider.setup()
            env_provider.insert_data_provider(data_provider)
        except AkashicError as e:
            return response(
                akashic_dsd, e.message, e.line, e.col, RespType.ERROR)

        # Add to mongo database
        dsd_entry = {}
        dsd_entry['dsd-name'] = akashic_dsd['data-source-definition-name']
        dsd_entry['model-id'] = akashic_dsd['model-id']
        dsd_entry['dsd'] = akashic_dsd
        dsd_entry['clips_code'] = data_provider.clips_template
        mongo.db.dsds.insert_one(dsd_entry)

        message = "New DSD with model-id '{0}' " \
                  "is successfully created." \
                  .format(akashic_dsd['model-id'])
        return response(dsd_entry, message, 0, 0, RespType.SUCCESS)



    @app.route('/dsds/<string:old_model_id>', methods=['PUT'])
    def update_dsd(old_model_id):
        # Get JSON data
        akashic_dsd = request.json

        # Check if DSD with given model-id exists
        foundDSD = mongo.db.dsds.find_one(
            {'model-id': {'$eq': old_model_id}})

        if not foundDSD:
            message = "DSD with given model-id does not exists."
            return response(None, message, 0, 0, RespType.ERROR)

        # Remove data provider from env_provider
        try:
            env_provider.remove_data_provider(old_model_id)
        except AkashicError as e:
            return response(
                None, e.message, e.line, e.col, RespType.ERROR)

        # Create new DSD provider -> syntactic and semnatic check
        # Add data_provider to env_provider
        data_provider = DataProvider(env_provider)
        try:
            data_provider.load(dumps(akashic_dsd, indent=True))
            data_provider.setup()
            env_provider.insert_data_provider(data_provider)
        except AkashicError as e:
            # Reinsert deleted DSD:
            data_provider = DataProvider(env_provider)
            try:
                data_provider.load(dumps(foundDSD["dsd"], indent=True))
                data_provider.setup()
                env_provider.insert_data_provider(data_provider)
            except AkashicError as e:                
                return response(
                    akashic_dsd, e.message, e.line, e.col, RespType.ERROR)

            return response(
                akashic_dsd, e.message, e.line, e.col, RespType.ERROR)
            
        # Create DSD db-entry
        dsd_entry = {}
        dsd_entry['dsd-name'] = akashic_dsd['data-source-definition-name']
        dsd_entry['model-id'] = akashic_dsd['model-id']
        dsd_entry['dsd'] = akashic_dsd
        dsd_entry['clips_code'] = data_provider.clips_template

        # Repalce old db-entry
        mongo.db.dsds.replace_one({"model-id": old_model_id}, dsd_entry)

        message = "DSD with model-id '{0}' is successfully updated." \
                  .format(old_model_id)
        return response(dsd_entry, message, 0, 0, RespType.SUCCESS)



    @app.route('/dsds/<string:model_id>', methods=['DELETE'])
    def remove_dsd(model_id):
        # Remove data provider from env_provider
        try:
            env_provider.remove_data_provider(model_id)
        except AkashicError as e:
            return response(
                None, e.message, e.line, e.col, RespType.ERROR)

        result = mongo.db.dsds.delete_one({"model-id": model_id})

        message = "DSD with model-id '{0}' is successfully deleted." \
                  .format(model_id)
        return response(None, message, 0, 0, RespType.SUCCESS)



## RULE SECTION
#######################################################

    @app.route('/rules', methods=['GET'])
    def get_rules():
        cursors = mongo.db.rules.find({})
        rules = list(cursors)

        message = "List of rules is successfully queried."
        return response(rules, message, 0, 0, RespType.SUCCESS)


    
    @app.route('/rules', methods=['POST'])
    def create_rule():
        akashic_rule = request.json

        is_run_once_rule = False
        # Check if rule is one time rule,
        # if yes, skip DB checks and adding to DB
        # Check if rule with given name already exists
        if mongo.db.rules.count_documents(
        {'rule-name': { '$eq': akashic_rule['rule-name']}}) > 0:
            foundRule = mongo.db.rules.find_one(
                {'rule-name': {'$eq': akashic_rule['rule-name']}})

            if foundRule["hash"] == \
            hashlib.sha256(dumps(akashic_rule, indent=True) \
            .encode('utf-8')).hexdigest() and \
            ("run-once" in akashic_rule) and \
            akashic_rule["run-once"]:
                is_run_once_rule = True
            else:
                message = "Rule with given rule-name already exists."
                return response(None, message, 0, 0, RespType.ERROR)

        # Add rule to env_provider
        transpiler = Transpiler(env_provider)
        try:
            transpiler.load(dumps(akashic_rule, indent=True))
            env_provider.insert_rule(transpiler.rule.rule_name, 
                                     transpiler.tranpiled_rule)
        except AkashicError as e:
            return response(
                akashic_rule, e.message, e.line, e.col, RespType.ERROR)

        rule_entry = None
        if not is_run_once_rule:
            rule_entry = {}
            rule_entry['rule-name'] = akashic_rule['rule-name']
            rule_entry['active'] = True
            rule_entry['rule'] = akashic_rule
            rule_entry['clips_code'] = transpiler.tranpiled_rule
            rule_entry['hash'] = hashlib.sha256(dumps(akashic_rule, indent=True) \
                                .encode('utf-8')).hexdigest()

            mongo.db.rules.insert_one(rule_entry)
        
        message = "New rule with rule-name '{0}' is successfully created." \
                  .format(akashic_rule['rule-name'])
        return response(rule_entry, message, 0, 0, RespType.SUCCESS)



    @app.route('/rules/<string:old_rule_name>', methods=['PUT'])
    def update_rule(old_rule_name):
        # Get JSON data
        akashic_rule = request.json

        # Check if DSD with given model-id exists
        foundRule = mongo.db.rules.find_one(
            {'rule-name': {'$eq': old_rule_name}})
        if not foundRule:
            message = "Rule with given rule-name does not exists."
            return response(None, message, 0, 0, RespType.ERROR)

        # Remove old rule from env_provider
        try:
            env_provider.remove_rule(old_rule_name)
        except AkashicError as e:
            if not foundRule["rule"]["run-once"]:
                return response(
                    None, e.message, e.line, e.col, RespType.ERROR)
            else:
                pass

        # Insert updated rule into env_provider
        # Add rule to env_provider
        transpiler = Transpiler(env_provider)
        try:
            transpiler.load(dumps(akashic_rule, indent=True))
            env_provider.insert_rule(transpiler.rule.rule_name, 
                                    transpiler.tranpiled_rule)
        except AkashicError as e:
            # Reinsert deleted RULE:
            transpiler = Transpiler(env_provider)
            try:
                transpiler.load(dumps(foundRule["rule"], indent=True))
                env_provider.insert_rule(transpiler.rule.rule_name, 
                                        transpiler.tranpiled_rule)
            except AkashicError as e:
                return response(
                    akashic_rule, e.message, e.line, e.col, RespType.ERROR)
            return response(
                akashic_rule, e.message, e.line, e.col, RespType.ERROR)

        # Create DSD db-entry
        rule_entry = {}
        rule_entry['rule-name'] = akashic_rule['rule-name']
        if foundRule["rule"]["run-once"]:
            rule_entry['active'] = True
        else:
            rule_entry['active'] = foundRule['active']
        rule_entry['rule'] = akashic_rule
        rule_entry['clips_code'] = transpiler.tranpiled_rule
        rule_entry['hash'] = hashlib.sha256(dumps(akashic_rule, indent=True) \
                            .encode('utf-8')).hexdigest()

        # Replace old db-entry
        mongo.db.rules.replace_one(
            {"rule-name": old_rule_name}, rule_entry)

        message = "Rule with rule-name '{0}' is successfully updated." \
                  .format(old_rule_name)
        return response(rule_entry, message, 0, 0, RespType.SUCCESS)



    @app.route('/rules/enable/<string:rule_name>', methods=['PUT'])
    def enable_rule(rule_name):
        foundRule = mongo.db.rules.find_one(
            {'rule-name': {'$eq': rule_name}})
        if not foundRule:
            message = "Rule with given rule-name does not exists."
            return response(None, message, 0, 0, RespType.ERROR) 

        # Insert updated rule into env_provider
        # Add rule to env_provider
        transpiler = Transpiler(env_provider)
        try:
            transpiler.load(dumps(foundRule["rule"], indent=True))
            env_provider.insert_rule(transpiler.rule.rule_name, 
                                    transpiler.tranpiled_rule)
        except AkashicError as e:
            return response(
                None, e.message, e.line, e.col, RespType.ERROR)

        result = mongo.db.rules.find_one_and_update(
            {"rule-name": rule_name}, 
            {"$set": {"active": True}},
            return_document=ReturnDocument.AFTER
        )

        message = "Rule with rule-name '{0}' is successfully enabled." \
                  .format(rule_name)
        return response(result, message, 0, 0, RespType.SUCCESS)



    @app.route('/rules/disable/<string:rule_name>', methods=['PUT'])
    def disable_rule(rule_name):
        foundRule = mongo.db.rules.find_one(
            {'rule-name': {'$eq': rule_name}})
        if not foundRule:
            message = "Rule with given rule-name does not exists."
            return response(None, message, 0, 0, RespType.ERROR) 

        try:
            env_provider.remove_rule(rule_name)
        except AkashicError as e:
            if not foundRule["rule"]["run-once"]:
                return response(
                    None, e.message, e.line, e.col, RespType.ERROR)
            else:
                pass

        result = mongo.db.rules.find_one_and_update(
                    {"rule-name": rule_name}, 
                    {"$set": {"active": False}},
                    return_document=ReturnDocument.AFTER
        )

        message = "Rule with rule-name '{0}' is successfully disabled." \
                  .format(rule_name)
        return response(result, message, 0, 0, RespType.SUCCESS)



    @app.route('/rules/<string:rule_name>', methods=['DELETE'])
    def remove_rule(rule_name):
        foundRule = mongo.db.rules.find_one(
            {'rule-name': {'$eq': rule_name}})
        if not foundRule:
            message = "Rule with given rule-name does not exists."
            return response(None, message, 0, 0, RespType.ERROR)            
        
        try:
            env_provider.remove_rule(rule_name)
        except AkashicError as e:
            if not foundRule["rule"]["run-once"]:
                return response(
                    None, e.message, e.line, e.col, RespType.ERROR)
            else:
                pass

        result = mongo.db.rules.delete_one({"rule-name": rule_name})  

        message = "Rule with rule-name '{0}' is successfully deleted." \
                .format(rule_name)
        return response(None, message, 0, 0, RespType.SUCCESS)

   

#### ENGINE FUNCS SECTION
    @app.route('/run', methods=['GET'])
    def run():        
        try:
            env_provider.run()
        except AkashicError as e:
            return response(
                None, e.message, e.line, e.col, RespType.ERROR)

        return_data_array = []
        for ret in env_provider.return_data:
            return_data_array.append(loads(ret))
                
        message = "Engine has finished inference process."
        return response(return_data_array, message, 0, 0, RespType.SUCCESS)

    

    @app.route('/load-all-templates', methods=['POST'])
    def load_all_templates():
        global all_templates_loaded
        if all_templates_loaded:
            message = "All templates are already loaded."
            return response(None, message, 0, 0, RespType.INFO)
        all_templates_loaded = True

        # Insert DSDs from database
        cursors = mongo.db.dsds.find({})
        dsds = list(cursors)

        for akashic_dsd in dsds:
            data_provider = DataProvider(env_provider)
            try:
                data_provider.load(dumps(akashic_dsd["dsd"], indent=True))
                data_provider.setup()
                env_provider.insert_data_provider(data_provider)
            except AkashicError as e:
                return response(
                    None, e.message, e.line, e.col, RespType.ERROR)

        message = "Engine has finished loading templates " \
                  "from database."
        return response(None, message, 0, 0, RespType.SUCCESS)




    @app.route('/load-all-rules', methods=['POST'])
    def load_all_rules():
        global all_rules_loaded
        if all_rules_loaded:
            message = "All rules are already loaded."
            return response(None, message, 0, 0, RespType.INFO)
        all_rules_loaded = True

        # Insert RULES from database
        cursors = mongo.db.rules.find({})
        rules = list(cursors)

        for akashic_rule in rules:
            if not akashic_rule["active"]:
                continue
            # Add rule to env_provider
            transpiler = Transpiler(env_provider)
            try:
                transpiler.load(dumps(akashic_rule["rule"], indent=True))
                env_provider.insert_rule(transpiler.rule.rule_name, 
                                         transpiler.tranpiled_rule)
            except AkashicError as e:
                print(e.message)
                return response(
                    None, e.message, e.line, e.col, RespType.ERROR)

        message = "Engine has finished loading rules " \
                  "from database."
        return response(None, message, 0, 0, RespType.SUCCESS)



    @app.route('/all-template-names', methods=['GET'])
    def get_all_tempalte_names():
        template_names = env_provider.get_template_names()
        return response(template_names, "", 0, 0, RespType.SUCCESS)



    @app.route('/all-rule-names', methods=['GET'])
    def get_all_rule_names():
        rule_names = env_provider.get_rule_names()
        return response(rule_names, "", 0, 0, RespType.SUCCESS)

    
    @app.route('/all-facts', methods=['GET'])
    def get_all_facts():
        rule_names = env_provider.get_facts()
        return response(rule_names, "", 0, 0, RespType.SUCCESS)



    @app.route('/assist', methods=['POST'])
    def assist():
        akashic_rule = request.json

        # Insert rule that needs assistance into engine
        transpiler = Transpiler(env_provider)
        try:
            transpiler.load(dumps(akashic_rule, indent=True))
            env_provider.insert_rule(transpiler.rule.rule_name, 
                                     transpiler.tranpiled_rule)
        except AkashicError as e:
            return response(
                akashic_rule, e.message, e.line, e.col, RespType.ERROR)

        # Run the engine is assistance mode / assistance session
        try:
            env_provider.run()
        except AkashicError as e:
            return response(
                None, e.message, e.line, e.col, RespType.ERROR)

        # Collect the reponses from the assistance session
        return_data_array = []
        for ret in env_provider.return_data:
            return_data_array.append(loads(ret))

        print("ALL RETURNS AFTER ASSISTANCE")
        print(str(return_data_array))
        print("----------------------------")

        # Create the list of assistance query results
        # And the list of query rules to be removed 
        #from the engine 
        query_results = []
        rules_to_remove = set()
        for ret in return_data_array:
            print("RET: " + str(ret))
            if ret["meta"]["tag"] == "query_return":
                query_results.append(ret)
        
            if ret["meta"]["tag"] == "query_rule_name_return":
                if "query_rule_name" in ret["data"]:
                    rules_to_remove.add(ret["data"]["query_rule_name"])

        # Remove the rules colelcted in list above 
        for rule_name in rules_to_remove:
            try:
                env_provider.remove_rule(rule_name)
            except AkashicError as e:
                return response(
                    None, e.message, e.line, e.col, RespType.ERROR)

        # Turn off engine assistance mode so that all other
        # non-assistance related rules can run in next esssion
        env_provider.execute("(do-for-all-facts ((?ao __AssistanceOn)) TRUE (retract ?ao) )")
       
        # Undefine assisted rule
        try:
            env_provider.remove_rule(akashic_rule['rule-name'])
        except AkashicError as e:
            pass

        # Create response and return
        resp = {}
        resp["query_results"] = query_results
        resp["rule"] = akashic_rule
                
        message = "Assistance is done. You can view get possible values for ???* values"
        return response(resp, message, 0, 0, RespType.SUCCESS)



    #### RETURN APP
    return app