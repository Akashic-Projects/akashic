from textx import metamodel_from_file
from textx.export import metamodel_export, model_export

from os.path import join, dirname
from enum import Enum

from akashic.arules.variable_table import VariableTable
from akashic.arules.data_locator_table import DataLocatorTable
from akashic.arules.clips_statement_builder import ClipsStatementBuilder

from akashic.exceptions import AkashicError, ErrType

from akashic.util.type_converter import clips_to_py_type, py_to_clips_type, translate_if_c_bool
from akashic.util.type_resolver import resolve_expr_type
from akashic.util.string_util import remove_quotes


#TODO: Need to add DataType: STRING_VAR, INT_VAR, FLOAT_VAR, BOOL_VAR 
#-> podatke vuci iz data_provider-a
class DataType(Enum):
    """ DataType enum class

    We use this class to define type of data generated inside of transpiler loop
    """

    WORKABLE    = 1
    VARIABLE    = 2
    EXPRESSION  = 3
    SPECIAL     = 4 # conditional statement
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
            'CountExpression': self.count_expression,
            'NegationExpression': self.negation_expression,
            'LogicExpression': self.logic_expression,
            'CompExpression': self.comp_expression,
            'PlusMinusExpr': self.plus_minus_expr,
            'MulDivExpr': self.mul_div_expr,
            'SqrExpr': self.sqr_expr,
            'Factor': self.factor,
            'DataLocator': self.data_locator,
            'VARIABLE': self.variable,

            'RHSStatement': self.rhs_statement,
            'CreateStatement': self.create_statement,
            'ReadOneStatement': self.read_one_statement,
            'ReadMultipleStatement': self.read_multiple_statement,
            'UpdateStatement': self.update_statement,
            'DeleteStatement': self.delete_statement,
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


