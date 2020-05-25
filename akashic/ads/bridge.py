
from akashic.util.type_converter import py_to_clips_type
from akashic.exceptions import AkashicError, ErrType



#TODO: Use BIND to save count result, to be used on RHS??? Maybe
#TODO: Add variable-value binding
#TODO: Add onetime option for rule execution


class Bridge(object):
    def __init__(self, data_providers):
        self.data_providers = data_providers

        self.dp_map = {}

        for dp in self.data_providers:
            self.dp_map[dp.dsd.model_id] = dp


    
    def string_to_json_type(self, s, to_type):
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



    def data_arg_list_to_request_body(self, arg_list, data_provider):
        json_construct = {}
        i = 0
        l = len(arg_list)
        while i < l:
            field_name = arg_list[i]
            field_value = arg_list[i+1]
            to_type = self.get_field_def(field_name, data_provider).type
            json_construct[field_name] = self.string_to_json_type(field_value, to_type)

            i += 2

        return json_construct



    def ref_arg_list_to_url_map(self, arg_list, dp_ref_foreign_models):
        url_map_args = {}

        i = 0
        l = len(arg_list)
        while i < l:
            for ref in dp_ref_foreign_models:
                if arg_list[i] == ref.field_name:
                    url_map_args[ref.url_placement] = i[i + 1]
            i += 2

        return url_map_args



    def create_func(self, args):
        args = map(lambda arg: arg.replace('"', ''), args)
        args = list(args)
        print("-----")
        for a in args:
            print(a)


        data_provider = self.dp_map[args[0]]
        reflect_on_web = self.string_to_json_type(args[2], "BOOLEAN")
        data_len = self.string_to_json_type(args[4], "INTEGER")
        data_json_construct = self.data_arg_list_to_request_body(args[5:5+data_len], data_provider)

        print("-----")
        for a in args[5:5 + data_len]:
            print(a)

        if reflect_on_web:
            ref_len = self.string_to_json_type(args[5 + data_len + 1], "INTEGER")
            print("-----0999---- " + str(ref_len))

            ref_start_pos = 5 + data_len + 2
            url_map_args = self.ref_arg_list_to_url_map(args[ref_start_pos : ref_start_pos + ref_len], 
                                data_provider.dsd.apis.create.ref_foreign_models)

            data_provider.create(data_json_construct, **url_map_args)

        print("++**")
        

        