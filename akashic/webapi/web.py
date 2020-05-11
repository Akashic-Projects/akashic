from flask import Flask, jsonify, request 
from flask_pymongo import PyMongo
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config["MONGO_URI"] = "mongodb://admin:devdevdev@127.0.0.1:27017/akashic?authSource=admin&readPreference=primary&appname=MongoDB%20Compass&ssl=false"

mongo = PyMongo(app)

@app.route('/rules', methods=['POST'])
def create_rule():
  akashic_rule = request.json
  akashic_rule['_id'] = akashic_rule['rule-name']

  mongo.db.rules.insert_one(akashic_rule)

  return akashic_rule


app.run(debug=True)