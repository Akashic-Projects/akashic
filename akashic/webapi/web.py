from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo

from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config["MONGO_URI"] = "mongodb://admin:devdevdev@127.0.0.1:27017/test?authSource=admin&readPreference=primary&appname=MongoDB%20Compass&ssl=false"

mongo = PyMongo(app)

@app.route('/rules', methods=['POST'])
def create_rule():
  content = request.json
  print(content)
  return content

  # user = mongo.db.user
  # output = []
  # print(user.find())
  # for s in user.find():
  #   output.append({'name' : s['name'], 'age' : s['age']})
  # return jsonify({'result' : output})


app.run(debug=True)