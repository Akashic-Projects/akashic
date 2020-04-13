from textx import metamodel_from_file
from textx.export import metamodel_export, model_export

from os.path import join, dirname
from enum import Enum

from akashic.arules.variable_table import VariableTable
from akashic.arules.data_locator_table import DataLocatorTable
from akashic.arules.clips_statement_builder import ClipsStatementBuilder

from akashic.exceptions import SemanticError

from akashic.util.type_converter import clips_to_py_type, py_to_clips_type, translate_if_c_bool
from akashic.util.type_resolver import resolve_expr_type


#TODO: Need to add DataType: STRING_VAR, INT_VAR, FLOAT_VAR, BOOL_VAR 
#-> podatke vuci iz data_provider-a
class DataType(Enum):
    """ DataType enum class

    We use this class to define type of data generated inside of transpiler loop
    """

    WORKABLE    = 1
    VARIABLE    = 2
    EXPRESSION  = 3
    SPECIAL     = 4
    NOTHING     = 5



class Transpiler(object):
    """ Transpiler class

    We use this class to transpile Akashic rule into the CLIPS rule.
    """

    def __init__(self, data_providers):
        """ Transpiler constructor method
        
        Details
        -------
        1. Imports created data_providers.
        2. Creates new Variable table (used for managing symbolic and real variables).
        3. Creates new DataLocatorTable (used for namaging fact data referencing inside of rule).
        4. Setups model processor functions - transpiler loop.
        5. Loads Akashic meta-model.
        6. Loads CLIPS Pattern Builder module.
        """

        self.data_providers = data_providers
        self.variable_table = VariableTable()
        self.data_locator_table = DataLocatorTable()
        self.clips_command_list = []

        # Keep track of used variables in this array
        self.data_locator_vars = []

        processors = {
            'LHSStatement': self.lhs_statement,
            'SpecialBinaryLogicExpression': self.special_binary_logic_expression,
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

        # Get builder classes
        self.clips_statement_builder = ClipsStatementBuilder()

        self.rule = None



    # TODO: Need to catch this exception!!!
    def load(self, akashic_rule):
        """ Loads akashic_rule from given string

        Parameters
        ----------
        akashic_rule : str
            String containing Akashic rule

        Raises
        ------
        None
        """
        
        self.rule = self.meta_model.model_from_str(akashic_rule)



    def rotate_used_data_locator_vars(self):
        """ Function rotates used data locator variables

        Details
        -------
        1. We go through variables used to reference CLIPS facts (data locators (DL) - in Akashic terminology)
        2. We through data locator table to get every entry using current DL variable
        3. We generate new variable in varialbe table (with new name - 'name rotation')
        4. We reassign this new variable to mentioned entry
        
        5. We go through all defined variables* and replace old helper varialbe names with new ones.
        6. We go through list of variables refenrenced in statement of * and replace their names also.
        """

        for var_name in self.data_locator_vars:
            for template_name, template in self.data_locator_table.table.items():
                for field_name, field in template.fields.items():
                    if field.var_name == var_name:
                        to_add = ("", DataType.NOTHING)
                        gen_var_name = self.variable_table.add_helper_var(to_add)
                        field.var_name = gen_var_name

                        for vn, var_value in self.variable_table.table.items():
                            var_value.value = (var_value.value[0].replace(var_name, gen_var_name), var_value.value[1])

                            var_value.used_variables = [gen_var_name if uv == var_name else uv for uv in var_value.used_variables]



    def lhs_statement(self, lhss):
        """ Processes left hand side (LHS) of the rule

        Parameters
        ----------
        lhss : object
            LHS object constructed by the textX by parsing Akashic rule based on predefined meta-model
        
        Details
        -------
        1. If statement represents variable definition / init then we add varaible name
        to the variable table (something like table of sumbols) along with value / defined expression
        and list of used DL variables in that expression. After adding to the variable list, we empty
        the data_locator_vars - list that contains current DL variables in use in last expression.

        2. Id statement represents assertion function. Then nothing... for now.. 
        """

        if lhss.stat.__class__.__name__ == "VARIABLE_INIT":
            # Check if WORKABLE and string -> add " " and build str-cmp expression
            self.variable_table.add_named_var(lhss.stat.var_name, self.translate_bool(lhss.stat.expr), self.data_locator_vars)
            self.data_locator_vars = []
        elif lhss.stat.__class__.__name__ == "ASSERTION":
            print("Assertion done.")
            


    def special_binary_logic_expression(self, binary):
        if len(binary.operands) < 2:
            self.clips_command_list.append(binary.operands[0][0])
        else:
            ops = []
            for i in range(0, len(binary.operands)):
                if binary.operands[i][1] == DataType.STATEMENT:
                    # Build clips command
                    clips_command = self.clips_statement_builder.build_special_pattern(self.data_locator_table, self.data_locator_vars, binary.operands[i][0])
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



    def special_singular_logic_expression(self, singular):
        # Because we use return as (value, DataType)
        if singular.operand[1] != DataType.STATEMENT:
            raise SemanticError("{0} must be statement. {1} given.".format(singular.operator, singular.operand[1].name))

        print("From special_singular_logic_expression: " + str(self.data_locator_vars))
        # Build clips command
        clips_command = self.clips_statement_builder.build_special_pattern(self.data_locator_table, self.data_locator_vars, singular.operand[0])

        # Rotate defined variables for next special expression
        self.rotate_used_data_locator_vars()
        self.data_locator_vars = []

        # Return CLIPS command
        return ("(" + singular.operator + " " + clips_command + ")", DataType.SPECIAL)


    # TODO: Here!!
    def test_singular_logic_expression(self, test):
        # Because we use return as (value, DataType)
        if test.operand[1] != DataType.EXPRESSION:
            raise SemanticError("Test must be statement. {0} given.".format(test.operand[1]))

        # Build clips commands
        clips_commands = self.clips_statement_builder.build_regular_dl_patterns(self.data_locator_table)
        self.clips_command_list.extend(clips_commands)
        self.clips_command_list.append("(test " + test.operand[0] + ")")



    def negation_expression(self, neg):
        result = neg.operand

        # Exit if operator is not present
        if neg.operator and neg.operator != "not":
            return result

        if result["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
            raise SemanticError("Operand of type INTEGER, FLOAT or BOOLEAN expected, {0} geven.".format(result["content_type"]))

        operator = neg.operator

        if result["content_type"] == DataType.WORKABLE:
            val = not result["content"]
            return {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": DataType.WORKABLE
                }

        else:
            val = '(' + operator + ' ' + 
                    str(translate_if_c_bool(result["content"])) + ')'

            # It is always bool
            resolved_c_type = "BOOLEAN"
            return {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": DataType.EXPRESSION
            }



    def logic_expression(self, logic):
        result = logic.operands[0]

        l = len(logic.operands)
        i = 1
        while i < l:
            current = logic.operands[i]

            if result["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
                raise SemanticError("Operand of type INTEGER, FLOAT or BOOLEAN expected, {0} geven.".format(result["content_type"]))
            if current["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
                raise SemanticError("Operand of type INTEGER, FLOAT or BOOLEAN expected, {0} geven.".format(result["content_type"]))

            operator = logic.operator[i-1]

            if (result["construct_type"]  == DataType.WORKABLE 
            and current["construct_type"] == DataType.WORKABLE):
                if operator == 'and':
                    val = result["content"] and current["content"]
                if operator == 'or':
                    val = result["content"] or current["content"]

                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": DataType.WORKABLE
                }

            else:
                val = '(' + operator + ' ' + 
                        str(translate_if_c_bool(result["content"])) + ' ' +
                        str(translate_if_c_bool(current["content"])) + ')'

                resolved_c_type = resolve_expr_type("logic", result["content_type"], current["content_type"])

                result = {
                    "content": val,
                    "content_type": resolved_c_type,
                    "construct_type": DataType.EXPRESSION
                }

            i += 1

        return result



    def comp_expression(self, comp):
        result = comp.operands[0]

        l = len(comp.operands)
        i = 1
        while i < l:
            current = comp.operands[i]

            if result["content_type"] not in ["INTEGER", "FLOAT", "STRING"]:
                raise SemanticError("Operand of type INTEGER, FLOAT or STRING expected, {0} geven.".format(result["content_type"]))
            if current["content_type"] not in ["INTEGER", "FLOAT", "STRING"]:
                raise SemanticError("Operand of type INTEGER, FLOAT or STRING expected, {0} geven.".format(result["content_type"]))

            # Resolve eq operaator
            if comp.operator[i-1] == '==':
                operator = '='
            else:
                operator = comp.operator[i-1]

            if (result["construct_type"]  == DataType.WORKABLE 
            and current["construct_type"] == DataType.WORKABLE)
            and ((result["content_type"] in ["INTEGER", "FLOAT"] and current["content_type"] in  ["INTEGER", "FLOAT"])
            or  (result["content_type"] == "STRING" and current["content_type"] == "STRING")):
                   
                if operator == '<':
                    val = result["content"] < current["content"]
                elif operator == '>':
                    val = result["content"] > current["content"]
                elif operator == '<=':
                    val = result["content"] <= current["content"]
                elif operator == '>=':
                    val = result["content"] >= current["content"]
                elif operator == '=':
                    val = result["content"] == current["content"]
                elif operator == '!=':
                    val = result["content"] + current["content"]
                
                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": DataType.WORKABLE
                }

            else:
                op1 = ""
                op2 = ""
                if result["content_type"] == "STRING" and result["construct_type"]  == DataType.WORKABLE:
                    op1 = "\"" + result["content"] + "\""
                else:
                    op1 = result["content"]

                if current["content_type"] == "STRING" and current["construct_type"]  == DataType.WORKABLE:
                    op2 = "\"" + current["content"] + "\""
                 else:
                    op2 = current["content"]
                    
                op1 = translate_if_c_bool(op1)
                op2 = translate_if_c_bool(op2)

                val = self.clips_statement_builder.build_string_comparison_expr(op1, op2, operator)
                resolved_c_type = resolve_expr_type("comp", result["content_type"], current["content_type"])

                # Check if type is resolved correctly
                if resolved_c_type > 0:
                    raise SemanticError("Incompatible operand types present in comparison expression.")

                result = {
                    "content": val,
                    "content_type": resolved_c_type,
                    "construct_type": DataType.EXPRESSION
                }

            i += 1

        return result



    def plus_minus_expr(self, plus_minus):
        result = plus_minus.operands[0]

        l = len(plus_minus.operands)
        i = 1
        while i < l:
            current = plus_minus.operands[i]

            if result["content_type"] not in ["INTEGER", "FLOAT"]:
                raise SemanticError("Operand of type INTEGER or FLOAT expected, {0} geven.".format(result["content_type"]))
            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                raise SemanticError("Operand of type INTEGER or FLOAT expected, {0} geven.".format(result["content_type"]))

            operator = plus_minus.operator[i-1]

            if (result["construct_type"]  == DataType.WORKABLE 
            and current["construct_type"] == DataType.WORKABLE):
                if operator == '+':
                    val = result["content"] + current["content"]
                elif operator == '-':
                    val = result["content"] - current["content"]
                    
                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": DataType.WORKABLE
                }

            else:
                val = '(' + operator + ' ' + str(result["content"]) + ' ' + str(current["content"]) + ')'
                resolved_c_type = resolve_expr_type("plus_minus", result["content_type"], current["content_type"])

                result = {
                    "content": val,
                    "content_type": resolved_c_type,
                    "construct_type": DataType.EXPRESSION
                }

            i += 1

        return result



    def mul_div_expr(self, mul_div):
        result = mul_div.operands[0]

        l = len(mul_div.operands)
        i = 1
        while i < l:
            current = mul_div.operands[i]

            if result["content_type"] not in ["INTEGER", "FLOAT"]:
                raise SemanticError("Operand of type INTEGER or FLOAT expected, {0} geven.".format(result["content_type"]))
            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                raise SemanticError("Operand of type INTEGER or FLOAT expected, {0} geven.".format(result["content_type"]))

            operator = mul_div.operator[i-1]

            if (result["construct_type"]  == DataType.WORKABLE 
            and current["construct_type"] == DataType.WORKABLE):
                if operator == '*':
                    val = result["content"] * current["content"]
                elif operator == '/':
                    val = result["content"] / current["content"]
                
                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": DataType.WORKABLE
                }

            else:
                val = '(' + operator + ' ' + str(result["content"]) + ' ' + str(current["content"]) + ')'
                resolved_c_type = resolve_expr_type("mul_div", result["content_type"], current["content_type"])

                result = {
                    "content": val,
                    "content_type": resolved_c_type,
                    "construct_type": DataType.EXPRESSION
                }

            i += 1

        return result



    def sqr_expr(self, sqr):
        result = sqr.operands[0]

        l = len(sqr.operands)
        i = 1
        while i < l:
            current = sqr.operands[i]
           
            if result["content_type"] not in ["INTEGER", "FLOAT"]:
                raise SemanticError("Operand of type INTEGER or FLOAT expected, {0} geven.".format(result["content_type"]))
            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                raise SemanticError("Operand of type INTEGER or FLOAT expected, {0} geven.".format(result["content_type"]))

            operator = '**'

            if (result["construct_type"]  == DataType.WORKABLE 
            and current["construct_type"] == DataType.WORKABLE):
                val = result["content"] ** current["content"]

                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": DataType.WORKABLE
                }

            else:
                val = '(' + operator + ' ' + str(result["content"]) + ' ' + str(current["content"]) + ')'
                resolved_c_type = resolve_expr_type("sqr", result["content_type"], current["content_type"])

                result = {
                    "content": val, 
                    "content_type": resolved_c_type,
                    "construct_type": DataType.EXPRESSION
                }

            i += 1

        return result



    def factor(self, factor):
        if factor.value.__class__.__name__ in ["int", "float", "bool"]:
            # If factor class is simple python type
            return {
                "content": factor.value, 
                "content_type": py_to_clips_type(factor.value.__class__),
                "construct_type": DataType.WORKABLE
            }

        elif factor.value.__class__.__name__ == "STRING_C":
            # Remove single quotation marks if factor class is string
            return {
                "content": factor.value.val.replace("'", ""), 
                "content_type": py_to_clips_type(str),
                "construct_type": DataType.WORKABLE
            }

        else:
            # Enters when factor class is: VARIABLE or DataLocator VALUE ENTRY
            return factor.value



    def variable(self, var):
        var_entry = self.variable_table.lookup(var.var_name)
        if var_entry == None:
            raise SemanticError("Undefined variable {0}.".format(var.var_name))
        else:
            # Add used variables from current variable to the list of globally used variables
            self.data_locator_vars = list(set(self.data_locator_vars) | set(var_entry.used_variables))
            return var_entry.value



    def data_locator(self, data_locator):
        # Get needed data
        template_name = data_locator.template_conn_expr.templates[0]
        field_name = data_locator.field

        # Search for existing entry in data locator table
        field = self.data_locator_table.lookup(template_name, field_name)
        if field and field.var_name:
            return {
                "content": field.var_name, 
                "content_type": field.dp_field.type,
                "construct_type": DataType.VARIABLE
            }

        else:
            # Checks field names against given data_providers
            found_data_provider = None
            for data_provider in self.data_providers:
                if data_provider.dsd.model_id == template_name:
                    found_data_provider = data_provider

            if found_data_provider == None:
                raise SemanticError("There is no data provider defined for template connection '{0}'.".format(template_name))
            
            found_dp_field = found_data_provider.field_lookup(field_name)

            if not found_dp_field:
                raise SemanticError("Template field '{0}' is not defined in data provider's template '{1}'".format(field_name, template_name))

            # Generate new variable and add new entry to the data locator table
            gen_var_name = self.variable_table.add_helper_var(("", DataType.NOTHING, found_dp_field.type))
            self.data_locator_vars.append(gen_var_name)
            self.data_locator_table.add(template_name, field_name, gen_var_name, found_dp_field)
            
            return {
                "content": gen_var_name,
                "content_type": found_dp_field.type,
                "construct_type": DataType.VARIABLE
            }
