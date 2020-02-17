from os.path import join, dirname
import re

from textx import metamodel_from_file
from textx.export import metamodel_export, model_export
from textx.exceptions import TextXSyntaxError, TextXSemanticError

from akashic.exceptions import SyntacticError, SemanticError
from akashic.adss.data_checker import DataChecker
from akashic.adss.data_fetcher import DataFetcher

import json
from jsonpath_ng import jsonpath, parse


class DataSourceDefinitionInterpreter(object):

    def __init__(self):
        this_folder = dirname(__file__)
        self.meta_model = metamodel_from_file(join(this_folder, 'meta_model.tx'), debug=False)
        self.dsd = None
        self.checker = None
        self.fetcher = None


    def transalte_exception(self, ttype, line, col, message):
        message = f"Detected: {ttype} error at line {line} and column {col}. \nMessage: " + message
        if ttype == "Syntax":
            raise SyntacticError(message)
        elif ttype == "Semantic":
            raise SemanticError(message)


    def load(self, dsd_string):
        try:
            self.dsd = self.meta_model.model_from_str(dsd_string)
            return 0
        except TextXSyntaxError as syntaxError:
            self.transalte_exception("Syntax", syntaxError.line, syntaxError.col, syntaxError.message)
        except TextXSemanticError as semanticError:
            self.transalte_exception("Semantic", syntaxError.line, syntaxError.col, syntaxError.message)
    

    def setup(self):
        self.checker = DataChecker(self.dsd)
        self.checker.check_url_mappings()

        self.fetcher = DataFetcher(self.dsd.auth_header, self.dsd.additional_headers)
        return 0
        

    def fill_url_map(self, url_map, **kwargs):
        url_fields = []
        for m in re.finditer(r"\{(((?!\{|\}).)*)\}", url_map):
            url_fields.append(m.group(1))
        
        if len(url_fields) != len(kwargs):
            return 1

        for key, value in kwargs.items():
            pattern = re.compile("\{" + key + "\}")
            url_map = re.sub(pattern, str(value), url_map)
        
        return url_map


    def generate_clips_template(self):
        tempalte_def = "(deftemplate " + str(self.dsd.model_id) + "\n"
        slot_defs = []
        for field in self.dsd.fields:
            # Resolve BOOLEAN type
            resolved_type = "INTEGER"
            if (field.type == "BOOLEAN"):
                resolved_type = "INTEGER"
            else:
                resolved_type = field.type
            slot_defs.append("\t(slot " + str(field.field_name) + " (type " + str(resolved_type) + "))")
        
        tempalte_def += "\n".join(slot_defs) + ")"

        return tempalte_def


    def generate_clips_fact(self, json_string):
        self.checker.check_field_types(json_string)

        clips_fact = "(" + str(self.dsd.model_id)
        clips_fields = []

        # Resolve field values
        for field in self.dsd.fields:
            jsonpath_expr = parse(field.json_path)
            parsed_json = json.loads(json_string)
            result = [match.value for match in jsonpath_expr.find(parsed_json)][0]

            resolved_value = None
            if field.type == "INTEGER" or field.type == "FLOAT":
                resolved_value = result
            elif field.type == "BOOLEAN":
                if result == True:
                    resolved_value = 1
                else:
                    resolved_value = 0
            elif field.type == "STRING":
                resolved_value = f"\"{result}\""

            clips_fields.append("\t(" + str(field.field_name) + " " + str(resolved_value) + ")")

        clips_fact += "\n".join(clips_fields) + ")"
        return clips_fact


    def create(self, data):
        pass


    def read_one(self, **kwargs):
        url_map = self.dsd.apis.read_one.url_map
        url = self.fill_url_map(url_map, **kwargs)
        
        result = self.fetcher.read_one(url)
        return result
    

    def read_multiple(self, options):
        pass


    def update(self, data):
        pass


    def delete(self, data_id):
        pass
