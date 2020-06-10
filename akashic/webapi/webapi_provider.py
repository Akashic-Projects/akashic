from enum import Enum
from datetime import datetime

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


class RespType(Enum):
    def __str__(self):
        return str(self.name)

    SUCCESS = 1
    INFO = 2
    ERROR = 3


class WebAPIProvider(object):

    def __init__(self, mongo_uri):
        app = Flask(__name__)
        CORS(app, resources={r"/*": {"origins": "*"}})
        app.config["MONGO_URI"] = mongo_uri
        mongo = PyMongo(app)
    

    @app.before_first_request
    def init_akashic():
        global env_provider
        global dsd_providers_dict

        env_provider = EnvProvider()
        dsd_providers_dict = {}

        # Load DSDs

        # Load rules