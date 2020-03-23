from enum import Enum


class Template(object):
    def __init__(self):
        self.name = None
        self.fields = {}

class Field(object):
    def __init__(self):
        self.name = None
        self.var_name = None

class TableType(Enum):
    REGULAR = 0
    TMP = 1

class DataLocatorTable(object):
    def __init__(self):
        self.tables = {}
        self.tables[TableType.REGULAR] = {}
        self.tables[TableType.TMP] = {}


    def add(self, data_locator, var_name, table_type):
        template_name = data_locator.template_conn_expr.templates[0]
        field_name = data_locator.field

        if template_name not in self.tables[table_type]:
            self.tables[table_type][template_name] = Template()
            t = self.tables[table_type][template_name]
            t.name = template_name
        else:
            t = self.tables[table_type][template_name]

        f = Field()
        f.name = field_name
        f.var_name = var_name

        t.fields[field_name] = f

    
    def lookup(self, data_locator, table_type):
        template_name = data_locator.template_conn_expr.templates[0]
        field_name = data_locator.field

        if template_name in self.tables[table_type]:
            if field_name in self.tables[table_type][template_name].fields:
                return self.tables[table_type][template_name].fields[field_name]
        
        return None

    
    def reset_table(self, table_type):
        self.tables[table_type] = {}
