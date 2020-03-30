from textx import metamodel_from_file
from textx.export import metamodel_export, model_export

from os.path import join, dirname
from enum import Enum

from akashic.arules.variable_table import VariableTable
from akashic.arules.data_locator_table import DataLocatorTable, TableType

from akashic.arules.clips_pattern_builder import CLIPSPatternBuilder

from akashic.exceptions import SemanticError


class DataType(Enum):
    WORKABLE = 1
    VARIABLE = 2
    STATEMENT = 3
    SPECIAL = 4
    NOTHING = 5

#TODO: Need to add DataType: STRING_VAR, INT_VAR, FLOAT_VAR, BOOL_VAR 
#-> podatke vuci iz data_providera


# Should be transpiler
class RulesInterpreter(object):

    def __init__(self, data_providers):
        self.data_providers = data_providers
        self.variable_table = VariableTable()
        self.data_locator_table = DataLocatorTable()
        self.clips_command_list = []

        # Keep track of used variables in this array
        self.data_locator_vars = []

        processors = {
            'RHSStatement': self.rhs_statement,
            'SpecialBinaryLogicExpression': self.special_binary_logic_expression,
            'SpecialLogicExpressionFactor': self.special_logic_expression_factor,
            'SpecialSingularLogicExpression': self.special_singular_logic_expression,
            'TestSingularLogicExpression': self.test_singular_logic_expression,
            'NegationExpression': self.negation_expression,
            'LogicExpression': self.logic_expression,
            'CompExpression': self.comp_expression,
            'PlusMinusExpr': self.plus_minus_expr,
            'MulDivExpr': self.mul_div_expr,
            'SqrExpr': self.sqr_expr,
            'Factor': self.factor,
            'DataLocator': self.data_locator,
            'VARIABLE': self.variable
        }

        this_folder = dirname(__file__)
        self.meta_model = metamodel_from_file(join(this_folder, 'meta_model.tx'), debug=False)
        self.meta_model.register_obj_processors(processors)

        #Get builder classes
        self.clips_pattern_builder = CLIPSPatternBuilder()

        self.rule = None


    def load(self, akashic_rule):
        # TODO: Need to catch this exception!!!
        self.rule = self.meta_model.model_from_str(akashic_rule)


    # For testing -> extracting data after processing
    def print_clips_commands(self):
        print("\n\nCLIPS Commands:")
        print()
        for c in self.clips_command_list:
            print(str(c))
        
        print()


    def translate(self, value):
        if value.__class__ == bool:
            if value == True:
                return "TRUE"
            else:
                return "FALSE"
        else:
            return value



    def rotate_used_data_locator_vars(self):
        for var_name in self.data_locator_vars:
            for template_name, template in self.data_locator_table.tables[TableType.TMP].items():
                for field_name, field in template.fields.items():
                    if field.var_name == var_name:
                        to_add = ("", DataType.NOTHING)
                        gen_var_name = self.variable_table.add_helper_var(to_add)
                        field.var_name = gen_var_name

                        for vn, var_value in self.variable_table.table.items():
                            var_value.value = (var_value.value[0].replace(var_name, gen_var_name), var_value.value[1])

                            var_value.used_variables = [gen_var_name if uv == var_name else uv for uv in var_value.used_variables]





    def rhs_statement(self, rhss):
        if rhss.stat.__class__.__name__ == "VARIABLE_INIT":
            self.variable_table.add_named_var(rhss.stat.var_name, self.translate(rhss.stat.expr), self.data_locator_vars)
            self.data_locator_vars = []
        elif rhss.stat.__class__.__name__ == "ASSERTION":
            print("Assertion done.")
            



    def special_binary_logic_expression(self, binary):
        # if no explicit conditional element is given use 'test'
        if len(binary.operands) < 2:
            if binary.operands[0][1] == DataType.STATEMENT:
                # Build clips commands
                clips_commands = self.clips_pattern_builder.build_regular_pattern(self.data_locator_table)
                self.clips_command_list.extend(clips_commands)
                self.clips_command_list.append("(test " + binary.operands[0][0] + ")")
            elif binary.operands[0][1] == DataType.SPECIAL:
                self.clips_command_list.append(binary.operands[0][0])

        else:
            ops = []
            for i in range(0, len(binary.operands)):
                if binary.operands[i][1] == DataType.STATEMENT:
                    # Build clips command
                    clips_command = self.clips_pattern_builder.build_special_pattern(self.data_locator_table, self.data_locator_vars, binary.operands[i][0])
                    ops.append(clips_command) 

                    # Rotate defined variables for next special expression
                    self.rotate_used_data_locator_vars()
                    self.data_locator_vars = []

                elif binary.operands[i][1] == DataType.SPECIAL:
                    ops.append(binary.operands[i][0])

            result = ops[0]
            for i in range(1, len(binary.operands)):
                result = "(" + binary.operator[i-1] + " " + result + " " + ops[i] + ")"

            self.clips_command_list.append(result)



    def special_logic_expression_factor(self, factor):
        return factor.value
    


    def special_singular_logic_expression(self, singular):
        # Because we use return as (value, DataType)
        if singular.operand[1] != DataType.STATEMENT:
            raise SemanticError("{0} must be statement. {1} given.".format(singular.operator, singular.operand[1].name))

        print("From special_singular_logic_expression: " + str(self.data_locator_vars))
        # Build clips command
        clips_command = self.clips_pattern_builder.build_special_pattern(self.data_locator_table, self.data_locator_vars, singular.operand[0])

        # Rotate defined variables for next special expression
        self.rotate_used_data_locator_vars()
        self.data_locator_vars = []

        # Return CLIPS command
        return ("(" + singular.operator + " " + clips_command + ")", DataType.SPECIAL)



    def test_singular_logic_expression(self, test):
        # Because we use return as (value, DataType)
        if test.operand[1] != DataType.STATEMENT:
            raise SemanticError("Test must be statement. {0} given.".format(test.operand[1]))

        # Build clips commands
        clips_commands = self.clips_pattern_builder.build_regular_pattern(self.data_locator_table)
        self.clips_command_list.extend(clips_commands)
        self.clips_command_list.append("(test " + test.operand[0] + ")")



    def negation_expression(self, neg):
        if neg.operator != "not":
            return neg.operand

        if neg.operand[1] == DataType.WORKABLE:
            val = not neg.operand[0]
            return (val, DataType.WORKABLE)
        else:
            return ('(' + 
                    neg.operator + ' ' + 
                    str(self.translate(neg.operand[0])) + ')',  DataType.STATEMENT)



    def logic_expression(self, logic):
        result = logic.operands[0]
        for i in range(1, len(logic.operands)):
            if result[1] == DataType.WORKABLE and logic.operands[i][1] == DataType.WORKABLE:
                val = None
                if logic.operator[i-1] == 'and':
                    val = result[0] and logic.operands[i][0]
                if logic.operator[i-1] == 'or':
                    val = result[0] or logic.operands[i][0]

                result = (val, DataType.WORKABLE)
            else:
                result = ('(' + 
                        logic.operator[i-1] + ' ' + 
                        str(self.translate(result[0])) + ' ' + 
                        str(self.translate(logic.operands[i][0])) + ')',  DataType.STATEMENT)
        return result



    #TODO: Comaring strings function -> it will be complex -> requires data_provider data about field
    def comp_expression(self, comp):
        result = comp.operands[0]
        for i in range(1, len(comp.operands)):
            if result[1] == DataType.WORKABLE and comp.operands[i][1] == DataType.WORKABLE:
                if ((result[0].__class__ == int or result[0].__class__ == float)
                and (comp.operands[i][0].__class__ == int or comp.operands[i][0].__class__ == float)
                or  (result[0].__class__ == str and comp.operands[i][0].__class__ == str)):
                    val = None
                    if comp.operator[i-1] == '<':
                        val = result[0] < comp.operands[i][0]
                    if comp.operator[i-1] == '>':
                        val = result[0] > comp.operands[i][0]
                    if comp.operator[i-1] == '<=':
                        val = result[0] <= comp.operands[i][0]
                    if comp.operator[i-1] == '>=':
                        val = result[0] >= comp.operands[i][0]
                    if comp.operator[i-1] == '==':
                        val = result[0] == comp.operands[i][0]
                    if comp.operator[i-1] == '!=':
                        val = result[0] != comp.operands[i][0]
                    
                    result = (val, DataType.WORKABLE)
            else:
                result = ('(' + 
                        comp.operator[i-1] + ' ' + 
                        str(self.translate(result[0])) + ' ' + 
                        str(self.translate(comp.operands[i][0])) + ')',  DataType.STATEMENT)
        return result



    def plus_minus_expr(self, plus_minus):
        result = plus_minus.operands[0]
        for i in range(1, len(plus_minus.operands)):
            if result[1] == DataType.WORKABLE and plus_minus.operands[i][1] == DataType.WORKABLE:
                if ((result[0].__class__ == int or result[0].__class__ == float)
                and (plus_minus.operands[i][0].__class__ == int or plus_minus.operands[i][0].__class__ == float)):
                    val = None
                    if plus_minus.operator[i-1] == '+':
                        val = result[0] + plus_minus.operands[i][0]
                    if plus_minus.operator[i-1] == '-':
                        val = result[0] - plus_minus.operands[i][0]
                    
                    result = (val, DataType.WORKABLE)
            else:
                result = ('(' + 
                        plus_minus.operator[i-1] + ' ' + 
                        str(result[0]) + ' ' + 
                        str(plus_minus.operands[i][0]) + ')',  DataType.STATEMENT)
        return result


    def mul_div_expr(self, mul_div):
        result = mul_div.operands[0]
        for i in range(1, len(mul_div.operands)):
            if result[1] == DataType.WORKABLE and mul_div.operands[i][1] == DataType.WORKABLE:
                if ((result[0].__class__ == int or result[0].__class__ == float)
                and (mul_div.operands[i][0].__class__ == int or mul_div.operands[i][0].__class__ == float)):    
                    val = None
                    if mul_div.operator[i-1] == '*':
                        val = result[0] * mul_div.operands[i][0]
                    if mul_div.operator[i-1] == '/':
                        val = result[0] / mul_div.operands[i][0]
                    
                    result = (val, DataType.WORKABLE)
            else:
                result = ('(' + 
                        mul_div.operator[i-1] + ' ' + 
                        str(result[0]) + ' ' + 
                        str(mul_div.operands[1][0]) + ')',  DataType.STATEMENT)

        return result



    def sqr_expr(self, sqr):
        result = sqr.operands[0]
        for i in range(1, len(sqr.operands)):
            if result[1] == DataType.WORKABLE and sqr.operands[i][1] == DataType.WORKABLE:
                if ((result[0].__class__ == int or result[0].__class__ == float)
                and (sqr.operands[i][0].__class__ == int or sqr.operands[i][0].__class__ == float)):

                    val = result[0] ** sqr.operands[i][0]
                    result = (val, DataType.WORKABLE)
            else:
                result = ('(** ' + 
                        str(result[0]) + ' ' + 
                        str(sqr.operands[i][0]) + ')',  DataType.STATEMENT)

        return result


    def factor(self, factor):
        if factor.value.__class__.__name__ in ["int", "float", "bool"]:
            return (factor.value, DataType.WORKABLE)
        elif factor.value.__class__.__name__ == "STRING_C":

            # Translate single quotation marks to double
            return (factor.value.val.replace("'", "\""), DataType.WORKABLE)
        else:
            # Enters here for variable and data_locator
            return factor.value



    def variable(self, var):
        var_entry = self.variable_table.lookup(var.var_name)
        if var_entry == None:
            raise SemanticError("Undefined variable {0}.".format(var.var_name))
        else:
            print("To add vars from : " + str(var.var_name))
            print("-------")
            self.data_locator_vars = list(set(self.data_locator_vars) | set(var_entry.used_variables))
            return var_entry.value



    def data_locator(self, data_locator):
        template_name = data_locator.template_conn_expr.templates[0]
        field_name = data_locator.field

        found_var_name = self.data_locator_table.lookup(template_name, field_name, TableType.TMP)
        if found_var_name:
            return (found_var_name, DataType.VARIABLE)
        else:
            gen_var_name = self.variable_table.add_helper_var(("", DataType.NOTHING))
            self.data_locator_vars.append(gen_var_name)
            self.data_locator_table.add(template_name, field_name, gen_var_name, TableType.TMP)
            return (gen_var_name, DataType.VARIABLE)
