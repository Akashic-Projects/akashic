
from os.path import join, dirname
import re

from textx import metamodel_from_file
from textx.export import metamodel_export, model_export
from textx.exceptions import TextXSyntaxError, TextXSemanticError

from akashic.exceptions import SyntacticError, SemanticError
from akashic.ads.data_checker import DataChecker
from akashic.ads.data_fetcher import DataFetcher

import json
from jsonpath_ng import jsonpath, parse



class DataProvider(object):
    """ DataProvider class

    It serves the purpose of mapping json data obtained 
    from specified web services to the clips templates and facts,
    using written specification called DSD (data source definition).
    """

    def __init__(self):
        """ DataProvider constructor method
        
        Main operation is loading the meta-model which describes and defines
        the grammar and structure of single data source definition.
        """

        this_folder = dirname(__file__)
        self.meta_model = metamodel_from_file(join(this_folder, 'meta_model.tx'), debug=False)
        self.dsd = None
        self.checker = None
        self.fetcher = None




    # LOADING & SETUP OPERATIONS SECTION 
    ################################################################
    def transalte_exception(self, ttype, line, col, message):
        """ Translates the textX exceptions to akashic exceptions
        
        Parameters
        ----------
        ttype : str
            Type of exception, possible values: "Syntax" & "Semantic"
        line : int
            Line number in data source definition where error was occured
        col : int
            Column number in data source definition where error was occured
        message : str
            Error message

        Raises
        ------
        SyntacticError
            If syntactic error has occured
        SemanticError
            If semantic error has occured
        """

        message = f"Detected: {ttype} error at line {line} and column {col}. \nMessage: " + message
        if ttype == "Syntax":
            raise SyntacticError(message)
        elif ttype == "Semantic":
            raise SemanticError(message)



    def load(self, dsd_string):
        """ Loads data-provider specification from given string

        Parameters
        ----------
        dsd_string : str
            String containing data source definition

        Raises
        ------
        SyntacticError
            If syntactic error has occured
        SemanticError
            If semantic error has occured
        """

        try:
            self.dsd = self.meta_model.model_from_str(dsd_string)
            return 0
        except TextXSyntaxError as syntaxError:
            self.transalte_exception("Syntax", syntaxError.line, syntaxError.col, syntaxError.message)
        except TextXSemanticError as semanticError:
            self.transalte_exception("Semantic", syntaxError.line, syntaxError.col, syntaxError.message)
    


    def setup(self):
        """ Setup DataChecker and DataFetcher based on loaded data source definition

        """
        self.checker = DataChecker(self.dsd)
        self.checker.check_url_mappings()

        self.fetcher = DataFetcher(self.dsd.auth_header, self.dsd.additional_headers)
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
            slot_defs.append("\t(slot " + str(field.field_name) + " (type " + str(resolved_type) + "))")
        
        clips_tempalte_def += "\n".join(slot_defs) + ")"

        return clips_tempalte_def



    def generate_clips_fact(self, json_object, json_path_func):
        """ Generic method that generates CLIPS fact from given parsed JSON object

        Parameters
        ----------
        json_object : object
            Parsed JSON object
        json_path_func: function
            Function which determines which JSON path expression will be used,
            possible functions: for single object & for multitude of objects inside of array

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

        for field in self.dsd.fields:
            jsonpath_expr = parse(str(json_path_func(field)))
            result = [match.value for match in jsonpath_expr.find(json_object)][0]

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
                resolved_value = f"\"{result}\""

            clips_fields.append("\t(" + str(field.field_name) + " " + str(resolved_value) + ")")

        clips_fact += "\n".join(clips_fields) + ")"
        return clips_fact



    def generate_one_clips_fact(self, json_object):
        """ Generate single CLIPS fact from given single parsed JSON object originating
        from web service's RESPONSE!

        Parameters
        ----------
        json_object : object
            Parsed JSON object

        Details
        -------
        We define lambda func which extracts 'response_one_json_path' field from given field object.
        We feed the generic CLIPS fact generator with JSON object and this lambda function.

        Returns
        -------
        str
            Generated single CLIPS fact definition statement
        """

        json_path_func = lambda field : field.response_one_json_path
        return self.generate_clips_fact(json_object, json_path_func)



    def generate_multiple_clips_facts(self, json_object, array_len):
        """ Generate multiple CLIPS facts from given parsed JSON array of object originating
        from web service's RESPONSE!

        Parameters
        ----------
        json_object : object-array
            Parsed JSON array

        Details
        -------
        We define lambda func which extracts 'response_mul_json_path' field from given field object.
        We feed the generic CLIPS fact generator with JSON object and this lambda function.

        Returns
        -------
        facts: list[str]
            Generated array of CLIPS fact definition statements
        """

        facts = []
        for i in range(0, array_len):
            json_path_func = lambda field : self.fill_data_map(field.response_mul_json_path, index=i)
            clips_fact = self.generate_clips_fact(json_object, json_path_func)
            facts.append(clips_fact)
        return facts




    # API OPERATIONS SECTION 
    ################################################################
    def fill_data_map(self, url_map, **kwargs):
        """ Generates real URL by filling given URL with provided dict data

        Parameters
        ----------
        url_map : str
            URL map is regular URL string containing '{variable_name}' in places of real key data
        **kwargs: dict
            Dictionary of pairs 'variable_name: value'

        Details
        -------
        Here we use regular expression matcher to find all occurences like '{variable_name}'.
        
        Returns
        -------
        1 : int
            If number of provided variables does not match number of variables in url_map
        url_map : str
            Built real url
        """

        url_fields = []
        for m in re.finditer(r"\{(((?!\{|\}).)*)\}", url_map):
            url_fields.append(m.group(1))
        
        if len(url_fields) != len(kwargs):
            return 1

        for key, value in kwargs.items():
            pattern = re.compile("\{" + key + "\}")
            url_map = re.sub(pattern, str(value), url_map)
        
        return url_map



    def construct_query(self, **kwargs):
        """ Constructs search query with provided data - dict

        Parameters
        ----------
        **kwargs: dict
            Dictionary of pairs 'search_field: value'

        Details
        -------
        First we define default search query, then we override them with given fields
        
        Returns
        -------
        default_kwargs : dict
            Constructed search query in form of dictionary
        """
        # TODO: This must be universal, all default settings in dsd model
        default_kwargs = {
            "pageIndex": 1,
            "pageRowCount": 5,
            "searchFields": "",
            "searchStrings": "",
            "sortField": "",
            "sortOrder": ""
        }

        for key, value in kwargs.items():
            default_kwargs[key] = value
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
        """
       
        self.checker.check_field_types(use_json_as="request", operation="create", json_object=json_object)
        
        url_map = self.dsd.apis.create.url_map
        url = self.fill_data_map(url_map, **kwargs)
        
        # We set required JSON header
        result = self.fetcher.create(url, json_object, {"Content-Type": "application/json"})
        return json.loads(result)



    def read_one(self, **kwargs):
        """ Constructs 'read_one' web service request, as specified in DSD 

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
        """

        url_map = self.dsd.apis.read_one.url_map
        url = self.fill_data_map(url_map, **kwargs)
        
        result = self.fetcher.read_one(url, {})
        return json.loads(result)
    


    def read_multiple(self, **kwargs):
        """ Constructs 'read_multiple' web service request, as specified in DSD 

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
        """

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
        """
        
        self.checker.check_field_types(use_json_as="request", operation="update", json_object=json_object)
        
        url_map = self.dsd.apis.update.url_map
        url = self.fill_data_map(url_map, **kwargs)
        
        # We set required JSON header
        result = self.fetcher.update(url, json_object, {"Content-Type": "application/json"})
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
        """

        url_map = self.dsd.apis.delete.url_map
        url = self.fill_data_map(url_map, **kwargs)
        
        result = self.fetcher.delete(url, {})
        return json.loads(result)