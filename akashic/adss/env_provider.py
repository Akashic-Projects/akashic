import clips


class EnvProvider(object):

    def __init__(self):
        self.env = clips.Environment()

        # Implement data queues
        # Request to add data (by the rule)
        # Request to remove data after it has expired (by the rule)
        # Implement live security system using akashic


    def define_template(self, template):
        return self.env.build(template)


    def undefine_template(self, tempalte_name):
        template = self.env.find_template(tempalte_name)
        template.undefine()

    
    def insert_fact(self, fact):
        return self.env.assert_string(fact)


    def retract_fact(self):
        pass


    