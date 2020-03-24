from akashic.arules.data_locator_table import DataLocatorTable, TableType

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
    def build_special_pattern():
        pass