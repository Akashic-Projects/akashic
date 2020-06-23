
import clips
from clips.agenda import Agenda
from clips.error import CLIPSError

from akashic.ads.data_provider import DataProvider
from akashic.arules.transpiler import Transpiler

from akashic.system.dsds.rule_to_block import RULE_TO_BLOCK
from akashic.system.dsds.rule_to_remove import RULE_TO_REMOVE
from akashic.system.dsds.assistance_on import ASSISTANCE_ON
from akashic.system.rules.remove_rule import REMOVE_RULE

from akashic.bridges.data_bridge import DataBridge
from akashic.bridges.time_bridge import TimeBridge

from akashic.meta_models.dsd import DSD_META_MODEL
from akashic.meta_models.rule import RULE_META_MODEL

from akashic.exceptions import AkashicError, ErrType


class EnvProvider(object):
    """ EnvProvider class

    This class gives us access to new CLIPS enviroment 
    and enables to add / remove CLIPS tempaltes and facts.
    """


    def __init__(self, custom_bridges=[]):
        """ EnvProvider constructor method

        Create new CLIPS enviroment
        """

        # Define holders for data_providers, bridges, functions, 
        # built-it funcs, return func data
        self.data_providers = []
        self.bridges = {}
        self.functions = {}
        self.built_in_functions = ["not", "count", "str"]
        self.return_data = []
       
        # Create new empty CLIPS enviroment
        self.env = clips.Environment()
        

        # Prepare DSD meta-model and fill RULE meta model
        self.dsd_mm = DSD_META_MODEL
        mm_fill = self.import_custom_bridges(custom_bridges)
        self.rule_mm = self.fill_rule_meta_model(*mm_fill)

        # Build system data providers and define it's tempaltes
        self.data_providers = self.build_system_data_providers()
        self.define_templates_of_dsds(self.data_providers)

        # Insert system bridges
        self.insert_system_bridges()

        # Insert system rules
        self.insert_system_rules()
        


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
                          .format(data_provider.model_id)
                raise AkashicError(message, 0, 0, ErrType.SYSTEM)

        # Add to the list
        self.data_providers.append(data_provider)
        
        self.define_templates_of_dsds([data_provider])
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
                      .format(dsd_model_id)
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)
        
        self.data_providers.remove(to_remove)
        self.refresh_data_proviers_in_bridges()

        try:
            self.undefine_template(dsd_model_id)
        except CLIPSError as ce:
            print(ce)
            message = "Facts of type '{0}' are still present " \
                      "in enviroment. Please remove all facts " \
                      "related to that model, then try again." \
                      .format(dsd_model_id)
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)


    def build_system_data_providers(self):
        # Setup system data providers
        rtb_data_provider = DataProvider(self)
        rtb_data_provider.load(RULE_TO_BLOCK)
        rtb_data_provider.setup()

        rtr_data_provider = DataProvider(self)
        rtr_data_provider.load(RULE_TO_REMOVE)
        rtr_data_provider.setup()

        ao_data_provider = DataProvider(self)
        ao_data_provider.load(ASSISTANCE_ON)
        ao_data_provider.setup()

        return [rtb_data_provider, rtr_data_provider, ao_data_provider]


    
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

        # Add bridge functions to the rules_meta_model 
        # and build ad save meta model
        zero_arg_fcs = []
        one_arg_fcs = []
        onep_arg_fcs = []
        for bridge in custom_bridges:
            for f in bridge.exposed_functions:
                if f["num_of_args"] == 0:
                    zero_arg_fcs.append("\t'" + f["function"].__name__ + "'")
                elif f["num_of_args"] == 1:
                    one_arg_fcs.append("\t'" + f["function"].__name__ + "'")
                else:
                    onep_arg_fcs.append("\t'" + f["function"].__name__ + "'")

        return [zero_arg_fcs, one_arg_fcs, onep_arg_fcs]



    def fill_rule_meta_model(self, zero_arg_fcs, one_arg_fcs, onep_arg_fcs):
        zero = ""
        one = ""
        onep = ""
        if zero_arg_fcs != []:
            zero =  '|\n' + ' |\n'.join(zero_arg_fcs)
        if one_arg_fcs != []:
            one = '|\n' + ' |\n'.join(one_arg_fcs)
        if onep_arg_fcs != []:
            onep = '|\n' + ' |\n'.join(onep_arg_fcs)
        return RULE_META_MODEL.format(zero, one, onep)



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
        rule_name : str
            CLIPS rule name
        rule : str
            CLIPS rule in string form
        """
        try:
            self.check_rule_name(rule_name)
            self.env.build(rule)
        except CLIPSError as ce:
            print(ce)
            message = "Error occured while adding rule '{0}', " \
                      "Rule with same name MAY be already present." \
                      .format(rule_name)
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)



    def remove_rule(self, rule_name):
        """ Removes CLIPS rule from the enviroment
        
        Parameters
        ----------
        rule_name : str
            CLIPS rule name
        """

        try:
            rule = self.env.find_rule(rule_name)
        except:
            message = "Rule with name '{0}' is not found. " \
                      .format(rule_name)
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)
        if not rule:
            message = "Rule with name '{0}' is not found. " \
                      .format(rule_name)
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)
        if not rule.deletable:
            message = "Rule with name '{0}' is not deletable. " \
                      .format(rule_name)
            raise AkashicError(message, 0, 0, ErrType.SYSTEM)

        rule.undefine()



    def execute(self, clips_command):
        self.env.eval(clips_command)
    


    def run(self):
        #Clear data and query data of previous run
        self.return_data = []

        self.env.run()


    def get_template_names(self):
        template_names = []
        for t in self.env.templates():
            template_names.append(t.name)
        return template_names

    
    def get_rule_names(self):
        rule_names = []
        for r in self.env.rules():
            rule_names.append(r.name)
        return rule_names


    def get_facts(self):
        facts = []
        for f in self.env.facts():
            facts.append(str(f))
        return facts
            