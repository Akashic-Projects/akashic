import clips


class EnvProvider(object):

    def __init__(self):
        self.env = clips.Environment()


    def define_template(self, template):
        return self.env.build(template)


    def undefine_template(self, tempalte_name):
        template = self.env.find_template(tempalte_name)
        template.undefine()

    
    def insert_fact(self, fact):
        return self.env.assert_string(fact)


    def retract_fact(self):
        pass


    