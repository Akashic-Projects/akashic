
from akashic.arules.data_locator_table import DataLocatorTable

from akashic.exceptions import AkashicError, ErrType


class ClipsStatementBuilder(object):
    """ CLIPSPatternBuilder class

    We use this class to build complex CLIPS statements. 
    """

    def __init__(self):
        self.count_operation_var_counter = 0


    def build_regular_dl_patterns(self, data_locator_table):
        """ Builds CLIPS statement without *Predicate Constraints*
        
        Details
        -------
        We analyse data_locator_table and create simple SLIPS pattern(s)

        Returns
        -------
        list
            List of clips statemtns in string form
        """

        clips_statement_list = []

        for template_name, template in data_locator_table.table.items():
            clips_statement = "(" + template_name + " "

            clips_field_list = []
            for field_name, field in template.fields.items():
                clips_field_list.append("(" + field_name + " " + field.var_name  + ")")
                
            clips_statement += " ".join(clips_field_list) + ")"
            clips_statement_list.append(clips_statement)

        return clips_statement_list



    def count_different_templates(self, data_locator_table, used_vars):
        t_set = set()
        print("\nBEGIN count")
        for template_name, template in data_locator_table.table.items():
            for field_name, field in template.fields.items():
                print("inside dlt: " + field.var_name)
                if field.var_name in used_vars:
                    t_set.add(template_name)
        print("END count\n")
        return len(t_set)
    

    def get_template(self, data_locator_table, used_vars):
        for template_name, template in data_locator_table.table.items():
            for field_name, field in template.fields.items():
                if field.var_name in used_vars:
                    return template

    
    #TODO: What happens when empty statement is given?
    def build_special_pattern(self, data_locator_table, used_vars, expression, expression_object):
        l = self.count_different_templates(data_locator_table, used_vars)
        print("NUM of used vars for DLs: " + str(len(used_vars)))
        print("NUM of diff templates: " + str(l))
        print("NUM of reg tempaltes: " + str(len(data_locator_table.table.items())))
        if self.count_different_templates(data_locator_table, used_vars) > 1:
            line, col = self.dsd._tx_parser.pos_to_linecol(expression_object._tx_position)
            message = f"Total number of different templates referenced inside of single conditional statement(except for 'test') must be 1. {l} given."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        clips_statement_list = []

        for template_name, template in data_locator_table.table.items():
            clips_statement = "(" + template_name + " "

            clips_field_list = []

            field_list = [ (k, v) for k, v in template.fields.items() ]
            for i in range(0, len(field_list) - 1):
                field_name = field_list[i][0]
                field = field_list[i][1]
                if field.var_name in used_vars:
                    clips_field_list.append("(" + field_name + " " + field.var_name  + ")")
            
            # Build special field
            field_name = field_list[len(field_list) - 1][0]
            field = field_list[len(field_list) - 1][1]
            if field.var_name in used_vars:
                clips_field_list.append("(" + field_name + " " + field.var_name + "&:" + expression  + ")")

            clips_statement += " ".join(clips_field_list) + ")"
            clips_statement_list.append(clips_statement)
        
        return clips_statement_list[0]



    # TODO: Add support for more templates
    def build_count_pattern(self, data_locator_table, used_vars, expression):
        clips_template_refs = []

        """example: (length$ (find-all-facts ((?f student)) (eq ?f:gruppa ?gr)))"""
        for template_name, template in data_locator_table.table.items():
            template_var = "?" + template_name.lower() + str(self.count_operation_var_counter)
            clips_template_refs.append("(" + template_var + " " + template_name + ")")

            field_list = [ (k, v) for k, v in template.fields.items() ]
            for i in range(0, len(field_list)):
                field_name = field_list[i][0]
                field = field_list[i][1]
                if field.var_name in used_vars:
                    replacement = template_var + ":" + field_name
                    expression = expression.replace(field.var_name, replacement)

        return "(length$ (find-all-facts (" + " ".join(clips_template_refs) + ") " + expression + "))"


    
    def build_string_comparison_expr(self, op1, op1_type, op2, op2_type, operator):
        
        if op1_type == "STRING" and op2_type == "STRING":

            second_part = '(str-compare ' + str(op1) + ' ' + str(op2) + ')' + '0)'
            if operator == '<':
                val = '(< ' + second_part
            elif operator == '>':
                val = '(> ' + second_part
            elif operator == '<=':
                val = '(<= ' + second_part
            elif operator == '>=':
                val = '(>= ' + second_part
            elif operator == '=':
                val = '(= ' + second_part
            elif operator == '!=':
                val = '(!= ' + second_part
            
            return val

        return '(' + operator + ' ' + str(op1) + ' ' + str(op2) + ')'