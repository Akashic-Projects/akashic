
import clips
from clips.agenda import Agenda



class EnvProvider(object):
    """ EnvProvider class

    This class gives us access to new CLIPS enviroment and enables to add / remove 
    CLIPS tempaltes and facts.
    """

    # TODO: Implement data queues
    # TODO: Request to add data (by the rule)
    # TODO: Request to remove data after it has expired (by the rule)


    def __init__(self):
        """ EnvProvider constructor method

        Create new CLIPS enviroment
        """

        self.env = clips.Environment()
        self.data_bridge = None

        self.time_bridge = None

    
    def set_data_bridge(self, data_bridge):
        self.data_bridge = data_bridge
        self.env.define_function(self.data_bridge.create_func)
        self.env.define_function(self.data_bridge.return_func)


    def set_time_bridge(self, time_bridge):
        self.time_bridge = time_bridge
        self.env.define_function(self.time_bridge.str_to_time)
        self.env.define_function(self.time_bridge.time_to_str)
        self.env.define_function(self.time_bridge.sub_times)

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