# ----------------------------------------------------------------
# LEFT HAND SIDE SECTION
# ----------------------------------------------------------------

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
                        to_add = {
                            "content": "",
                            "content_type": field.dp_field.type,
                            "construct_type": DataType.NOTHING
                        }
                        gen_var_name = self.variable_table.add_helper_var(to_add)
                        field.var_name = gen_var_name

                        for vn, var_value in self.variable_table.table.items():

                            # This check is important - very!!
                            if var_value.value["construct_type"] != DataType.WORKABLE:
                                var_value.value["content"] = var_value.value["content"].replace(var_name, gen_var_name)

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

        print("name: " +  lhss.stat.__class__.__name__)

        if lhss.stat.__class__.__name__ == "VARIABLE_INIT":
            if self.variable_table.lookup(lhss.stat.var_name):
                line, col = self.dsd._tx_parser.pos_to_linecol(lhss.stat._tx_position)
                message = f"Variable '{lhss.stat.var_name}' is already defined."
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
            
            self.variable_table.add_named_var(
                lhss.stat.var_name, 
                lhss.stat.expr, 
                self.data_locator_vars
            )
            self.data_locator_vars = []
            print("Variable adding done.")

        elif lhss.stat.__class__.__name__ == "ASSERTION":
            print("Assertion done.")
        
        elif lhss.stat.__class__.__name__ == "FACT_ADDRESS":
            if self.variable_table.lookup(lhss.stat.var_name):
                line, col = self.dsd._tx_parser.pos_to_linecol(lhss.stat._tx_position)
                message = f"Variable '{lhss.stat.var_name}' is already defined."
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            self.variable_table.add_named_var(
                lhss.stat.var_name,
                lhss.stat.expr, 
                []
            )
            clips_address_pattern_command = lhss.stat.var_name + " <- " + lhss.stat.expr["content"]
            self.clips_command_list.append(clips_address_pattern_command)
            print("Address pattern adding done.")

        elif lhss.stat.__class__.__name__ == "CLIPS_CODE":
            clips_address_pattern_command = lhss.stat.clips_code
            self.clips_command_list.append(remove_quotes(clips_address_pattern_command))


    def special_binary_logic_expression(self, binary):
        if len(binary.operands) < 2:
            self.clips_command_list.append(binary.operands[0]["content"])
            return 0

        ops = []
        for i in range(0, len(binary.operands)):
            if binary.operands[i]["construct_type"] == DataType.SPECIAL:
                ops.append(binary.operands[i]["content"])
            else:
                line, col = self.dsd._tx_parser.pos_to_linecol(binary.operands[i]["_tx_position"])
                message = "AND-OR logic operation arguments must be of SPECIAL conditional statement type. {0} given."
                            .format(binary.operands[i]["construct_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
                

        result = ops[0]
        for i in range(1, len(binary.operands)):
            result = "(" + binary.operator[i-1] + " " + result + " " + ops[i] + ")"

        self.clips_command_list.append(result)

        return 0



    def special_singular_logic_expression(self, singular):
        if singular.operand["construct_type"] != DataType.EXPRESSION:
            line, col = self.dsd._tx_parser.pos_to_linecol(singular.operand["_tx_position"])
            message = "{0} operation argument must be expression. {1} given."
                .format(singular.operator, singular.operand["construct_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        print("DLV from special_singular_logic_expression: " + str(self.data_locator_vars))

        # Build clips regular command
        clips_command = self.clips_statement_builder.build_special_pattern(
            self.data_locator_table, 
            self.data_locator_vars, 
            singular.operand["content"],
            singular
        )

        t_name = None
        # Extract used template name
        for template_name, template in self.data_locator_table.table.items():
            t_name = template_name

        # Rotate defined variables for next special expression
        self.rotate_used_data_locator_vars()
        self.data_locator_vars = []

        # Return CLIPS command
        if not singular.operator:
            val = clips_command
        else:
            val = "(" + singular.operator + " " + clips_command + ")"

        return {
            "content": val, 
            "content_type": None,
            "construct_type": DataType.SPECIAL,
            "model_id": t_name
        }



    def test_singular_logic_expression(self, test):
        if test.operand["construct_type"] != DataType.EXPRESSION:
            line, col = self.dsd._tx_parser.pos_to_linecol(test.operand["_tx_position"])
            message = "TEST operation argument must be an EXPRESSION. {0} given."
                .format(test.operand["construct_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC))

        # Build clips commands
        clips_commands = self.clips_statement_builder.build_regular_dl_patterns(self.data_locator_table)
        self.clips_command_list.extend(clips_commands)
        self.clips_command_list.append("(test " + test.operand["content"] + ")")

        return 0


    def count_expression(self, countt):
        # Exit if operator is not present
        if not countt.operator:
            return countt.operand

        if countt.operand["construct_type"] != DataType.EXPRESSION:
            line, col = self.dsd._tx_parser.pos_to_linecol(countt.operand["_tx_position"])
            message =  "{0} operation argument must be expression. {1} given."
                .format(countt.operator, countt.operand["construct_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC))

        # Build count command if present
        clips_command = self.clips_statement_builder.build_count_pattern(
            self.data_locator_table, 
            self.data_locator_vars, 
            countt.operand["content"]
        )
    
        # Rotate defined variables for next special expression
        self.rotate_used_data_locator_vars()
        self.data_locator_vars = []

        # Return CLIPS command
        val = "(" + countt.operator + " " + clips_command + ")"
        resolved_c_type = "INTEGER"
        return {
            "content": val,
            "content_type": resolved_c_type,
            "construct_type": DataType.EXPRESSION
        }



    def negation_expression(self, neg):
        result = neg.operand

        # Exit if operator is not present
        if not neg.operator:
            return result

        if result["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
            line, col = self.dsd._tx_parser.pos_to_linecol(result["_tx_position"])
            message = "Negation operand of type INTEGER, FLOAT or BOOLEAN expected, {0} geven."
                .format(result["content_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC))

        operator = neg.operator

        if result["content_type"] == DataType.WORKABLE:
            val = not result["content"]
            return {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": DataType.WORKABLE
                }

        else:
            val = '(' + operator + ' ' + \
                    str(translate_if_c_bool(result["content"])) + ')'

            # It is always bool
            resolved_c_type = "BOOLEAN"
            return {
                    "content": val, 
                    "content_type": resolved_c_type,
                    "construct_type": DataType.EXPRESSION
            }



    def logic_expression(self, logic):
        result = logic.operands[0]

        l = len(logic.operands)
        i = 1
        while i < l:
            current = logic.operands[i]
            
            if result["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
                line, col = self.dsd._tx_parser.pos_to_linecol(result["_tx_position"])
                message = "Logic operand of type INTEGER, FLOAT or BOOLEAN expected, {0} geven."
                    .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

            if current["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
                line, col = self.dsd._tx_parser.pos_to_linecol(current["_tx_position"])
                message = "Logic operand of type INTEGER, FLOAT or BOOLEAN expected, {0} geven."
                    .format(current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

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
                val = '(' + operator + ' ' + \
                        str(translate_if_c_bool(result["content"])) + ' ' + \
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
                line, col = self.dsd._tx_parser.pos_to_linecol(result["_tx_position"])
                message = "Comparison operand of type INTEGER, FLOAT or STRING expected, {0} geven."
                    .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

            if current["content_type"] not in ["INTEGER", "FLOAT", "STRING"]:
                line, col = self.dsd._tx_parser.pos_to_linecol(current["_tx_position"])
                message = "Comparison operand of type INTEGER, FLOAT or STRING expected, {0} geven."
                    .format(current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

            # Resolve eq operaator
            if comp.operator[i-1] == '==':
                operator = '='
            else:
                operator = comp.operator[i-1]

            if ((result["construct_type"]  == DataType.WORKABLE 
            and current["construct_type"] == DataType.WORKABLE)
            and ((result["content_type"] in ["INTEGER", "FLOAT"] and current["content_type"] in  ["INTEGER", "FLOAT"])
            or  (result["content_type"] == "STRING" and current["content_type"] == "STRING"))):
                   
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

                op1_type = result["content_type"]
                op2_type = current["content_type"]

                val = self.clips_statement_builder.build_string_comparison_expr(op1, op1_type, op2, op2_type, operator)
                resolved_c_type = resolve_expr_type("comp", result["content_type"], current["content_type"])

                # Check if type is resolved correctly
                if resolved_c_type == 1:
                    line, col = self.dsd._tx_parser.pos_to_linecol(result["_tx_position"])
                    message = "Incompatible operand types present in comparison expression."
                    raise AkashicError(message, line, col, ErrType.SEMANTIC))

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
                line, col = self.dsd._tx_parser.pos_to_linecol(result["_tx_position"])
                message = "Addition or subtraction operand of type INTEGER or FLOAT expected, {0} geven."
                    .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))
               
            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = self.dsd._tx_parser.pos_to_linecol(current["_tx_position"])
                message = "Addition or subtraction operand of type INTEGER or FLOAT expected, {0} geven."
                    .format(current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

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
                line, col = self.dsd._tx_parser.pos_to_linecol(result["_tx_position"])
                message = "Multiplication or division operand of type INTEGER or FLOAT expected, {0} geven."
                    .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = self.dsd._tx_parser.pos_to_linecol(current["_tx_position"])
                message = "Multiplication or division operand of type INTEGER or FLOAT expected, {0} geven."
                    .format(current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

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
                line, col = self.dsd._tx_parser.pos_to_linecol(result["_tx_position"])
                message = "Exponentiation or root extraction operand of type INTEGER or FLOAT expected, {0} geven."
                    .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = self.dsd._tx_parser.pos_to_linecol(current["_tx_position"])
                message = "Exponentiation or root extraction operand of type INTEGER or FLOAT expected, {0} geven."
                    .format(current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

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
                "construct_type": DataType.WORKABLE,
                "_tx_position": factor._tx_position
            }

        elif factor.value.__class__.__name__ == "STRING_C":
            # Remove single quotation marks if factor class is string
            return {
                "content": remove_quotes(factor.value.val),
                "content_type": py_to_clips_type(str),
                "construct_type": DataType.WORKABLE,
                "_tx_position": factor._tx_position
            }

        else:
            # Enters when factor class is: VARIABLE or DataLocator VALUE ENTRY
            return factor.value



    def variable(self, var):
        var_entry = self.variable_table.lookup(var.var_name)
        if var_entry == None:
            line, col = self.dsd._tx_parser.pos_to_linecol(var._tx_position)
            message = "Undefined variable {0}.".format(var.var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC))
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
                "construct_type": DataType.VARIABLE,
                "_tx_position": data_locator._tx_position
            }

        else:
            # Checks field names against given data_providers
            found_data_provider = None
            for data_provider in self.data_providers:
                if data_provider.dsd.model_id == template_name:
                    found_data_provider = data_provider

            if found_data_provider == None:
                line, col = self.dsd._tx_parser.pos_to_linecol(data_locator._tx_position)
                message = "There is no data provider defined for template connection '{0}'.".format(template_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC))
            
            found_dp_field = found_data_provider.field_lookup(field_name)

            if not found_dp_field:
                line, col = self.dsd._tx_parser.pos_to_linecol(data_locator._tx_position)
                message = "Template field '{0}' is not defined in data provider's template '{1}'".format(field_name, template_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC))

            # Generate new variable and add new entry to the data locator table
            gen_var_name = self.variable_table.add_helper_var({
                "content": "",
                "content_type": found_dp_field.type,
                "construct_type": DataType.NOTHING,
            })
            self.data_locator_vars.append(gen_var_name)
            self.data_locator_table.add(template_name, field_name, gen_var_name, found_dp_field)
            
            return {
                "content": gen_var_name,
                "content_type": found_dp_field.type,
                "construct_type": DataType.VARIABLE
            }



# ----------------------------------------------------------------
# RIGHT HAND SIDE SECTION
# ----------------------------------------------------------------

### TODO: TEST THIS SECTION!


    def rhs_statement(self, rhs):
        pass



    def find_data_provider(self, model_name, method_object):
        data_provider = None
        for ds in self.data_providers:
            if ds.model_id == model_name:
                data_provider = ds

        if not data_provider:
            line, col = self.dsd._tx_parser.pos_to_linecol(method_object._tx_position)
            message = "Model with name '{0}' does not exist.".format(model_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC))

        return data_provider



    def check_field_list_for_duplicates(self, json_field_list, method, method_object):
        sett == set()
        for json_field in json_field_list:
            sett.add(json_field.name)

        if (len(sett) != len(field_list)):
            line, col = self.dsd._tx_parser.pos_to_linecol(method_object._tx_position)
            message = f"Duplicate fields detected in data of {method} method."
            raise AkashicError(message, line, col, ErrType.SEMANTIC))



    def check_fact_address_def(self, json_field, dp_field):
        # Check if variable is [address variable]
        var_entry = self.variable_table.lookup(json_field.value.var_name)
        if not var_entry:
            line, col = self.dsd._tx_parser.pos_to_linecol(json_field.value._tx_position)
            message = f"Variable '{json_field.value.var_name}' is not defined."
            raise AkashicError(message, line, col, ErrType.SEMANTIC))

        if not "model_id" in var_entry.value:
            line, col = self.dsd._tx_parser.pos_to_linecol(json_field.value._tx_position)
            message = f"Variable '{json_field.value.var_name}' is not fact address."
            raise AkashicError(message, line, col, ErrType.SEMANTIC))

        # Extract information 
        fact_address_template_name = var_entry.value["model_id"]
        fact_address_field_name = json_field.value.field_name
        
        # Check semantics of fact_address_template_name and fact_address_field_name
        found_data_provider = None
        for data_provider in self.data_providers:
            if data_provider.dsd.model_id == fact_address_template_name:
                found_data_provider = data_provider
        if found_data_provider == None:
            line, col = self.dsd._tx_parser.pos_to_linecol(json_field.value._tx_position)
            message = f"There is no data provider defined for fact address template '{fact_address_template_name}'."
            raise AkashicError(message, line, col, ErrType.SEMANTIC))

        found_dp_field = found_data_provider.field_lookup(fact_address_field_name)
        if not found_dp_field:
            line, col = self.dsd._tx_parser.pos_to_linecol(json_field.value._tx_position)
            message = f"Fact address field '{fact_address_field_name}' is not defined in data provider's template '{fact_address_template_name}'"
            raise AkashicError(message, line, col, ErrType.SEMANTIC))

        # Check if type of fact accress field is same as field in json object
        if found_dp_field.type != dp_field.type:
            line, col = self.dsd._tx_parser.pos_to_linecol(json_field.value._tx_position)
            message = f"Type missmatch in field '{json_field.name}'. Expected type '{dp_field.type}'. Given type '{found_dp_field.type}'"
            raise AkashicError(message, line, col, ErrType.SEMANTIC))
  


    def check_fields_and_build_clips_func_call_arguments(
                                                        self, 
                                                        json_field_list, 
                                                        dp_field_list, 
                                                        model_name):
        arg_list = []
        for json_field in json_field_list:
            json_field_ok = False

            for dp_field in dp_field_list:
                if json_field.name == dp_field.field_name:
                    json_field_ok = True

                    given_type = py_to_clips_type(json_field.value)
                    if given_type == None:
                        self.check_fact_address_def(json_field, dp_field)

                        # Build clips command args
                        arg_list.append(json_field.name)
                        arg_list.append('(fact-slot-value ' + json_field.value.var_name + ' ' + json_field.value.field_name + ')')
                    else:
                        if given_type != dp_field.type:
                            line, col = self.dsd._tx_parser.pos_to_linecol(json_field.value._tx_position)
                            message = f"Field with name '{json_field.name}' contains data with wrong type. Expected type is {dp_field.type}. Given type is {given_type}."
                            raise AkashicError(message, line, col, ErrType.SEMANTIC))
                        
                        # Add field name
                        arg_list.append(json_field.name)

                        # Add field value
                        #TODO: Thisss and reverse in 'bridge' function
                        arg_list.append(str())

                        #TODO: Use BIND to save count result, to be used on RHS??? Maybe
                        #TODO: Add variable-value binding
                        #TODO: Add onetime option for rule execution
                    break 
                
            if not json_field_ok:
                line, col = self.dsd._tx_parser.pos_to_linecol(json_field.value._tx_position)
                message = f"Field with name '{json_field.name}' does not belong to the model'{model_name}'."
                raise AkashicError(message, line, col, ErrType.SEMANTIC))



    def create_statement(self, create_s):
        # Find data provider for given model
        data_provider = self.find_data_provider(create_s.model_name, oepration)

        # Check field list for duplicate fileds
        self.check_field_list_for_duplicates(create_s.json_object.field_list, "CREATE", create_s)

        # Check fields (names and types) and build CLIPS function call
        arg_list = self.check_fields_and_build_clips_func_call_arguments(
            create_s.json_object.field_list,
            data_provider.dsd.fields,
            create_s.model_name
        )

        # TODO: Use CLIPS value converter on create_s.reflect (bool) and add it ad 3. arg
        #       in clips command bellow

        # Bridge is used to store python functions called by clips
        clips_command = "(create_func " + create_s.model_name + " " + " ".join(arg_list) + ")"

        self.clips_command_list.append(clips_command)



    def read_one_statement(self, ros):
        pass

    def read_multiple_statement(self, rms):
        pass
    
    def update_statement(self, us):
        pass

    def delete_statement(self, ds):
        pass
