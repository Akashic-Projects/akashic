from os.path import join, dirname

from textx import metamodel_from_file
from textx.export import metamodel_export, model_export
from textx.exceptions import TextXSyntaxError, TextXSemanticError

from akashic.exceptions import SyntacticError, SemanticError
from akashic.adsds.checker import Checker

import re


class DataSourceDefinitionInterpreter(object):

    def __init__(self):
        this_folder = dirname(__file__)
        self.meta_model = metamodel_from_file(join(this_folder, 'meta_model.tx'), debug=False)
        self.dsd = None

    def print_error_message(self, ttype, line, col, message):
        print(f"Detected: {ttype} error at line {line} and column {col}. \nMessage: " + message)

    def load(self, dsd_string):
        try:
            self.dsd = self.meta_model.model_from_str(dsd_string)
            print(self.dsd.def_name)
            return 1
        except TextXSyntaxError as syntaxError:
            self.print_error_message("Syntax", syntaxError.line, syntaxError.col, syntaxError.message)
        except TextXSemanticError as semanticError:
            self.print_error_message("Semantic", syntaxError.line, syntaxError.col, syntaxError.message)
    

    def check_url_mappings(self):
        checker = Checker(self.dsd)
        checker.run()

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



    def setup_data_aquisition_module(self, options):
        pass

    def setup_data_container(self, options):
        pass

    def instantiate_data_container(self, data_container_id):
        pass

    def create(self, data):
        pass

    def read_one(self, id):
        pass
    
    def read_multiple(self, options):
        pass

    def update(self, data):
        pass

    def delete(self, data_id):
        pass
