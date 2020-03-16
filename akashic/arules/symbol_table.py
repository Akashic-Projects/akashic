import akashic.exceptions as ae
from enum import Enum


class Entry(object):
    def __init__(self):
        self.translation = None
        self.value = None
        self.type = None


class SymbolTable(object):
    def __init__(self):
        # Initial position is (0,0)
        self.gen_var_index = 0
        self.table = {}
        self.assertion = None


    def add_named_var(self, name, value, typee):
        if name in self.table:
            raise ae.VariableAlreadyDefinedError

        e = Entry()
        e.name = name
        e.translated = name
        e.value = value
        e.type = typee
        self.table[name] = e


    def add_helper_var(self, value, typee):
        gen_name = "?v" + str(self.gen_var_index)
        self.gen_var_index += 1

        e = Entry()
        e.name = gen_name
        e.translated = gen_name
        e.value = value
        e.type = typee
        self.table[name] = e

        return gen_name


    def lookup(self, name):
        if name in self.table:
            return self.table[name]
        else:
            return None


    def set_assertion(self, value):
        if self.assertion == None:
            return 1
        
        self.assertion = value


    def get_assertion(self):
        return self.assertion