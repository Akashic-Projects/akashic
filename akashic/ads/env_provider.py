
import clips
from clips.agenda import Agenda

from akashic.bridges.data_bridge import DataBridge
from akashic.bridges.time_bridge import TimeBridge

from akashic.exceptions import AkashicError, ErrType


class EnvProvider(object):
    """ EnvProvider class

    This class gives us access to new CLIPS enviroment 
    and enables to add / remove CLIPS tempaltes and facts.
    """

    # TODO: Implement data queues
    # TODO: Request to add data (by the rule)
    # TODO: Request to remove data after it has expired (by the rule)


    def __init__(self, data_providers, custom_bridges=None):
        """ EnvProvider constructor method

        Create new CLIPS enviroment
        """

        self.env = clips.Environment()

        self.data_providers = data_providers
        self.bridges = {}
        self.functions = {}
        self.built_in_functions = ["not", "count", "str"]

        # Init default bridges
        data_bridge = DataBridge(self.data_providers, self)
        time_bridge = TimeBridge()

        # Init default brigdes functions
        self.import_bridge(data_bridge)
        self.import_bridge(time_bridge)

        # Import custom bridges
        self.import_custom_bridges(custom_bridges)



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
            self.import_bridge(bridge)



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

    
    def insert_rule(self, rule):
        """ Inserts new CLIPS rule into the enviroment
        
        Parameters
        ----------
        rule : str
            CLIPS rule in string form
        """
        
        self.env.build(rule)

    
    def run(self):
        #agenda = Agenda(self.env)
        self.env.run()