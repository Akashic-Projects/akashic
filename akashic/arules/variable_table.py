

from enum import Enum

class VarType(Enum):
    def __str__(self):
        return str(self.name)
        
    SYMBOLIC     = 1
    BINDING      = 2
    FACT_ADDRESS = 3


class Entry(object):
    """ Entry class

    This class represents single entry inside of variable table.
    """

    def __init__(self):
        self.name = None
        self.value = None
        self.used_variables = []
        self.var_type = None



class VariableTable(object):
    """ VariableTable class

    This class Is wrapper and storage of symbolic and data locator variables.
    It provides methods for searching, adding names and auto-generted variables
    and their values, along with list of variables that are used in expression
    that is value of defined variable. 
    """

    def __init__(self):
        """ VariableTable constructor method

        We set starting index of generated variables names.
        We init the variable table - in form of dictionary.
        """

        self.gen_var_index = 0
        self.table = {}


    def next_var_name(self):
        gen_name = "?v" + str(self.gen_var_index)
        self.gen_var_index += 1

        return gen_name


    def add_named_var(self, name, value, used_vars, var_type=VarType.SYMBOLIC):
        """ Adds named variable to the table

        Parameters
        ----------
        name : str
            Name of the variable
        value : str
            Generated CLIPS expression that is value of given variable
        used_vars : list
            List of variable names used in given CLIPS expression

       
        Returns
        -------
        str
            Name of generated variable
        """

        e = Entry()
        e.name = name
        e.value = value
        e.used_variables = used_vars
        e.var_type = var_type

        self.table[name] = e
        return e.name



    def add_helper_var(self, value, var_type=VarType.SYMBOLIC):
        """ Adds helper variable to the table - variable with
            unique generated name

        Parameters
        ----------
        value : str
            Generated CLIPS expression that is value of given variable
       
        Returns
        -------
        str
            Generated name of generated variable
        """

        e = Entry()
        e.name = self.next_var_name()
        e.value = value
        e.used_variables = []
        e.var_type = var_type
       
        
        self.table[e.name] = e
        return e.name



    def set_var_value(self, name, value):
        """ Assignes value to specific variable

        Parameters
        ----------
        name : str
            Name of the variable
        value : str
            New generated CLIPS expression that is value of given variable
       
        Returns
        -------
        1
            If variable with given name is not present in table
        0
            If all is ok
        """

        if self.lookup(name):
            self.table[name].value = value
            return 0
        else:
            return 1



    def lookup(self, name):
        """ Searches for the variable with given name in variable table

        Parameters
        ----------
        name : str
            Name of the variable
       
        Returns
        -------
        object
            If wariable is found, return variable table entry
        None
            If variable is not found
        """

        if name in self.table:
            return self.table[name]
        else:
            return None