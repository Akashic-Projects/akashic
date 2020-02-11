from textx import metamodel_from_file
from textx.export import metamodel_export, model_export

from os.path import join, dirname

from textx.exceptions import TextXSyntaxError, TextXSemanticError

from akashic.exceptions import SyntacticError, SemanticError

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
    
    
    def check_structure(self):
        if self.dsd is not None:
            create = self.dsd.apis.create
            if create is not None:
                if create.ref_foreign_models is not None:
                    url_field_list = []
                    for m in re.finditer(r"\{(((?!\{|\}).)*)\}", create.url_map):
                        url_field_list.append(m.group(1))

                    for ref in create.ref_foreign_models:
                        if ref.url_placement in url_field_list:
                            url_field_list.remove(ref.url_placement)
                        else:
                            raise SemanticError(f"Field ({ref.url_placement}) cannot be found in url-map setting.")
                    
                    if len(url_field_list) > 0:
                        fields_left_string = ", ".join(url_field_list)
                        raise SemanticError(f"Following fields ({fields_left_string}) inside of url-map setting ({create.url_map}) are not referenced in (referenced-foreign-models) setting.")
        return 1


    def generate_url_dictionary(self):
        pass

    def generate_clips_template(self):
        pass



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
