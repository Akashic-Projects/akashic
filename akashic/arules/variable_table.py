
import akashic.exceptions as ae
from enum import Enum


class Entry(object):
    def __init__(self):
        self.name = None
        self.value = None
        self.used_variables = []


class VariableTable(object):
    def __init__(self):
        self.gen_var_index = 0
        self.table = {}


    def add_named_var(self, name, value, used_vars):
        e = Entry()
        e.name = name
        e.value = value
        e.used_variables = used_vars

        self.table[name] = e
        return e.name


    def add_helper_var(self, value):
        gen_name = "?v" + str(self.gen_var_index)
        self.gen_var_index += 1

        e = Entry()
        e.name = gen_name
        e.value = value
        e.used_variables = []
       
        
        self.table[gen_name] = e
        return gen_name


    def set_var_value(self, name, value):
        if self.lookup(name):
            self.table[name].value = value
        else:
            return 1


    def lookup(self, name):
        if name in self.table:
            return self.table[name]
        else:
            return None