
from akashic.util.type_converter import py_to_clips_type
from akashic.exceptions import AkashicError, ErrType



#TODO: Add variable-value binding - so save count result for example
#TODO: Add onetime option for rule execution
#TODO: Add date-time support
#TODO: ??? query system


class DataBridge(object):
    """ DataBridge class
        
    We use this class to store CRUD and data related python
    functions called by CLIPS enviroment
    """

    def __init__(self, data_providers):
        self.data_providers = data_providers
        self.env_provider = None

        self.data_providers_map = {}
        for dp in self.data_providers:
            self.data_providers_map[dp.dsd.model_id] = dp



    def set_env_provider(self, env_provider):
        self.env_provider = env_provider


    
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
            json_construct[field_name] = self.string_to_json_type(field_value,
                                                                  to_type)

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

        print("\n-------------------")
        for a in args:
            print(a)
        print()

        MODEL_NAME_POS      = 0
        REFLECT_INFO_POS    = 2
        DATA_LEN_POS        = 4
        DATA_START_POS      = 5

        data_provider = self.data_providers_map[args[MODEL_NAME_POS]]
        reflect_on_web = self.string_to_json_type(args[REFLECT_INFO_POS],
                                                  "BOOLEAN")
        data_len = self.string_to_json_type(args[DATA_LEN_POS], 
                                            "INTEGER")
        data_json_construct = self.data_arg_list_to_request_body(
                                args[DATA_START_POS:DATA_START_POS+data_len], 
                                data_provider)

        if reflect_on_web:
            REF_LEN_POS = DATA_START_POS + data_len + 1
            ref_len = self.string_to_json_type(args[REF_LEN_POS], 
                                               "INTEGER")

            REF_START_POS = REF_LEN_POS + 1
            url_map_args = self.ref_arg_list_to_url_map(
                            args[REF_START_POS:REF_START_POS+ref_len], 
                            data_provider.dsd.apis.create.ref_foreign_models)

            response_obj = data_provider.create(data_json_construct, 
                                                **url_map_args)
            
            # Create full CLIPS fact from response and add it to CLIPS env
            clips_fact = data_provider.generate_one_clips_fact(response_obj)
            print(clips_fact)
            self.env_provider.insert_fact(clips_fact)
        
        else:
            clips_fact = data_provider.generate_one_clips_fact(
                            data_json_construct)
            self.env_provider.insert_fact(clips_fact)


        for f in self.env_provider.env.facts():
            print("---------")
            print(f)

        print("****")
        

        
    def return_func(self, *args):
        args = map(lambda arg: arg.replace('"', ''), args)
        args = list(args)


        print("\n-------------------")
        for a in args:
            print(a)
        print()