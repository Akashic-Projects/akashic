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


# Should be transpiler
class RulesInterpreter(object):

    def __init__(self, data_providers):
        self.data_providers = data_providers
        self.variable_table = VariableTable()
        self.data_locator_table = DataLocatorTable()
        self.clips_command_list = []

        processors = {
            'RHSStatement': self.rhs_statement,
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


    #TODO: Create Count function
    def rhs_statement(self, rhss):
        if rhss.func.__class__.__name__ == "EXISTS_KW":
            # Because we use return as (value, DataType)
            if (rhss.expr[1] != DataType.STATEMENT):
                raise SemanticError("Test must be statement. {0} given.".format(rhss.expr[1].name))
            self.clips_command_list.append(rhss.expr[0])


        elif rhss.func.__class__.__name__ == "TEST_KW":
            # Because we use return as (value, DataType)
            if (rhss.expr[1] != DataType.STATEMENT):
                raise SemanticError("Test must be statement. {0} given.".format(rhss.expr[1].name))

            clips_commands = self.clips_pattern_builder.build_regular_pattern(self.data_locator_table)
            self.clips_command_list.extend(clips_commands)

            self.clips_command_list.append("(test " + rhss.expr[0] + ")")

            # Transfer to regular and clear up the TMP data locator table
            self.data_locator_table.transfer_from_to(TableType.TMP, TableType.REGULAR)
            self.data_locator_table.reset_table(TableType.TMP)

        elif rhss.func.__class__.__name__ == "VARIABLE_INIT":
            self.variable_table.add_named_var(rhss.func.var_name, rhss.expr)



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
        if len(logic.operands) < 2:
            return logic.operands[0]

        if logic.operands[0][1] == DataType.WORKABLE and logic.operands[1][1] == DataType.WORKABLE:
            val = None
            if logic.operator[0] == 'and':
                val = logic.operands[0][0] and logic.operands[1][0]
            if logic.operator[0] == 'or':
                val = logic.operands[0][0] or logic.operands[1][0]

            return (val, DataType.WORKABLE)
        else:
            return ('(' + 
                    logic.operator[0] + ' ' + 
                    str(self.translate(logic.operands[0][0])) + ' ' + 
                    str(self.translate(logic.operands[1][0])) + ')',  DataType.STATEMENT)


    #TODO: Comaring strings function
    def comp_expression(self, comp):
        if len(comp.operands) < 2:
            return comp.operands[0]

        if comp.operands[0][1] == DataType.WORKABLE and comp.operands[1][1] == DataType.WORKABLE:
            if ((comp.operands[0][0].__class__ == int or comp.operands[0][0].__class__ == float)
            and (comp.operands[1][0].__class__ == int or comp.operands[1][0].__class__ == float)
            or  (comp.operands[0][0].__class__ == str and comp.operands[1][0].__class__ == str)):
                val = None
                if comp.operator[0] == '==':
                    val = comp.operands[0][0] == comp.operands[1][0]
                if comp.operator[0] == '!=':
                    val = comp.operands[0][0] != comp.operands[1][0]
                if comp.operator[0] == '<':
                    val = comp.operands[0][0] < comp.operands[1][0]
                if comp.operator[0] == '>':
                    val = comp.operands[0][0] > comp.operands[1][0]
                if comp.operator[0] == '<=':
                    val = comp.operands[0][0] <= comp.operands[1][0]
                if comp.operator[0] == '>=':
                    val = comp.operands[0][0] >= comp.operands[1][0]

                return (val, DataType.WORKABLE)
        else:
            return ('(' + 
                    comp.operator[0] + ' ' + 
                    str(self.translate(comp.operands[0][0])) + ' ' + 
                    str(self.translate(comp.operands[1][0])) + ')',  DataType.STATEMENT)



    def plus_minus_expr(self, plus_minus):
        if len(plus_minus.operands) < 2:
            return plus_minus.operands[0]

        if plus_minus.operands[0][1] == DataType.WORKABLE and plus_minus.operands[1][1] == DataType.WORKABLE:
            if ((plus_minus.operands[0][0].__class__ == int or plus_minus.operands[0][0].__class__ == float)
            and (plus_minus.operands[1][0].__class__ == int or plus_minus.operands[1][0].__class__ == float)):
                val = None
                if plus_minus.operator[0] == '+':
                    val = plus_minus.operands[0][0] + plus_minus.operands[1][0]
                if plus_minus.operator[0] == '-':
                    val = plus_minus.operands[0][0] - plus_minus.operands[1][0]
                
                return (val, DataType.WORKABLE)
        else:
            return ('(' + 
                    plus_minus.operator[0] + ' ' + 
                    str(plus_minus.operands[0][0]) + ' ' + 
                    str(plus_minus.operands[1][0]) + ')',  DataType.STATEMENT)



    def mul_div_expr(self, mul_div):
        if len(mul_div.operands) < 2:
            return mul_div.operands[0]
        
        if mul_div.operands[0][1] == DataType.WORKABLE and mul_div.operands[1][1] == DataType.WORKABLE:
            if ((mul_div.operands[0][0].__class__ == int or mul_div.operands[0][0].__class__ == float)
            and (mul_div.operands[1][0].__class__ == int or mul_div.operands[1][0].__class__ == float)):    
                val = None
                if mul_div.operator[0] == '*':
                    val = mul_div.operands[0][0] * mul_div.operands[1][0]
                if mul_div.operator[0] == '/':
                    val = mul_div.operands[0][0] / mul_div.operands[1][0]
                
                return (val, DataType.WORKABLE)
        else:
            return ('(' + 
                    mul_div.operator[0] + ' ' + 
                    str(mul_div.operands[0][0]) + ' ' + 
                    str(mul_div.operands[1][0]) + ')',  DataType.STATEMENT)



    def sqr_expr(self, sqr):
        if len(sqr.operands) < 2:
            return sqr.operands[0]
      
        if sqr.operands[0][1] == DataType.WORKABLE and sqr.operands[1][1] == DataType.WORKABLE:
            if ((sqr.operands[0][0].__class__ == int or sqr.operands[0][0].__class__ == float)
            and (sqr.operands[1][0].__class__ == int or sqr.operands[1][0].__class__ == float)):

                val = sqr.operands[0][0] ** sqr.operands[1][0]
                return (val, DataType.WORKABLE)
        else:
            return ('(** ' + 
                    str(sqr.operands[0][0]) + ' ' + 
                    str(sqr.operands[1][0]) + ')',  DataType.STATEMENT)



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
            return var_entry.value



    def data_locator(self, data_locator):
        template_name = data_locator.template_conn_expr.templates[0]
        field_name = data_locator.field

        found_var_name1 = self.data_locator_table.lookup(template_name, field_name, TableType.TMP)
        found_var_name2 = self.data_locator_table.lookup(template_name, field_name, TableType.REGULAR)
        if found_var_name1:
            return (found_var_name1, DataType.VARIABLE)
        elif found_var_name2:
            return (found_var_name2, DataType.VARIABLE)
        else:
            gen_var_name = self.variable_table.add_helper_var("")
            print("NESTO: " + gen_var_name)
            self.data_locator_table.add(template_name, field_name, gen_var_name, TableType.TMP)
            return (gen_var_name, DataType.VARIABLE)
