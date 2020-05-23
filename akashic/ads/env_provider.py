
import clips
from clips.agenda import Agenda

from akashic.ads.bridge import create_func


class EnvProvider(object):
    """ EnvProvider class

    This class gives us access to new CLIPS enviroment and enables to add / remove 
    CLIPS tempaltes and facts.
    """

    # TODO: Implement data queues
    # TODO: Request to add data (by the rule)
    # TODO: Request to remove data after it has expired (by the rule)
    # TODO: Implement live security system using akashic
    def __init__(self):
        """ EnvProvider constructor method

        Create new CLIPS enviroment
        """

        self.env = clips.Environment()
        self.env.define_function(create_func)

       

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

    


    