
import re
import json
from jsonpath_ng import jsonpath, parse

from akashic.util.type_converter import clips_to_py_type, py_to_clips_type

from akashic.exceptions import AkashicError, ErrType


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



    def check_field_list(self):
        num_of_primary_keys = 0
        for field in self.dsd.fields:
            if field.use_as == "\"primary-key\"":
                num_of_primary_keys += 1
            
        if num_of_primary_keys != 1:
            line, col = self.dsd._tx_parser \
                        .pos_to_linecol(self.dsd._tx_position)
            message = "There must be one and only one primary-key field " \
                      "in DSD field list, but {0} found." \
                      .format(str(num_of_primary_keys))
            raise AkashicError(message, line, col, ErrType.SEMANTIC)



    def check_web_reflection_data(self):
        if not hasattr(self.dsd, 'apis'):
            line, col = self.dsd._tx_parser \
                        .pos_to_linecol(self.dsd._tx_position)
            message = "Web reflection is turned on. There must " \
                      "be at least one defined api in DSD."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)



    def check_url_mapping(self, operation):
        """ Checks single URL mapping
        
        Parameters
        ----------
        operation : object
            Web service operation / method, 

        Raises
        ------
        AkashicError
            If URL map fields missmatches fileds specified in DSD
        """

        # TODO: Add check if model-ids are ok
        d_line, d_col = self.dsd._tx_parser \
                            .pos_to_linecol(operation._tx_position)
        url_map = operation.url_map
        url_fields = []
        for m in re.finditer(r"\{(((?!\{|\}).)*)\}", url_map):
            url_fields.append(m.group(1))

        for ref_obj in operation.ref_models:
            ref = ref_obj.url_placement
            if ref in url_fields:
                url_fields.remove(ref)
            else:
                line, col = self.dsd._tx_parser \
                                .pos_to_linecol(ref_obj._tx_position)
                message = "Url placement '{0}' in operation " \
                          "cannot be found in url-map setting." \
                          .format(ref)
                raise AkashicError(message, 
                                   line, 
                                   col, 
                                   ErrType.SEMANTIC)
        
        if len(url_fields) > 0:
            fields_left_string = ", ".join(url_fields)
            message = "Following url palcements '{0}' inside " \
                      "of url-map setting '{1}' in operation " \
                      "are not referenced in settings." \
                      .format(fields_left_string, url_map)
            raise AkashicError(message, 
                               d_line, 
                               d_col, 
                               ErrType.SEMANTIC)



    def check_url_mappings(self):
        """ Checks all URL mappings from given DSD

        Details
        -------
        Here we check URL mapping of each web service method

        Raises
        ------
        AkashicError
            If URL map fields missmatches fileds specified in DSD
        """

        if not hasattr(self.dsd, 'apis'):
            return 0

        # Check create api, if available
        if self.dsd is not None:
            if hasattr(self.dsd.apis, 'create'):
                create = self.dsd.apis.create
                if hasattr(create, "ref_models"):
                    self.check_url_mapping(create)
            
            # # Check read_one api, if available
            # if hasattr(self.dsd.apis, 'read_one'):
            #     read_one = self.dsd.apis.read_one
            #     if hasattr(read_one, "ref_models"):
            #        self.check_url_mapping(read_one)

            # # Check read_multiple api, if available
            # if hasattr(self.dsd.apis, 'read_multiple'):
            #     read_mul = self.dsd.apis.read_multiple
            #     if read_mul is not None:
            #         if read_mul.ref_models is not None:
            #             field_refs = []
            #             for ref in read_mul.ref_models:
            #                 field_refs.append(ref.url_placement)
            #             field_refs.append(
            #                 read_mul.page_index_url_placement)
            #             field_refs.append(
            #                 read_mul.page_row_count_url_placement)
            #             field_refs.append(
            #                 read_mul.search_fields_url_placement)
            #             field_refs.append(
            #                 read_mul.search_strings_url_placement)
            #             field_refs.append(
            #                 read_mul.sort_field_url_placement)
            #             field_refs.append(
            #                 read_mul.sort_order_url_placement)
                        
            #             try:
            #                 self.check_url_mapping("read-multiple", 
            #                                        read_mul.url_map, 
            #                                        field_refs)
            #             except AkashicError as e:
            #                 line, col = self.dsd._tx_parser \
            #                             .pos_to_linecol(
            #                                 read_mul.ref_models._tx_position)
            #                 raise AkashicError(e.message, 
            #                                    line, 
            #                                    col, 
            #                                    ErrType.SEMANTIC)
                        
            # Check update api, if available
            if hasattr(self.dsd.apis, 'update'):
                update = self.dsd.apis.update
                if hasattr(update, "ref_models"):
                    self.check_url_mapping(update)

            # Check delete api, if available
            if hasattr(self.dsd.apis, 'delete'):
                delete = self.dsd.apis.delete
                if hasattr(delete, "ref_models"):
                    self.check_url_mapping(delete)



    def check_field_types(self, use_json_as, operation, json_object):
        """ Checks JSON object field types against fields defined in DSD
        
        Parameters
        ----------
        use_json_as : str
            Value which defines if JSON originates from web server 
            'request' or 'response'
        operation : str
            Web service operation / method, 
            possible values: "create", "read_one", "read_multiple", 
                             "update", "delete"
        json_object : object
            Parsed JSON object

        Raises
        ------
        AkashicError
            If JSON object field types missmatch fields defined in DSD 
        """

        json_path = None
        if use_json_as == "response":
            json_path = lambda field : field.response_one_json_path
        elif use_json_as == "request":
            json_path = lambda field : "$." + field.field_name

        for field in self.dsd.fields:
            
            jsonpath_expr = parse(json_path(field))
            result = [match.value for match in jsonpath_expr.find(json_object)]

            if len(result) == 0:
                line, col = self.dsd._tx_parser \
                            .pos_to_linecol(field._tx_position)
                message = "Field '{0}' is not present in json object." \
                          .format(field.field_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if len(result) > 1:
                line, col = self.dsd._tx_parser \
                            .pos_to_linecol(field._tx_position)
                message = "More than one field with same name '{0}' " \
                          "is present in json object." \
                          .format(field.field_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            expected_type = clips_to_py_type(field.type)

            if not isinstance(result[0], expected_type):
                line, col = self.dsd._tx_parser \
                            .pos_to_linecol(field._tx_position)
                message = "Type of field '{0}' does not match type from " \
                          "provided data. Expected '{1}', " \
                          "but received '{2}'." \
                          .format(field.field_name,
                                  str(field.type),
                                  py_to_clips_type(result[0].__class__))
                raise AkashicError(message, line, col, ErrType.SEMANTIC)