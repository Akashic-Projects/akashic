from akashic.exceptions import SyntacticError, SemanticError

import re
import json
from jsonpath_ng import jsonpath, parse

class DataChecker(object):

    def __init__(self, dsd):
        self.dsd = dsd

    def check_url_mapping(self, operation, url_map, field_refs):
        url_fields = []
        for m in re.finditer(r"\{(((?!\{|\}).)*)\}", url_map):
            url_fields.append(m.group(1))

        for ref in field_refs:
            if ref in url_fields:
                url_fields.remove(ref)
            else:
                raise SemanticError(f"Field ({ref}) in operation ({operation}) cannot be found in url-map setting.")
        
        if len(url_fields) > 0:
            fields_left_string = ", ".join(url_fields)
            raise SemanticError(f"Following fields ({fields_left_string}) inside of url-map setting ({url_map}) in operation ({operation}) are not referenced in settings.")


    def check_url_mappings(self):

        # Check create api, if available
        if self.dsd is not None:
            create = self.dsd.apis.create
            if create is not None:
                if create.ref_foreign_models is not None:
                    field_refs = []
                    for ref in create.ref_foreign_models:
                        field_refs.append(ref.url_placement)
                    
                    self.check_url_mapping("create", create.url_map, field_refs)
            
            # Check read_one api, if available
            read_one = self.dsd.apis.read_one
            if read_one is not None:
                if read_one.ref_foreign_models is not None:
                    field_refs = []
                    for ref in read_one.ref_foreign_models:
                        field_refs.append(ref.url_placement)
                    field_refs.append(read_one.data_indexing_up)
                    
                    self.check_url_mapping("read-one", read_one.url_map, field_refs)

                # Check read_multiple api, if available
            read_mul = self.dsd.apis.read_multiple
            if read_mul is not None:
                if read_mul.ref_foreign_models is not None:
                    field_refs = []
                    for ref in read_mul.ref_foreign_models:
                        field_refs.append(ref.url_placement)
                    field_refs.append(read_mul.page_index_url_placement)
                    field_refs.append(read_mul.page_row_count_url_placement)
                    field_refs.append(read_mul.search_fields_url_placement)
                    field_refs.append(read_mul.search_strings_url_placement)
                    field_refs.append(read_mul.sort_field_url_placement)
                    field_refs.append(read_mul.sort_order_url_placement)
                    
                    self.check_url_mapping("read-multiple", read_mul.url_map, field_refs)
                        
            # Check update api, if available
            update = self.dsd.apis.update
            if update is not None:
                if update.ref_foreign_models is not None:
                    field_refs = []
                    for ref in update.ref_foreign_models:
                        field_refs.append(ref.url_placement)
                    field_refs.append(update.data_indexing_up)
                    
                    self.check_url_mapping("update", update.url_map, field_refs)

            # Check delete api, if available
            delete = self.dsd.apis.delete
            if delete is not None:
                if delete.ref_foreign_models is not None:
                    field_refs = []
                    for ref in delete.ref_foreign_models:
                        field_refs.append(ref.url_placement)
                    field_refs.append(delete.data_indexing_up)
                    
                    self.check_url_mapping("delete", delete.url_map, field_refs)
        return 0


    def translate_type(self, type_string):
        ttype = None
        if type_string == "INTEGER":
            ttype = int
        elif type_string == "FLOAT":
            ttype = float
        elif type_string == "STRING":
            ttype = str
        elif type_string == "BOOLEAN":
            ttype = bool
        return ttype


    def check_field_types(self, use_json_as, operation, json_string):
        json_path = None
        if use_json_as == "response":
            json_path = lambda field : field.response_json_path
        elif use_json_as == "request":
            json_path = lambda field : field.request_json_path

        for field in self.dsd.fields:

            if (
                (not (use_json_as == "request" and operation == "create" and field.use_for_create)) and
                (not (use_json_as == "request" and operation == "update" and field.use_for_update))
            ): 
                continue
            

            jsonpath_expr = parse(json_path(field))
            parsed_json = json.loads(json_string)
            result = [match.value for match in jsonpath_expr.find(parsed_json)]

            if len(result) == 0:
                raise SemanticError(f"Field ({field.field_name}) is not present in json object.")

            if len(result) > 1:
                raise SemanticError(f"More than one field with same name ({field.field_name}) is present in json object.")

            expected_type = self.translate_type(field.type)

            if not isinstance(result[0], expected_type):
                raise SemanticError(f"Type of field ({field.field_name}) does not match type from provided data. Expected ({str(expected_type)}), but received ({result[0].__class__.__name__}).")