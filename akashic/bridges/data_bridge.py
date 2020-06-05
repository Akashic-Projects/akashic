
import uuid
import json

from akashic.arules.transpiler import Transpiler

from akashic.util.type_converter import string_to_py_type
from akashic.exceptions import AkashicError, ErrType

from akashic.system.rules.generic_rule import GENERIC_RULE

from akashic.ads.data_provider import FactGenType


class DataBridge(object):
    """ DataBridge class
        
    We use this class to store CRUD and data related python
    functions called by CLIPS enviroment
    """

    def __init__(self, data_providers, env_provider):
        self.data_providers = data_providers
        self.env_provider = env_provider

        self.data_providers_map = {}
        for dp in self.data_providers:
            self.data_providers_map[dp.dsd.model_id] = dp

        # If num_of_args are -1, -2, -3,
        # then it is actually 'more than 1,2,3..'
        self.exposed_functions= [
            {
                "function":     self.create_func,
                "num_of_args":  -1,
                "return_type":  "INTEGER"
            },
            {
                "function":     self.return_func,
                "num_of_args":  -1,
                "return_type":  "INTEGER"
            },
            {
                "function":     self.update_func,
                "num_of_args":  -1,
                "return_type":  "INTEGER"
            },
            {
                "function":     self.delete_func,
                "num_of_args":  -1,
                "return_type":  "INTEGER"
            }
        ]


    def refresh_data_providers(self, data_providers):
        self.data_providers = data_providers
        self.data_providers_map = {}
        for dp in self.data_providers:
            self.data_providers_map[dp.dsd.model_id] = dp



    def data_arg_list_to_request_body(self, arg_list):
        json_construct = {}
        i = 0
        l = len(arg_list)
        while i < l:
            field_name = arg_list[i]
            field_value = arg_list[i+1]
            to_type = arg_list[i+2]
            
            json_construct[field_name] = string_to_py_type(field_value,
                                                           to_type)
            i += 3
        return json_construct



    def ref_arg_list_to_url_map(self, arg_list, dsd_api_object):
        url_map_args = {}
        i = 0
        l = len(arg_list)
        while i < l:
            for ref in dsd_api_object.ref_models:
                if arg_list[i] == ref.field_name:
                    url_map_args[ref.url_placement] = arg_list[i + 1]

            i += 2

        return url_map_args



    def print_args(self, args, header):
        print("\n-------------------" + str(header) + " START")
        for a in args:
            print(a)
        print("\n-------------------" + str(header) + " END")



    def create_func(self, *args):
        args = map(lambda arg: arg.replace('"', ''), args)
        args = list(args)

        self.print_args(args, "CREATE")

        MODEL_ID_POS       = 0
        REFLECT_INFO_POS   = 2
        DATA_LEN_POS       = 4
        DATA_START_POS     = 5

        data_provider = self.data_providers_map[args[MODEL_ID_POS]]
        reflect_on_web = string_to_py_type(args[REFLECT_INFO_POS], "BOOLEAN")

        data_len = string_to_py_type(args[DATA_LEN_POS], "INTEGER")
        data_json_construct = self.data_arg_list_to_request_body(
            args[DATA_START_POS:DATA_START_POS+data_len]
        )

        if reflect_on_web:
            REF_LEN_POS = DATA_START_POS + data_len + 1
            ref_len = string_to_py_type(args[REF_LEN_POS], "INTEGER")

            REF_START_POS = REF_LEN_POS + 1
            url_map_args = self.ref_arg_list_to_url_map(
                args[REF_START_POS:REF_START_POS+ref_len], 
                data_provider.dsd.apis.create
            )

            response_obj = data_provider.create(data_json_construct, 
                                                **url_map_args)
            
            # Create full CLIPS fact from response and add it to CLIPS env
            clips_fact = data_provider.generate_one_clips_fact(
                response_obj,
                FactGenType.RESP_FROM_WEB
            )
            self.env_provider.insert_fact(clips_fact)
        
        else:
            clips_fact = data_provider.generate_one_clips_fact(
                data_json_construct,
                FactGenType.PLAIN
            )
            self.env_provider.insert_fact(clips_fact)

        return 0



    def gen_clips_modify_fact_expr(self, var_name, args):
        clips_field_mods = []
        length = len(args)
        i = 0
        while i < length:
            field_name = args[i]
            field_value = args[i+1]
            field_type = args[i+2]

            if field_type == "STRING":
                field_value = '"' + field_value + '"'
            clips_field_mods.append("(" + \
                                    field_name + " " + \
                                    field_value + \
                                    ")")
            i += 3
        
        return "(modify " + var_name + " " + \
               " ".join(clips_field_mods) + \
               ")"



    def get_primary_key_field(self, data_provider):
        for field in data_provider.dsd.fields:
            if field.use_as == "\"primary-key\"":
                return field



    def get_field_value_from_args(self, args, field_name):
        length = len(args)
        i = 0
        while i < length:
            f_name = args[i]
            value = args[i+1]
            value_type = args[i+2]
            if f_name == field_name:
                new_value = value
                if value_type == "STRING":
                    new_value = '"' + new_value + '"'
                return new_value
            i += 3



    def update_func(self, *args):
        args = map(lambda arg: arg.replace('"', ''), args)
        args = list(args)

        self.print_args(args, "UPDATE")

        MODEL_ID_POS      = 0
        REFLECT_INFO_POS  = 2
        DATA_LEN_POS      = 4
        DATA_START_POS    = 5

        # Obtain data from args
        data_provider = self.data_providers_map[args[MODEL_ID_POS]]
        reflect_on_web = string_to_py_type(args[REFLECT_INFO_POS], "BOOLEAN")
        data_len = string_to_py_type(args[DATA_LEN_POS], "INTEGER")

        REF_LEN_POS = DATA_START_POS + data_len + 1
        REF_START_POS = REF_LEN_POS + 1
        
        ref_len = string_to_py_type(args[REF_LEN_POS], "INTEGER")
        
        # Build and deploy modification rule
        primary_key_field_name = \
            self.get_primary_key_field(data_provider).field_name
        primary_key_field_value = self.get_field_value_from_args(
            args[REF_START_POS:REF_START_POS+ref_len],
            primary_key_field_name
        )
        rhs = """{{ "?to_update<-": "[{0}.{1} == {2}]" }}""".format(
                data_provider.dsd.model_id,
                str(primary_key_field_name),
                str(primary_key_field_value)
            )
        lhs = """{{ "clips": "{0}" }}""".format(
            self.gen_clips_modify_fact_expr(
                "?to_update",
                args[DATA_START_POS:DATA_START_POS+data_len]
            )
        )
        tmp_update_rule = GENERIC_RULE.format(
            "__update_fact_" + str(uuid.uuid4()).replace('-', ''),
            "\"system\"",
            "true",
            rhs,
            lhs
        )
        print("\nMODIFICATION FULE: " + tmp_update_rule)

        print("\nMOD. RULE TRANSPILATION PRINT:")
        transpiler = Transpiler(self.env_provider)
        transpiler.load(tmp_update_rule)

        self.env_provider.insert_rule(transpiler.rule.rule_name, 
                                      transpiler.tranpiled_rule)
        
        # Reflect modification on web if required
        if reflect_on_web:
            data_json_construct = self.data_arg_list_to_request_body(
                args[DATA_START_POS:DATA_START_POS+data_len]
            )

            url_map_args = self.ref_arg_list_to_url_map(
                *args[REF_START_POS:REF_START_POS+ref_len], 
                data_provider.dsd.apis.update
            )

            print("\nMAP: " + str(url_map_args))

            response_obj = data_provider.update(data_json_construct, 
                                                **url_map_args)

            print("\nUPDATE RESPONSE:\n" + str(response_obj) + "\n\n")

        # Print all facts
        print("FACTS - print from bridge:")
        for f in self.env_provider.env.facts():
            print("---------")
            print(f)

        print("****")
        return 0



    def return_func(self, *args):
        args = map(lambda arg: arg.replace('"', ''), args)
        args = list(args)

        self.print_args(args, "RETURN")

        DATA_LEN_POS = 1
        DATA_START_POS = 2

        data_len = string_to_py_type(args[DATA_LEN_POS], "INTEGER")
        data_json_construct = self.data_arg_list_to_request_body(
            args[DATA_START_POS : (DATA_START_POS + data_len)],
        )

        print(json.dumps(data_json_construct, indent=4))
        return 0



    def delete_func(self, *args):
        args = map(lambda arg: arg.replace('"', ''), args)
        args = list(args)

        self.print_args(args, "DELETE")

        MODEL_ID_POS     = 0
        REFLECT_INFO_POS = 2
        REF_LEN_POS      = 4
        REF_START_POS    = 5

        # Obtain data from args
        data_provider = self.data_providers_map[args[MODEL_ID_POS]]
        reflect_on_web = string_to_py_type(args[REFLECT_INFO_POS], "BOOLEAN")        
        ref_len = string_to_py_type(args[REF_LEN_POS], "INTEGER")
        
        # Build and deploy modification rule
        primary_key_field_name = \
            self.get_primary_key_field(data_provider).field_name
        primary_key_field_value = self.get_field_value_from_args(
            args[REF_START_POS:REF_START_POS+ref_len],
            primary_key_field_name
        )
        rhs = """{{ "?to_delete<-": "[{0}.{1} == {2}]" }}""".format(
                data_provider.dsd.model_id,
                str(primary_key_field_name),
                str(primary_key_field_value)
            )
        lhs = """{{ "clips": "{0}" }}""".format(
            "(retract ?to_delete)"
        )
        tmp_update_rule = GENERIC_RULE.format(
            "__delete_fact_" + str(uuid.uuid4()).replace('-', ''),
            "\"system\"",
            "true",
            rhs,
            lhs
        )
        print("\nDELETION FULE: " + tmp_update_rule)

        print("\nDEL. RULE TRANSPILATION PRINT:")
        transpiler = Transpiler(self.env_provider)
        transpiler.load(tmp_update_rule)

        self.env_provider.insert_rule(transpiler.rule.rule_name, 
                                      transpiler.tranpiled_rule)
        
        # Reflect modification on web if required
        if reflect_on_web:
            url_map_args = self.ref_arg_list_to_url_map(
                args[REF_START_POS:REF_START_POS+ref_len],
                data_provider.dsd.apis.update
            )

            print("\nMAP: " + str(url_map_args))

            response_obj = data_provider.delete(**url_map_args)

            print("\nDELETION RESPONSE:\n" + str(response_obj) + "\n\n")

        # Print all facts
        print("FACTS - print from bridge:")
        for f in self.env_provider.env.facts():
            print("---------")
            print(f)

        print("****")
        return 0

        return 0