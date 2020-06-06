
import clips
from clips.agenda import Agenda

from akashic.ads.data_provider import DataProvider
from akashic.arules.transpiler import Transpiler

from akashic.system.dsds.rule_to_block import RULE_TO_BLOCK
from akashic.system.dsds.rule_to_remove import RULE_TO_REMOVE
from akashic.system.rules.remove_rule import REMOVE_RULE

from akashic.bridges.data_bridge import DataBridge
from akashic.bridges.time_bridge import TimeBridge

from akashic.exceptions import AkashicError, ErrType


class EnvProvider(object):
    """ EnvProvider class

    This class gives us access to new CLIPS enviroment 
    and enables to add / remove CLIPS tempaltes and facts.
    """


    def __init__(self, data_providers=[], custom_bridges=[]):
        """ EnvProvider constructor method

        Create new CLIPS enviroment
        """

        self.env = clips.Environment()

        self.data_providers = [*data_providers, 
                               *self.build_system_providers()]
        self.define_templates_of_dsds(self.data_providers)

        self.custom_bridges = custom_bridges
        self.bridges = {}
        self.functions = {}
        self.built_in_functions = ["not", "count", "str"]

        # Insert system bridges
        self.insert_system_bridges()

        # Insert custom bridges
        self.import_custom_bridges(self.custom_bridges)

        # Insert system rules
        self.insert_system_rules()

        # Store return function data
        self.return_data = []


    def clear_return_data(self):
        self.return_data = []


    def get_return_data(self):
        return self.return_data

    
    def add_return_data(self, entry):
        self.return_data.append(entry)
    

    def insert_system_bridges(self):
        # Init default bridges
        data_bridge = DataBridge(self.data_providers, self)
        time_bridge = TimeBridge()

        # Init default brigdes functions
        self.import_bridge(data_bridge)
        self.import_bridge(time_bridge)

    

    def refresh_data_proviers_in_bridges(self):
        self.bridges["DataBridge"]. \
            refresh_data_providers(self.data_providers)



    def insert_data_provider(self, data_provider):
        # Check if model_id is unique
        for dp in self.data_providers:
            if dp.dsd.model_id == data_provider.dsd.model_id:
                message = "Data provider with model id '{0}' " \
                          "already exists. Please change data " \
                          "provider model id and try again." \
                          .format(rule_name)
                raise AkashicError(message, 0, 0, ErrType.SYSTEM)

        # Add to the list
        self.data_providers.append(data_provider)
        self.refresh_data_proviers_in_bridges()


    
    def remove_data_provider(self, dsd_model_id):
        to_remove = None
        for dp in self.data_providers:
            if dp.dsd.model_id == dsd_model_id:
                to_remove = dp
        
        if to_remove == None:
            message = "Data provider with model id '{0}' " \
                      "cannot be found. Therefore it cannot " \
                      "be removed." \
                      .format(rule_name)
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)
        else:
            self.data_providers.remove(to_remove)
            self.refresh_data_proviers_in_bridges()


    def build_system_providers(self):
        # Setup system data providers
        rtb_data_provider = DataProvider()
        rtb_data_provider.load(RULE_TO_BLOCK)
        rtb_data_provider.setup()

        rtr_data_provider = DataProvider()
        rtr_data_provider.load(RULE_TO_REMOVE)
        rtr_data_provider.setup()

        return [rtb_data_provider, rtr_data_provider]


    
    def insert_system_rules(self):
        transpiler = Transpiler(self)
        transpiler.load(REMOVE_RULE)
        self.insert_rule(transpiler.rule.rule_name, transpiler.tranpiled_rule)



    def define_templates_of_dsds(self, data_providers):
        for dp in data_providers:
            clips_template = dp.generate_clips_template()
            self.define_template(clips_template)



    def import_bridge(self, bridge):
        if bridge.__class__.__name__ in self.bridges:
            message = "Bridge with class name '{0}' " \
                      "already exists." \
                      .format(bridge.__class__.__name__)
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)

        if not hasattr(bridge, "exposed_functions"):
            message = "Bridge with class name '{0}' is malformed. " \
                      "'exposed_functions' array is not found." \
                      .format(bridge.__class__.__name__)

        for f in bridge.exposed_functions:
            if (not "function" in f) or (not "num_of_args" in f) or \
            (not "return_type" in f):
                message = "Function entry is malformed. " \
                          "'exposed_functions' array must contain" \
                          "dictionary with 'function' and 'num_of_args' " \
                          "and 'return_type' fields."
                raise AkashicError(message, 0, 0, ErrType.SYSTEM)

            if f["function"].__name__ in self.functions:
                message = "Function with name '{0}' is already " \
                          "defined in bridge with class name '{1}'." \
                          .format(f["function"].__name__,
                                  self.functions[f["function"].__name__] \
                                  ["bridge"].__class__.__name__)
                raise AkashicError(message, 0, 0, ErrType.SYSTEM)

            if f["function"].__name__ in self.built_in_functions:
                message = "Function with name '{0}' is already " \
                          "defined as built-in function." \
                          .format(f["function"].__name__)
                raise AkashicError(message, 0, 0, ErrType.SYSTEM)

            self.functions[f["function"].__name__] = {
                "bridge": bridge,
                "num_of_args": f["num_of_args"],
                "return_type": f["return_type"]
            }
            self.bridges[bridge.__class__.__name__] = bridge
            self.env.define_function(f["function"])
            


    def import_custom_bridges(self, custom_bridges):
        if custom_bridges == None:
            return 0
        for bridge in custom_bridges:
            self.import_bridge(custom_bridge)


    def define_template(self, template):
        """ Defines / inserts new CLIPS template into the enviroment
        
        Parameters
        ----------
        template : str
            CLIPS template in string form
        
        Returns
        -------
        CLIPS lib response
        """

        return self.env.build(template)



    def undefine_template(self, tempalte_name):
        """ Undefines / removes CLIPS template from the enviroment
        
        Parameters
        ----------
        tempalte_name : str
            CLIPS template name
        """

        template = self.env.find_template(tempalte_name)
        template.undefine()


    
    def insert_fact(self, fact):
        """ Inserts new CLIPS fact into the enviroment
        
        Parameters
        ----------
        fact : str
            CLIPS fact in string form
        
        Returns
        -------
        CLIPS lib response
        """
        return self.env.assert_string(fact)



    def retract_fact(self):
        """ Removes CLIPS fact from the enviroment
    
        """

        pass



    def check_rule_name(self, rule_name):
        for rule in self.env.rules():
            if rule.name == rule_name:
                message = "Rule with name '{0}' already exists. " \
                          "Please change rule name and try again." \
                          .format(rule_name)
                raise AkashicError(message, 0, 0, ErrType.SYSTEM)



    def insert_rule(self, rule_name, rule):
        """ Inserts new CLIPS rule into the enviroment
        
        Parameters
        ----------
        rule : str
            CLIPS rule in string form
        """

        self.check_rule_name(rule_name)
        
        self.env.build(rule)



    def execute(self, clips_command):
        self.env.eval(clips_command)
    


    def run(self):
        #agenda = Agenda(self.env)
        self.env.run()