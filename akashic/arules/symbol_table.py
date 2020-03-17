
import akashic.exceptions as ae
from enum import Enum


class Entry(object):
    def __init__(self):
        self.name = None
        self.translated_name = None
        self.value = None


class SymbolTable(object):
    def __init__(self):
        # Initial position is (0,0)
        self.gen_var_index = 0
        self.table = {}


    def add_named_var(self, name, value):
        e = Entry()
        e.name = name
        e.translated_name = name
        e.value = value

        self.table[name] = e
        return e.name


    def add_helper_var(self, value):
        gen_name = "?v" + str(self.gen_var_index)
        self.gen_var_index += 1

        e = Entry()
        e.name = gen_name
        e.translated_name = gen_name
        e.value = value
        
        self.table[name] = e
        return e.name


    def lookup(self, name):
        if name in self.table:
            return self.table[name]
        else:
            return None