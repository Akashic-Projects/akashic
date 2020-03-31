
from akashic.exceptions import SyntacticError, SemanticError

import re
import json
from jsonpath_ng import jsonpath, parse



class DataChecker(object):
    """ DataChecker class

    We use this class to check semantics of URL mappings in DSD and
    to check if fields of JSON object corespond to the given DSD
    """

    def __init__(self, dsd):
        """ DataChecker constructor method
        
        Here we load DSD on which checking operations will take place.
        """

        self.dsd = dsd



    def check_url_mapping(self, operation, url_map, field_refs):
        """ Checks single URL mapping
        
        Parameters
        ----------
        operation : str
            Web service operation / method, 
            possible values: "create", "read_one", "read_multiple", "update", "delete"
        url_map : str
            URL map is regular URL string containing '{variable_name}' in places of real key data
        field_refs : list
            The list of referenced-foreign-models url-placements

        Raises
        ------
        SemanticError
            If URL map fields missmatches fileds specified in DSD
        """

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
        """ Checks all URL mappings from given DSD

        Details
        -------
        Here we check URL mapping of each web service method

        Raises
        ------
        SemanticError
            If URL map fields missmatches fileds specified in DSD
        """

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
        return 1



    # TODO: Check if BOOLEAN is really needed here
    def clips_to_py_type(self, ctype):
        """ Converts CLIPS type to Python type
        
        Parameters
        ----------
        ctype : str
            CLIPS type, possible values: "INTEGER", "FLOAT", "STRING" and maybe "BOOLEAN"

        Returns
        -------
        ptype: type
            Coresponding python type
        """

        ptype = None
        if ctype == "INTEGER":
            ptype = int
        elif ctype == "FLOAT":
            ptype = float
        elif ctype == "STRING":
            ptype = str
        elif ctype == "BOOLEAN":
            ptype = bool
        return ptype



    def py_to_clips_type(self, ptype):
        """ Converts Python type to CLIPS type
        
        Parameters
        ----------
        ptype : str
            Python type

        Returns
        -------
        ctype: str
            Coresponding CLIPS type
        """

        ctype = None
        if ptype == int:
            ctype = "INTEGER"
        elif ptype == float:
            ctype = "FLOAT"
        elif ptype == str:
            ctype = "STRING"
        elif ptype == bool:
            ctype = "BOOLEAN"
        return ctype



    # TODO: Does this even make senase?
    def check_field_types(self, use_json_as, operation, json_object):
        """ Checks JSON object field types against fields defined in DSD
        
        Parameters
        ----------
        use_json_as : str
            Value which defines if JSON originates from web server 'request' or 'response'
        operation : str
            Web service operation / method, 
            possible values: "create", "read_one", "read_multiple", "update", "delete"
        json_object : object
            Parsed JSON object

        Raises
        ------
        SemanticError
            If JSON object field types missmatch fields defined in DSD 
        """

        json_path = None
        if use_json_as == "response":
            json_path = lambda field : field.response_one_json_path
        elif use_json_as == "request":
            json_path = lambda field : field.request_json_path

        for field in self.dsd.fields:
            if (
                (not (use_json_as == "request" and operation == "create" and field.use_for_create)) and
                (not (use_json_as == "request" and operation == "update" and field.use_for_update))
            ): 
                continue
            
            jsonpath_expr = parse(json_path(field))
            result = [match.value for match in jsonpath_expr.find(json_object)]

            if len(result) == 0:
                raise SemanticError(f"Field ({field.field_name}) is not present in json object.")

            if len(result) > 1:
                raise SemanticError(f"More than one field with same name ({field.field_name}) is present in json object.")

            expected_type = self.clips_to_py_type(field.type)

            if not isinstance(result[0], expected_type):
                raise SemanticError(f"Type of field ({field.field_name}) does not match type from provided data. Expected ({str(field.type)}), but received ({self.py_to_clips_type(result[0].__class__)}).")