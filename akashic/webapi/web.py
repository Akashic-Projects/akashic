from flask import Flask, jsonify, request 
from flask_pymongo import PyMongo
from flask_cors import CORS
import json

from pymongo.errors import DuplicateKeyError

from akashic.arules.transpiler import Transpiler
from akashic.ads.data_provider import DataProvider
from akashic.ads.env_provider import EnvProvider


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["MONGO_URI"] = "mongodb://admin:devdevdev@127.0.0.1:27017/akashic?authSource=admin&readPreference=primary&appname=MongoDB%20Compass&ssl=false"
mongo = PyMongo(app)


@app.route('/dsds', methods=['POST'])
def create_dsd():
  akashic_dsd = request.json
  akashic_dsd['_id'] = akashic_dsd['model-name']

  try:
    mongo.db.dsds.insert_one(akashic_dsd)
  except DuplicateKeyError as err:
    return json.dumps({"error": "DSD with given model name already exists."})

  return akashic_dsd


@app.route('/rules', methods=['POST'])
def create_rule():
  akashic_rule = request.json
  akashic_rule['_id'] = akashic_rule['rule-name']
  try:
    mongo.db.rules.insert_one(akashic_rule)
  except DuplicateKeyError as err:
    return json.dumps({"error": "Rule with given name already exists."})

  return akashic_rule


app.run(debug=True)