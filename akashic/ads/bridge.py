
from akashic.util.type_converter import py_to_clips_type
from akashic.exceptions import AkashicError, ErrType

from jsonpath_ng import jsonpath, parse


#TODO: Use BIND to save count result, to be used on RHS??? Maybe
#TODO: Add variable-value binding
#TODO: Add onetime option for rule execution


class Bridge(object):
    def __init__(self, data_providers):
        self.data_providers = data_providers

        self.dp_map = {}

        for dp in self.data_providers:
            self.dp_map[dp.dsd.model_id] = dp


    
    def string_to_json_type(s, to_type):
        if to_type == "INTEGER":
            return int(s)
        elif to_type == "FLOAT":
            return float(s)
        elif to_type == "BOOLEAN":
            if s == "True":
                return True
            else: 
                return False
        else:
            return s

    

    def get_field_def(self, field_name, data_provider):
        for f in data_provider.dsd.fields:
            if (f.field_name == field_name):
                return f



    def arg_list_to_request_body(self, arg_list, data_provider):
        json_construct = {}
        i = 0
        l = len(arg_list)
        while i < l:
            field_name = arg_list[i]
            field_value = arg_list[i+1]
            to_type = get_field_def(field_name, data_provider).type
            json_construct[field_name] = string_to_json_type(field_value, to_type)

            i += 2

        return json_construct



    def create_func(self, *args):
        #data_provider = self.dp_map[args[0]]
        #reflect_on_web = string_to_json_type(args[2], "BOOLEAN")
        #json_construct = arg_list_to_request_body(args[3:], data_provider)

        print("-----")
        for a in args:
            print(a)