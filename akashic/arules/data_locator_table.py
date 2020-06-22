
from enum import Enum


class Template(object):
    """ Template class

    This class represents single CLIPS template / data source model
    """

    def __init__(self):
        """ Template constructor method

        Set name to None. Init fields dictionary.
        """

        self.name = None
        self.fields = {}



class Field(object):
    """ Field class

    This class represents single CLIPS fact inside of CLIPS template:
    name and variable name
    """

    def __init__(self):
        """ Field constructor method

        Set field name to None. 
        Set variable name to None.
        Set data provider field to None.
        """

        self.name = None
        self.var_name = None
        self.dp_field = None



class DataLocatorTable(object):
    """ DataLocatorTable class

        Class that contains all usages of data locators and variables 
        ascribed to them.
    """

    def __init__(self):
        """ DataLocatorTable constructor method

        Init table as dictionary
        """

        self.table = {}



    def add(self, template_name, field_name, var_name, dp_field):
        """ Adds data locator to the table, 
            pair [tempalte_name][field_name] : var_name

        Parameters
        ----------
        template_name : str
            Name of the referenced template
        field_name : str
            Name of the referenced field inside of referenced template
        var_name : str
            Name of the variable used to reference given template and field
        dp_field : object
            Field object from specific data provider
        """

        if template_name not in self.table:
            self.table[template_name] = Template()
            t = self.table[template_name]
            t.name = template_name
        else:
            t = self.table[template_name]

        if field_name not in t.fields:
            f = Field()
            f.name = field_name
            f.var_name = var_name
            f.dp_field = dp_field

            t.fields[field_name] = f

    

    def lookup(self, template_name, field_name):
        """ Searches for template-field entry in data locator table

        Parameters
        ----------
        template_name : str
            Name of the referenced template
        field_name : str
            Name of the referenced field inside of referenced template
        
        Returns
        -------
        Field object
            If data locator is found
        None
            If data locator is not found
        """

        if template_name in self.table:
            if field_name in self.table[template_name].fields:
                return self.table[template_name].fields[field_name]
        
        return None


    def __str__(self):
        val_array = []
        for template_name, template in self.table.items():
            val_array.append("Template name: " + template_name)
            for field_name, field in template.fields.items():
                val_array.append("\tField name: " + field_name)
                val_array.append("\t\t Var name: " + field.var_name)
                val_array.append("\t\t dp_field name: " + 
                                    field.dp_field.field_name)
        
        return "\n".join(val_array)