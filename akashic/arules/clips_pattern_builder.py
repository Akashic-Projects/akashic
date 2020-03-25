
from akashic.arules.data_locator_table import DataLocatorTable, TableType

from akashic.exceptions import SemanticError


# Needs to checks template and field names against given data_providers 
class CLIPSPatternBuilder(object):

    def build_regular_pattern(self, data_locator_table):
        clips_statement_list = []

        for template_name, template in data_locator_table.tables[TableType.TMP].items():
            clips_statement = "(" + template_name + " "

            clips_field_list = []
            for field_name, field in template.fields.items():
                clips_field_list.append("(" + field_name + " " + field.var_name  + ")")
                
            clips_statement += " ".join(clips_field_list) + ")"
            clips_statement_list.append(clips_statement)

        return clips_statement_list

    
    #TODO: handle special conditional elements (exists, forall, ...)
    def build_special_pattern(self, data_locator_table, expression):
        number_of_templates = len(data_locator_table.tables[TableType.TMP].items())
        if number_of_templates > 1:
            raise SemanticError("Total number of different templates referenced inside of single conditional statement(except for 'test') must be 1. {0} given.".format(number_of_templates))

        clips_statement_list = []

        for template_name, template in data_locator_table.tables[TableType.TMP].items():
            clips_statement = "(" + template_name + " "

            clips_field_list = []

            field_list = [ (k, v) for k, v in template.fields.items() ]
            for i in range(0, len(field_list) - 1):
                field_name = field_list[i][0]
                field = field_list[i][1]
                clips_field_list.append("(" + field_name + " " + field.var_name  + ")")
            
            # Build special field
            field_name = field_list[len(field_list) - 1][0]
            field = field_list[len(field_list) - 1][1]
            clips_field_list.append("(" + field_name + " " + field.var_name + "&:" + expression  + ")")

            clips_statement += " ".join(clips_field_list) + ")"
            clips_statement_list.append(clips_statement)
        
        return clips_statement_list[0]