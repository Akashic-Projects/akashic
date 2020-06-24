
import re
import json
from enum import Enum
from jsonpath_ng import jsonpath, parse
from os.path import join, dirname

from textx import metamodel_from_file, metamodel_from_str
from textx.export import metamodel_export, model_export
from textx.exceptions import TextXSyntaxError, TextXSemanticError

from akashic.exceptions import AkashicError, ErrType
from akashic.ads.data_checker import DataChecker
from akashic.ads.data_fetcher import DataFetcher


class FactGenType(Enum):
    def __str__(self):
        return str(self.name)
        
    RESP_FROM_WEB   = 1
    PLAIN           = 2



class DataProvider(object):
    """ DataProvider class

    It serves the purpose of mapping json data obtained 
    from specified web services to the clips templates and facts,
    using written specification called DSD (data source definition).
    """

    def __init__(self, env_provider):
        """ DataProvider constructor method
        
        Main operation is loading the meta-model which describes and defines
        the grammar and structure of single data source definition.
        """

        self.env_provider = env_provider

        # this_folder = dirname(__file__)
        # self.meta_model = metamodel_from_file(
        #                     join(this_folder, 'meta_model.tx'), debug=False)
        self.meta_model = metamodel_from_str(self.env_provider.dsd_mm, 
                                             debug=False)
        self.dsd = None
        self.checker = None
        self.fetcher = None

        self.clips_template = None



    # LOADING & SETUP OPERATIONS SECTION 
    ################################################################

    def load(self, dsd_string):
        """ Loads data-provider specification from given string

        Parameters
        ----------
        dsd_string : str
            String containing data source definition

        Raises
        ------
        AkashicError
        """

        try:
            self.dsd = self.meta_model.model_from_str(dsd_string)
            return 
        except RecursionError as re:
            message = "Infinite left recursion is detected. " \
                      "There was unknown syntactic error."
            raise AkashicError(message, 0, 0, ErrType.SYNTACTIC)
        except TextXSyntaxError as syntaxError:
            raise AkashicError(
                syntaxError.message, 
                syntaxError.line, 
                syntaxError.col, 
                ErrType.SYNTACTIC
            )
        except TextXSemanticError as semanticError:
            raise AkashicError(
                semanticError.message, 
                semanticError.line, 
                semanticError.col, 
                ErrType.SEMANTIC
            )
    


    def setup(self):
        """ Setup DataChecker and DataFetcher based on 
            loaded data source definition

        """
        self.checker = DataChecker(self.dsd)
        self.checker.check_field_list()
        
        if self.dsd.can_reflect:
            self.checker.check_web_reflection_data()
            self.checker.check_url_mappings()
            self.fetcher = DataFetcher(
                self.dsd.auth_header, self.dsd.additional_headers)

        return 0
        


    # EXTERNAL OPERATIONS SECTION
    ################################################################

    def field_lookup(self, field_name):
        """ Searches field with given name
        
        Returns
        -------
        object
            Field object is returned if found
        None
            If field with given name is not found
        """

        for field in self.dsd.fields:
            if field.field_name == field_name:
                return field
        return None



    # CLIPS STATEMENTS GENERATION SECTION 
    ################################################################

    def generate_clips_template(self):
        """ Generates CLIPS template from loaded data source definition

        Details
        -------
        We use DSD model_id unique identifier for CLIPS template name.
        CLIPS does not support BOOLEAN type, so we convert it to INTEGER.

        Returns
        -------
        clips_tempalte_def : str
            Generated CLIPS template definition statement
        """

        clips_tempalte_def = "(deftemplate " + str(self.dsd.model_id) + "\n"
        slot_defs = []
        for field in self.dsd.fields:
            # Resolve BOOLEAN type
            resolved_type = "INTEGER"
            if (field.type == "BOOLEAN"):
                resolved_type = "INTEGER"
            else:
                resolved_type = field.type
            slot_defs.append("\t(slot " + str(field.field_name) + \
                             " (type " + str(resolved_type) + "))")
        
        clips_tempalte_def += "\n".join(slot_defs) + ")"

        self.clips_template = clips_tempalte_def
        return clips_tempalte_def



    def generate_clips_fact(self, json_object, json_path_func):
        """ Generic method that generates CLIPS fact 
            from given parsed JSON object

        Parameters
        ----------
        json_object : object
            Parsed JSON object
        json_path_func: function
            Function which determines which JSON path expression 
            will be used, possible functions: for single object & 
            for multitude of objects inside of array

        Details
        -------
        We use DSD model_id unique identifier for CLIPS fact name.
        CLIPS does not support BOOLEAN type, so we convert it to INTEGER.

        1. We loop through all fields of this data source definition.
        2. We locate DSD field in JSON object and read data from it.
        3. We translate BOOLEAN to INTEGER, if present.
        4. We add quotes to STRING type, if present.

        Returns
        -------
        clips_fact: str
            Generated CLIPS fact definition statement
        """

        clips_fact = "(" + str(self.dsd.model_id)
        clips_fields = []

        print("JSON")
        print(json.dumps(json_object))
        print("\n")


        for field in self.dsd.fields:
            jsonpath_expr = parse(str(json_path_func(field)))
            field_loc = [match.value for match in jsonpath_expr \
                                                  .find(json_object)]

            if not field_loc or len(field_loc) < 1:
                line, col = self.dsd._tx_parser \
                            .pos_to_linecol(field._tx_position)
                message = "Field '{0}' in DSD is not " \
                          "matched in provided JSON data." \
                          .format(field.field_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            result = field_loc[0]

            # Resolve field value
            resolved_value = None
            if field.type == "INTEGER" or field.type == "FLOAT":
                resolved_value = result
            elif field.type == "BOOLEAN":
                if result == True:
                    resolved_value = 1
                else:
                    resolved_value = 0
            elif field.type == "STRING":
                resolved_value = "\"{0}\"" \
                                 .format(result)

            clips_fields.append("\t(" + str(field.field_name) + " " + \
                                str(resolved_value) + ")")

        clips_fact += "\n".join(clips_fields) + ")"
        return clips_fact



    def generate_one_clips_fact(self, json_object, add_as=FactGenType.RESP_FROM_WEB):
        """ Generate single CLIPS fact from given single parsed 
            JSON object originating from web service's RESPONSE!

        Parameters
        ----------
        json_object : object
            Parsed JSON object

        Details
        -------
        - We define lambda func which extracts 'response_one_json_path' 
        field from given field object.
        - We feed the generic CLIPS fact generator with JSON object and 
        this lambda function.

        Returns
        -------
        str
            Generated single CLIPS fact definition statement
        """
        
        def check_existance(field):
            if add_as == FactGenType.RESP_FROM_WEB and \
            hasattr(field, "response_one_json_path") and \
            field.response_one_json_path != None and \
            field.response_one_json_path != "":
                return field.response_one_json_path
            else:
                return "$." + field.field_name

        json_path_func = lambda field : check_existance(field)
        return self.generate_clips_fact(json_object, json_path_func)



    def generate_multiple_clips_facts(self, json_object, array_len, add_as=FactGenType.RESP_FROM_WEB):
        """ Generate multiple CLIPS facts from given parsed JSON array
            of object originating from web service's RESPONSE!

        Parameters
        ----------
        json_object : object-array
            Parsed JSON array

        Details
        -------
        - We define lambda func which extracts 'response_mul_json_path' 
        field from given field object.
        - We feed the generic CLIPS fact generator with JSON object and
        this lambda function.

        Returns
        -------
        facts: list[str]
            Generated array of CLIPS fact definition statements
        """

        def check_existance(field):
            if add_as == FactGenType.RESP_FROM_WEB and \
            hasattr(field, "response_mul_json_path") and \
            field.response_mul_json_path != None and \
            field.response_mul_json_path != "":
                return field.response_mul_json_path
            else:
                return "$[{index}]." + field.field_name

        facts = []
        for i in range(0, array_len):
            json_path_func = lambda field : self.fill_data_map(
                                                check_existance(field),
                                                index=i)
            clips_fact = self.generate_clips_fact(json_object, 
                                                  json_path_func)
            facts.append(clips_fact)
        return facts



    # API OPERATIONS SECTION 
    ################################################################

    def fill_data_map(self, url_map, **kwargs):
        """ Generates real URL by filling given URL with provided dict data

        Parameters
        ----------
        url_map : str
            URL map is regular URL string containing '{variable_name}' 
            in places of real key data
        **kwargs: dict
            Dictionary of pairs 'variable_name: value'

        Details
        -------
        Here we use regular expression matcher to find all occurences 
        like '{variable_name}'.
        
        Returns
        -------
        1 : int
            If number of provided variables does not match number of 
            variables in url_map
        url_map : str
            Built real url
        """

        url_fields = []
        for m in re.finditer(r"\{(((?!\{|\}).)*)\}", url_map):
            url_fields.append(m.group(1))
        
        if len(url_fields) != len(kwargs.items()):
            message = "Failed to fill url map '{0}'. " \
                      "Insufficient number of arguments. " \
                      "Expected {1}, but found {2}" \
                      .format(url_map, 
                              len(url_fields), 
                              len(kwargs.items()))
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)

        for key, value in kwargs.items():
            pattern = re.compile("\{" + key + "\}")
            url_map = re.sub(pattern, str(value), url_map)
        
        return url_map



    def check_if_dsd_provides_web_op(self, operation):
        if not hasattr(self.dsd, 'apis'):
            line, col = self.dsd._tx_parser \
                        .pos_to_linecol(self.dsd._tx_position)
            message = "Data source '{0}' does not provide web operations." \
                      .format(self.dsd.model_id)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        if not hasattr(self.dsd.apis, operation):
            line, col = self.dsd._tx_parser \
                        .pos_to_linecol(self.dsd.apis._tx_position)
            message = "Data source '{0}' does not provide '{1}' operation." \
                      .format(self.dsd.model_id, operation)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)


    def get_primary_key_field(self):
        for field in self.dsd.fields:
            if field.use_as == "\"primary-key\"":
                return field


    def construct_query(self, **kwargs):
        """ Constructs search query with provided data - dict

        Parameters
        ----------
        **kwargs: dict
            Dictionary of pairs 'query_field: value'

        Details
        -------
        First we define default search query, then we override 
        them with given fields
        
        Returns
        -------
        default_kwargs : dict
            Constructed search query in form of dictionary

        Raises
        ------
        AkashicError
            If query field is not defined in given data source definition
        """

        self.check_if_dsd_provides_web_op("read_multiple")

        default_kwargs = {
            
            self.dsd.apis.read_multiple.page_index_url_placement: \
                self.dsd.apis.read_multiple.default_page_index,
            self.dsd.apis.read_multiple.page_row_count_url_placement: \
                self.dsd.apis.read_multiple.default_page_row_count,

            self.dsd.apis.read_multiple.search_fields_url_placement:    "",
            self.dsd.apis.read_multiple.search_strings_url_placement:   "",
            self.dsd.apis.read_multiple.sort_field_url_placement: \
                self.get_primary_key_field().field_name,
            self.dsd.apis.read_multiple.sort_order_url_placement:       "ASC"
        }

        # Check if field url placements are right
        for key, value in kwargs.items():
            if key in default_kwargs:
                default_kwargs[key] = value
            else:
                line, col = \
                    self.dsd._tx_parser \
                    .pos_to_linecol(self.dsd.apis.read_multiple._tx_position)
                message = "Query field {0} is not defined " \
                          "in data source definition." \
                          .format(key)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

        return default_kwargs



    def create(self, json_object, **kwargs):
        """ Constructs 'create' web service request, as specified in DSD

        Parameters
        ----------
        json_object: object
            Parsed JSON array
        **kwargs: dict
            Dictionary of data used to fill URL map

        Details
        -------
        1. We if all check field types are right
        2. We fill the URL map
        3. We call data featcher to execute request
        
        Returns
        -------
        parsed JSON object
            Web service response as parsed JSON object
        
        Raises
        ------
        AkashicError
            If DSD does not provide this web operations
        """

        self.check_if_dsd_provides_web_op("create")
       
        self.checker.check_field_types(
            use_json_as="request", 
            operation="create", 
            json_object=json_object
        )
        
        url_map = self.dsd.apis.create.url_map
        url = self.fill_data_map(url_map, **kwargs)
        
        # We set required JSON header
        result = self.fetcher.create(
            url, 
            json_object, 
            {"Content-Type": "application/json"}
        )
        return json.loads(result)



    def read_one(self, **kwargs):
        """ Constructs 'read_one' web service request,
            as specified in DSD

        Parameters
        ----------
        **kwargs: dict
            Dictionary of data used to fill URL map

        Details
        -------
        1. We fill the URL map
        2. We call data featcher to execute request
        
        Returns
        -------
        parsed JSON object
            Web service response as parsed JSON object
        
        Raises
        ------
        AkashicError
            If DSD does not provide this web operations
        """

        self.check_if_dsd_provides_web_op("read_one")

        url_map = self.dsd.apis.read_one.url_map
        url = self.fill_data_map(url_map, **kwargs)
        
        result = self.fetcher.read_one(url, {})
        return json.loads(result)
    


    def read_multiple(self, **kwargs):
        """ Constructs 'read_multiple' web service request,
            as specified in DSD 

        Parameters
        ----------
        **kwargs: dict
            Dictionary of data used to fill URL map

        Details
        -------
        1. We fill the URL map
        2. We call data featcher to execute request
        
        Returns
        -------
        parsed JSON object
            Web service response as parsed JSON object
        
        Raises
        ------
        AkashicError
            If DSD does not provide this web operations
        """

        self.check_if_dsd_provides_web_op("read_multiple")

        url_map = self.dsd.apis.read_multiple.url_map
        url = self.fill_data_map(url_map, **self.construct_query(**kwargs))
        
        result = self.fetcher.read_multiple(url, {})
        return json.loads(result)



    def update(self, json_object, **kwargs):
        """ Constructs 'update' web service request, as specified in DSD

        Parameters
        ----------
        json_object: object
            Parsed JSON array
        **kwargs: dict
            Dictionary of data used to fill URL map

        Details
        -------
        1. We if all check field types are right
        2. We fill the URL map
        3. We call data featcher to execute request
        
        Returns
        -------
        parsed JSON object
            Web service response as parsed JSON object
        
        Raises
        ------
        AkashicError
            If DSD does not provide this web operations
        """

        self.check_if_dsd_provides_web_op("update")
        
        self.checker.check_field_types(
            use_json_as="request", 
            operation="update", 
            json_object=json_object
        )
        
        url_map = self.dsd.apis.update.url_map
        url = self.fill_data_map(url_map, **kwargs)
        
        # We set required JSON header
        result = self.fetcher.update(
            url, 
            json_object, 
            {"Content-Type": "application/json"}
        )
        return json.loads(result)



    # TODO: There might be problem if response is empty
    def delete(self, **kwargs):
        """ Constructs 'delete' web service request, as specified in DSD

        Parameters
        ----------
        **kwargs: dict
            Dictionary of data used to fill URL map

        Details
        -------
        1. We fill the URL map
        2. We call data featcher to execute request
        
        Returns
        -------
        parsed JSON object
            Web service response as parsed JSON object
        
        Raises
        ------
        AkashicError
            If DSD does not provide this web operations
        """

        self.check_if_dsd_provides_web_op("delete")

        url_map = self.dsd.apis.delete.url_map
        url = self.fill_data_map(url_map, **kwargs)
        
        result = self.fetcher.delete(url, {})
        return ""