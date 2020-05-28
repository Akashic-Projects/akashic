from os.path import join, dirname

from textx import metamodel_from_file
from textx.export import metamodel_export, model_export
from textx.model import get_model

from akashic.arules.variable_table import VariableTable, VarType
from akashic.arules.data_locator_table import DataLocatorTable
from akashic.arules.clips_statement_builder import ClipsStatementBuilder

from akashic.exceptions import AkashicError, ErrType

from akashic.util.type_converter import clips_to_py_type, py_to_clips_type, \
                                        translate_if_c_bool
from akashic.util.type_resolver import resolve_expr_type
from akashic.util.string_util import remove_quotes, to_clips_quotes

from akashic.enums.construct_type import ConstructType
from akashic.enums.data_type import DataType


class Transpiler(object):
    """ Transpiler class

    We use this class to transpile Akashic rule into the CLIPS rule.
    """

    def __init__(self, env_provider):
        """ Transpiler constructor method
        
        Details
        -------
        1. Imports created data_providers.
        2. Creates new Variable table (used for managing symbolic
           and real variables).
        3. Creates new DataLocatorTable (used for namaging fact
           data referencing inside of rule).
        4. Setups model processor functions - transpiler loop.
        5. Loads Akashic meta-model.
        6. Loads CLIPS Pattern Builder module.
        """

        self.data_bridge = env_provider.data_bridge
        self.time_bridge = env_provider.time_bridge

        self.data_providers = self.data_bridge.data_providers

        self.variable_table = VariableTable()
        self.data_locator_table = DataLocatorTable()
        self.lhs_clips_command_list = []
        self.rhs_clips_command_list = []

        # Keep track of used variables in this array
        self.data_locator_vars = []

        processors = {
            'Rule': self.rule,

            #### LHS processors
            'LHSStatement':     self.lhs_statement,
            'SYMBOLIC_VAR':     self.symbolic_var,
            'FACT_ADDRESS_VAR': self.fact_address_var,
            'BINDING_VAR':      self.binding_var,

            'SpecialBinaryLogicExpression': \
                self.special_binary_logic_expression,
            'SpecialSingularLogicExpression': \
                self.special_singular_logic_expression,
            'TestSingularLogicExpression': \
                self.test_singular_logic_expression,

            'NegationFunction':   self.negation_function,
            'CountFunction':      self.count_function,
            'StrFunction':        self.str_function,
            'StrToTimeFunction':  self.str_to_time_function,
            'TimeToStrFunction':  self.time_to_str_function,
            
            'LogicExpression':  self.logic_expression,
            'CompExpression':   self.comp_expression,
            'PlusMinusExpr':    self.plus_minus_expr,
            'MulDivExpr':       self.mul_div_expr,
            'SqrExpr':          self.sqr_expr,
            'Factor':           self.factor,
            'DataLocator':      self.data_locator,
            'VARIABLE':         self.variable,

            #### RHS processors
            'RHSStatement':     self.rhs_statement,
            'CreateStatement':  self.create_statement,
            'ReturnStatement':  self.return_statement,
            'UpdateStatement':  self.update_statement,
            'DeleteStatement':  self.delete_statement,
        }

        this_folder = dirname(__file__)
        self.meta_model = metamodel_from_file(
                            join(this_folder, 'meta_model.tx'), debug=False)
        self.meta_model.register_obj_processors(processors)

        # Get builder classes
        self.clips_statement_builder = ClipsStatementBuilder()

        self.rule = None
        self.tranpiled_rule = None



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
        return 0



# ----------------------------------------------------------------
#  HELPER FUNCTIONS SECTION
# ----------------------------------------------------------------

    def clear_after_binding_var(self):
        fields_to_remove = []
        for var_name in self.data_locator_vars:
            for template_name, template in self.data_locator_table \
                                           .table.items():
                for field_name, field in template.fields.items():
                    if field.var_name == var_name:
                        fields_to_remove.append((template_name, field_name))
                    
        for f in fields_to_remove:
            self.data_locator_table.table[f[0]].fields.pop(f[1])

            if len(self.data_locator_table.table[f[0]].fields.items()) < 1:
                self.data_locator_table.table.pop(f[0])
        return 0



    def rotate_used_data_locator_vars(self):
        """ Function rotates used data locator variables

        Details
        -------
        1. We go through variables used to reference CLIPS facts 
            (data locators (DL) - in Akashic terminology)
        2. We through data locator table to get every entry using
            current DL variable
        3. We generate new variable in varialbe table
            (with new name - 'name rotation')
        4. We reassign this new variable to mentioned entry
        
        5. We go through all defined variables* and replace old
            helper varialbe names with new ones.
        6. We go through list of variables refenrenced in statement
            of * and replace their names also.
        """

        new_data_locator_vars = self.data_locator_vars.copy()

        for var_name in self.data_locator_vars:
            for template_name, template in self.data_locator_table \
                                           .table.items():
                for field_name, field in template.fields.items():
                    if field.var_name != var_name:
                        continue

                    gen_var_name = self.variable_table.next_var_name()

                    for vn, var_value in self.variable_table.table.items():
                        if var_value.value["construct_type"] != \
                        ConstructType.WORKABLE:
                            field.var_name = gen_var_name
                            var_value.value["content"] = \
                                var_value.value["content"] \
                                .replace(var_name, gen_var_name)

                        var_value.used_variables = \
                            [gen_var_name if uv == var_name \
                            else uv for uv in var_value.used_variables]
                        new_data_locator_vars = \
                            [gen_var_name if dlv == var_name \
                            else dlv for dlv in new_data_locator_vars]
        
        self.data_locator_vars = new_data_locator_vars
        return 0



# ----------------------------------------------------------------
# LEFT HAND SIDE SECTION
# ----------------------------------------------------------------

    def rule(self, rule):
        clips_salience = ""
        if hasattr(rule, 'salience'):
            if (rule.salience < 0):
                line, col = get_model(rule)._tx_parser \
                            .pos_to_linecol(rule._tx_position)
                message = "Rule salience cannot be negative."
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
            else:
                clips_salience = "\n\t(declare (salience " + \
                                 str(rule.salience) + "))\n"

        rule = "(defrule " + rule.rule_name + clips_salience
        
        lhs_commands = ["\t" + comm for comm in self.lhs_clips_command_list]
        rhs_commands = ["\t" + comm for comm in self.rhs_clips_command_list]

        rule += "\n" + \
                "\n".join(lhs_commands) + \
                "\n\t=>\n" + \
                "\n".join(rhs_commands) + "\n)"

        self.tranpiled_rule = rule
        return 0



    def lhs_statement(self, lhss):
        """ Informs about creation of new statement

        Parameters
        ----------
        lhss : object
            LHS object constructed by the textX by parsing
            Akashic rule based on predefined meta-model

        """

        if lhss.stat.__class__.__name__ == "ASSERTION":
            print("Assertion of expression - done.")

        elif lhss.stat.__class__.__name__ == "SYMBOLIC_VAR":
            print("Init of new symbolic variable - done.")
        
        elif lhss.stat.__class__.__name__ == "FACT_ADDRESS_VAR":
            print("Init of new fact address variable - done.")

        elif lhss.stat.__class__.__name__ == "BINDING_VAR":
            print("Init of new binding variable - done.")
        return 0



    def clips_code(self, cc):
        clips_command = remove_quotes(cc.clips_code)
        self.lhs_clips_command_list.append(to_clips_quotes(clips_command))
        return 0



    def symbolic_var(self, sv):
        if self.variable_table.lookup(sv.var_name):
            line, col = get_model(sv)._tx_parser \
                        .pos_to_linecol(sv._tx_position)
            message = "Variable '{0}' is already defined." \
                      .format(sv.var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)
        
        self.variable_table.add_named_var(
            sv.var_name, 
            sv.expr, 
            self.data_locator_vars,
            VarType.SYMBOLIC
        )
        self.data_locator_vars = []
        return 0



    def fact_address_var(self, fav):
        if self.variable_table.lookup(fav.var_name):
            line, col = get_model(fav)._tx_parser \
                        .pos_to_linecol(fav._tx_position)
            message = "Variable '{0}' is already defined." \
                      .format(sv.var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        self.variable_table.add_named_var(
            fav.var_name,
            fav.expr,
            [],
            VarType.FACT_ADDRESS
        )
        clips_command = fav.var_name + \
                        " <- " + \
                        fav.expr["content"]
        self.lhs_clips_command_list.append(clips_command)
        return 0



    def binding_var(self, bv):
        if self.variable_table.lookup(bv.var_name):
            line, col = get_model(bv)._tx_parser \
                        .pos_to_linecol(bv._tx_position)
            message = "Variable '{0}' is already defined." \
                      .format(sv.var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        self.variable_table.add_named_var(
            bv.var_name,
            bv.expr,
            [],
            VarType.BINDING
        )

        # Build clips commands
        if bv.expr["construct_type"] in [ ConstructType.NORMAL_EXP, \
                                          ConstructType.VARIABLE, \
                                          ConstructType.FUNCTION_CALL ]:
            clips_commands = self.clips_statement_builder \
                            .build_regular_dl_patterns(self.data_locator_table)
            self.lhs_clips_command_list.extend(clips_commands)
            self.clear_after_binding_var()

        return 0



    def special_binary_logic_expression(self, binary):
        if len(binary.operands) < 2:
            self.lhs_clips_command_list.append(binary.operands[0]["content"])
            return 0

        args = []
        for i in range(0, len(binary.operands)):
            if binary.operands[i]["construct_type"] == \
            ConstructType.SPECIAL_CON_EXP:
                args.append(binary.operands[i]["content"])
            else:
                line, col = binary.operands[i]["_tx_position"]
                message = "Special Binary Operation argument must be a " \
                          "Special Conditional Expression, but '{0}' found." \
                          .format(binary.operands[i]["construct_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
                
        clips_command = args[0]
        for i in range(1, len(binary.operands)):
            clips_command = "(" + \
                            binary.operator[i-1] + " " + \
                            clips_command + " " + \
                            args[i] + \
                            ")"

        self.lhs_clips_command_list.append(clips_command)
        return 0



    def special_singular_logic_expression(self, singular):
        bline, bcol = get_model(singular)._tx_parser \
                      .pos_to_linecol(singular._tx_position)

        if hasattr(singular, "template") and singular.template != '':
            self.find_data_provider(singular.template, singular)
            clips_command = '(' + singular.template + ')'
            if singular.operator:
                clips_content = clips_command
            else:
                clips_content = "(" + \
                                singular.operator + " " + \
                                clips_command + \
                                ")"
            
            return {
                "content": clips_content, 
                "content_type": None,
                "construct_type": ConstructType.SPECIAL_CON_EXP,
                "_tx_position": (bline, bcol),
                "model_id": singular.template
            }

        if singular.operand["construct_type"] != ConstructType.NORMAL_EXP:
            line, col = singular.operand["_tx_position"]
            message = "Special Singular Operation argument must be a " \
                      "Normal Expression, but '{0}' found." \
                      .format(singular.operand["construct_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        clips_command = self.clips_statement_builder.build_special_pattern(
            self.data_locator_table, 
            self.data_locator_vars, 
            singular.operand["content"],
            singular
        )

        # Extract used template name
        template = self.clips_statement_builder.get_template(
            self.data_locator_table, 
            self.data_locator_vars
        )

        # Rotate defined variables for next special expression
        self.rotate_used_data_locator_vars()
        self.data_locator_vars = []

        # Return CLIPS command
        if not singular.operator:
            clips_content = clips_command
        else:
            clips_content = "(" + singular.operator + " " + clips_command + ")"

        return {
            "content": clips_content, 
            "content_type": None,
            "construct_type": ConstructType.SPECIAL_CON_EXP,
            "_tx_position": (bline, bcol),
            "model_id": template.name
        }



    def test_singular_logic_expression(self, test):
        if test.operand["construct_type"] != ConstructType.NORMAL_EXP:
            line, col = test.operand["_tx_position"]
            message = "Test Operation argument must be a " \
                      "Normal Expression, but '{0}' found." \
                      .format(test.operand["construct_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Build clips commands
        clips_commands = self.clips_statement_builder \
                         .build_regular_dl_patterns(self.data_locator_table)

        self.lhs_clips_command_list.extend(clips_commands)
        self.lhs_clips_command_list.append("(test " + \
                                           test.operand["content"] + \
                                           ")")
        return 0



    def negation_function(self, neg):
        result = neg.operand
        bline, bcol = get_model(neg)._tx_parser \
                      .pos_to_linecol(neg._tx_position)

        if result["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
            line, col = result["_tx_position"]
            message = "Negation operand type INTEGER, FLOAT or BOOLEAN " \
                      "is expected, but '{0}' found." \
                      .format(result["content_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        operator = neg.operator
        if result["content_type"] == ConstructType.WORKABLE:
            clips_content = not result["content"]
            return {
                "content": clips_content, 
                "content_type": py_to_clips_type(clips_content.__class__),
                "construct_type": ConstructType.WORKABLE,
                "_tx_position": (bline, bcol)
            }
        else:
            clips_content = '(' + operator + ' ' + \
                            str(translate_if_c_bool(result["content"])) + \
                            ')'

            resolved_c_type = "BOOLEAN"
            return {
                "content": clips_content, 
                "content_type": resolved_c_type,
                "construct_type": ConstructType.NORMAL_EXP,
                "_tx_position": (bline, bcol)
            }



    def count_function(self, countt):
        bline, bcol = get_model(countt)._tx_parser.pos_to_linecol(countt._tx_position)

        if countt.operand["construct_type"] != ConstructType.NORMAL_EXP:
            line, col = countt.operand["_tx_position"]
            message =  "{0} operation argument must be expression. {1} given.".format(
                countt.operator, countt.operand["construct_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Build count command if present
        clips_command = self.clips_statement_builder.build_count_pattern(
            self.data_locator_table, 
            self.data_locator_vars, 
            countt.operand["content"]
        )

        # Rotate defined variables for next special expression
        # self.rotate_used_data_locator_vars()
        # self.data_locator_vars = []

        # Return CLIPS command
        clips_content = clips_command
        resolved_c_type = "INTEGER"
        return {
            "content": clips_content,
            "content_type": resolved_c_type,
            "construct_type": ConstructType.COUNT_FUNC_CALL,
            "_tx_position": (bline, bcol)
        }



    def str_function(self, strr):
        result = strr.operand
        bline, bcol = get_model(strr)._tx_parser \
                      .pos_to_linecol(strr._tx_position)

        resolved_c_type = "STRING"
        if result["content_type"] == ConstructType.WORKABLE:
            clips_content = str(result["content"])
            return {
                "content": clips_content,
                "content_type": resolved_c_type,
                "construct_type": ConstructType.WORKABLE,
                "_tx_position": (bline, bcol)
            }
        else:
            clips_content = '(str-cat ' + \
                            str(translate_if_c_bool(result["content"])) + ')'
            return {
                "content": clips_content, 
                "content_type": resolved_c_type,
                "construct_type": ConstructType.FUNCTION_CALL,
                "_tx_position": (bline, bcol)
            }



    def str_to_time_function(self, sttf):
        time = sttf.operands[0]
        time_format = sttf.operands[1]

        bline, bcol = get_model(sttf)._tx_parser \
                      .pos_to_linecol(sttf._tx_position)

        def raise_error_if_not_type(obj, expected_types):
            if obj["content_type"] != "STRING":
                line, col = obj["_tx_position"]
                message = "Expected type {0}, but {1} found." \
                          .format(expected_types, 
                                  time["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
        
        raise_error_if_not_type(time, "STRING")
        raise_error_if_not_type(time_format, "STRING")

        time_str = None
        if time["construct_type"] == ConstructType.WORKABLE:
            time_str = '"' + time["content"] + '"'
        else:
            time_str = time["content"]

        time_format_str = None
        if time_format["construct_type"] == ConstructType.WORKABLE:
            time_format_str = '"' + time_format["content"] + '"'
        else:
            time_format_str = time_format["content"]
        
        construct_type = None
        if time["construct_type"] != ConstructType.WORKABLE or \
        time_format["construct_type"] != ConstructType.WORKABLE:
            construct_type = ConstructType.NORMAL_EXP
        else:
            construct_type = ConstructType.WORKABLE

        resolved_c_type = "INTEGER"
        clips_content = "(str_to_time " + \
                        time_str + " " + \
                        time_format_str + \
                        ")"
        return {
            "content": clips_content,
            "content_type": resolved_c_type,
            "construct_type": construct_type,
            "_tx_position": (bline, bcol)
        }



    def time_to_str_function(self, ttsf):
        pass



    def logic_expression(self, logic):
        result = logic.operands[0]
        bline, bcol = get_model(logic)._tx_parser.pos_to_linecol(logic._tx_position)

        l = len(logic.operands)
        i = 1
        while i < l:
            current = logic.operands[i]
            
            if result["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
                line, col = result["_tx_position"]
                message = "Logic operand of type INTEGER, FLOAT or BOOLEAN expected, {0} found.".format(
                    result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if current["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
                line, col = current["_tx_position"]
                message = "Logic operand of type INTEGER, FLOAT or BOOLEAN expected, {0} found.".format(
                    current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            operator = logic.operator[i-1]

            if (result["construct_type"]  == ConstructType.WORKABLE 
            and current["construct_type"] == ConstructType.WORKABLE):
                if operator == 'and':
                    val = result["content"] and current["content"]
                if operator == 'or':
                    val = result["content"] or current["content"]

                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": ConstructType.WORKABLE,
                    "_tx_position": (bline, bcol)
                }

            else:
                val = '(' + operator + ' ' + \
                        str(translate_if_c_bool(result["content"])) + ' ' + \
                        str(translate_if_c_bool(current["content"])) + ')'

                resolved_c_type = resolve_expr_type("logic", result["content_type"], current["content_type"])

                result = {
                    "content": val,
                    "content_type": resolved_c_type,
                    "construct_type": ConstructType.NORMAL_EXP,
                    "_tx_position": (bline, bcol)
                }

            i += 1

        return result



    def comp_expression(self, comp):
        result = comp.operands[0]
        bline, bcol = get_model(comp)._tx_parser.pos_to_linecol(comp._tx_position)

        l = len(comp.operands)
        i = 1
        while i < l:
            current = comp.operands[i]
            
            if result["content_type"] not in ["INTEGER", "FLOAT", "STRING"]:
                line, col = result["_tx_position"]
                message = "Comparison operand of type INTEGER, FLOAT or STRING expected, {0} found.".format(
                    result["content_type"])
                print("----" + str(result["content"]))
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if current["content_type"] not in ["INTEGER", "FLOAT", "STRING"]:
                line, col = current["_tx_position"]
                message = "Comparison operand of type INTEGER, FLOAT or STRING expected, {0} found.".format(
                    current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            # Resolve eq operaator
            if comp.operator[i-1] == '==':
                operator = '='
            else:
                operator = comp.operator[i-1]

            if ((result["construct_type"]  == ConstructType.WORKABLE 
            and current["construct_type"] == ConstructType.WORKABLE)
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
                    "construct_type": ConstructType.WORKABLE,
                    "_tx_position": (bline, bcol)
                }

            else:
                op1 = ""
                op2 = ""
                if result["content_type"] == "STRING" and result["construct_type"]  == ConstructType.WORKABLE:
                    op1 = "\"" + result["content"] + "\""
                else:
                    op1 = result["content"]

                if current["content_type"] == "STRING" and current["construct_type"]  == ConstructType.WORKABLE:
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
                    line, col = result["_tx_position"]
                    message = "Incompatible operand types present in comparison expression."
                    raise AkashicError(message, line, col, ErrType.SEMANTIC)

                result = {
                    "content": val,
                    "content_type": resolved_c_type,
                    "construct_type": ConstructType.NORMAL_EXP,
                    "_tx_position": (bline, bcol)
                }

            i += 1

        return result



    def plus_minus_expr(self, plus_minus):
        bline, bcol = get_model(plus_minus)._tx_parser \
                        .pos_to_linecol(plus_minus._tx_position)

        # Check if expression is numeric
        result = plus_minus.operands[0]
        
        l = len(plus_minus.operands)
        i = 1
        while i < l:
            current = plus_minus.operands[i]

            if result["content_type"] not in ["INTEGER", "FLOAT", "STRING"]:
                line, col = result["_tx_position"]
                message = "Addition or subtraction operand of type INTEGER "\
                          "or FLOAT expected, {0} found."\
                            .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
               
            if current["content_type"] not in ["INTEGER", "FLOAT","STRING"]:
                line, col = current["_tx_position"]
                message = "Addition or subtraction operand of type INTEGER "\
                          "or FLOAT expected, {0} found."\
                            .format(current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            operator = plus_minus.operator[i-1]

            if (result["construct_type"]  == ConstructType.WORKABLE 
            and current["construct_type"] == ConstructType.WORKABLE):
                if operator == '+':
                    val = result["content"] + current["content"]
                elif operator == '-':
                    if ("STRING" in [result["content_type"],
                    current["content_type"]]):
                        line, col = result["_tx_position"]
                        message = "Cannot perform operation 'minus' "\
                                  "on strings."
                        raise AkashicError(message, line, col, 
                                           ErrType.SEMANTIC)

                    val = result["content"] - current["content"]
                    
                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": ConstructType.WORKABLE,
                    "_tx_position": (bline, bcol)
                }

            else:

                if ("STRING" in [result["content_type"],
                current["content_type"]]):
                    
                    if result["construct_type"] == ConstructType.WORKABLE:
                        if result["content_type"] != "STRING": 
                            result_content = str(result["content"]) 
                        else: 
                            result_content = '"' + str(result["content"]) + '"'
                    else:
                        result_content = str(result["content"]) 

                    if current["construct_type"] == ConstructType.WORKABLE:
                        if current["content_type"] != "STRING": 
                            current_content = str(current["content"]) 
                        else: 
                            current_content = '"' + str(current["content"]) + '"'
                    else:
                        current_content = str(current["content"]) 

                    val = '(str-cat ' + ' ' + \
                          result_content + ' ' + \
                          current_content + ')'
                    resolved_c_type = resolve_expr_type(
                                        "plus_minus", 
                                        result["content_type"], 
                                        current["content_type"])

                else:
                    val = '(' + operator + ' ' + \
                        str(result["content"]) + ' ' + \
                        str(current["content"]) + ')'
                    resolved_c_type = resolve_expr_type(
                                        "plus_minus", 
                                        result["content_type"], 
                                        current["content_type"])

                result = {
                    "content": val,
                    "content_type": resolved_c_type,
                    "construct_type": ConstructType.NORMAL_EXP,
                    "_tx_position": (bline, bcol)
                }

            i += 1
        return result



    def mul_div_expr(self, mul_div):
        result = mul_div.operands[0]
        bline, bcol = get_model(mul_div)._tx_parser.pos_to_linecol(mul_div._tx_position)

        l = len(mul_div.operands)
        i = 1
        while i < l:
            current = mul_div.operands[i]

            if result["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = result["_tx_position"]
                message = "Multiplication or division operand of type INTEGER or FLOAT expected, {0} found.".format(
                    result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = current["_tx_position"]
                message = "Multiplication or division operand of type INTEGER or FLOAT expected, {0} found.".format(
                    current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            operator = mul_div.operator[i-1]

            if (result["construct_type"]  == ConstructType.WORKABLE 
            and current["construct_type"] == ConstructType.WORKABLE):
                if operator == '*':
                    val = result["content"] * current["content"]
                elif operator == '/':
                    val = result["content"] / current["content"]
                
                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": ConstructType.WORKABLE,
                    "_tx_position": (bline, bcol)
                }

            else:
                val = '(' + operator + ' ' + str(result["content"]) + ' ' + str(current["content"]) + ')'
                resolved_c_type = resolve_expr_type("mul_div", result["content_type"], current["content_type"])

                result = {
                    "content": val,
                    "content_type": resolved_c_type,
                    "construct_type": ConstructType.NORMAL_EXP,
                    "_tx_position": (bline, bcol)
                }

            i += 1

        return result



    def sqr_expr(self, sqr):
        result = sqr.operands[0]
        bline, bcol = get_model(sqr)._tx_parser.pos_to_linecol(sqr._tx_position)

        l = len(sqr.operands)
        i = 1
        while i < l:
            current = sqr.operands[i]
           
            if result["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = result["_tx_position"]
                message = "Exponentiation or root extraction operand of type INTEGER or FLOAT expected, {0} found.".format(
                    result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = current["_tx_position"]
                message = "Exponentiation or root extraction operand of type INTEGER or FLOAT expected, {0} found.".format(
                    current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            operator = '**'

            if (result["construct_type"]  == ConstructType.WORKABLE 
            and current["construct_type"] == ConstructType.WORKABLE):
                val = result["content"] ** current["content"]

                result = {
                    "content": val, 
                    "content_type": py_to_clips_type(val.__class__),
                    "construct_type": ConstructType.WORKABLE,
                    "_tx_position": (bline, bcol)
                }

            else:
                val = '(' + operator + ' ' + str(result["content"]) + ' ' + str(current["content"]) + ')'
                resolved_c_type = resolve_expr_type("sqr", result["content_type"], current["content_type"])

                result = {
                    "content": val, 
                    "content_type": resolved_c_type,
                    "construct_type": ConstructType.NORMAL_EXP,
                    "_tx_position": (bline, bcol)
                }

            i += 1

        return result



    def factor(self, factor):
        line, col = get_model(factor)._tx_parser.pos_to_linecol(factor._tx_position)
        if factor.value.__class__.__name__ in ["int", "float", "bool"]:
            # If factor class is simple python type
            return {
                "content": factor.value, 
                "content_type": py_to_clips_type(factor.value.__class__),
                "construct_type": ConstructType.WORKABLE,
                "_tx_position": (line, col)
            }
        elif factor.value.__class__.__name__ == "STRING_C":
            # Remove single quotation marks if factor class is string
            return {
                "content": remove_quotes(factor.value.val),
                "content_type": py_to_clips_type(str),
                "construct_type": ConstructType.WORKABLE,
                "_tx_position": (line, col)
            }

        else:
            # Enters when factor class is: VARIABLE or DataLocator VALUE ENTRY
            return factor.value



    def variable(self, var):
        var_entry = self.variable_table.lookup(var.var_name)
        if var_entry == None:
            line, col = get_model(var)._tx_parser.pos_to_linecol(var._tx_position)
            message = "Undefined variable {0}.".format(var.var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)
        else:
            # Add used variables from current variable to the list of globally used variables
            self.data_locator_vars = list(set(self.data_locator_vars) | set(var_entry.used_variables))
            return var_entry.value



    def data_locator(self, data_locator):
        # Get needed data
        template_name = data_locator.template_conn_expr.templates[0]
        field_name = data_locator.field

        # Get position of token
        line, col = get_model(data_locator)._tx_parser.pos_to_linecol(data_locator._tx_position)

        # Search for existing entry in data locator table
        field = self.data_locator_table.lookup(template_name, field_name)
        if field and field.var_name:
            return {
                "content": field.var_name, 
                "content_type": field.dp_field.type,
                "construct_type": ConstructType.VARIABLE,
                "_tx_position": (line, col)
            }

        else:
            # Checks field names against given data_providers
            found_data_provider = None
            for data_provider in self.data_providers:
                if data_provider.dsd.model_id == template_name:
                    found_data_provider = data_provider

            if found_data_provider == None:
                message = "There is no data provider defined for template connection '{0}'.".format(template_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
            
            found_dp_field = found_data_provider.field_lookup(field_name)

            if not found_dp_field:
                message = "Template field '{0}' is not defined in data provider's template '{1}'".format(field_name, template_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            # Generate new variable and add new entry to the data locator table
            gen_var_name = self.variable_table.add_helper_var({
                "content": "",
                "content_type": found_dp_field.type,
                "construct_type": ConstructType.NOTHING,
            })
            self.data_locator_vars.append(gen_var_name)
            self.data_locator_table.add(template_name, field_name, gen_var_name, found_dp_field)
            
            return {
                "content": gen_var_name,
                "content_type": found_dp_field.type,
                "construct_type": ConstructType.VARIABLE,
                "_tx_position": (line, col)
            }



# ----------------------------------------------------------------
# RIGHT HAND SIDE SECTION
# ----------------------------------------------------------------

### TODO: TEST THIS SECTION!

    def find_data_provider(self, model_name, web_op_object):
        data_provider = None
        for ds in self.data_providers:
            if ds.dsd.model_id == model_name:
                data_provider = ds

        if not data_provider:
            line, col = get_model(web_op_object)._tx_parser.pos_to_linecol(web_op_object._tx_position)
            message = "DSD model with name '{0}' does not exist.".format(model_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        return data_provider



    def check_field_list_for_duplicates(self, json_field_list, web_op_object):
        for i in range(0, len(json_field_list)):
            for j in range(i+1, len(json_field_list)):
                if json_field_list[i].name == json_field_list[j].name:
                    line, col = get_model(web_op_object)._tx_parser.pos_to_linecol(web_op_object._tx_position)
                    message = f"Duplicate fields '{json_field_list[i].name}' detected."
                    raise AkashicError(message, line, col, ErrType.SEMANTIC)



    def check_fact_address_def(self, json_field, dp_field=None):
        # Check if variable is [address variable]
        var_entry = self.variable_table.lookup(json_field.value.var_name)
        # Get token json_field value token location
        line, col = get_model(json_field.value)._tx_parser.pos_to_linecol(json_field.value._tx_position)

        if not var_entry:
            message = f"Variable '{json_field.value.var_name}' is not defined."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)
        
        if var_entry.var_type != VarType.FACT_ADDRESS:
            message = f"Variable '{json_field.value.var_name}' is not fact address."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        if not "model_id" in var_entry.value:
            message = f"Variable '{json_field.value.var_name}' does not point to any fact."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Extract information 
        fact_address_template_name = var_entry.value["model_id"]
        fact_address_field_name = json_field.value.field_name
        
        # Check semantics of fact_address_template_name and fact_address_field_name
        found_data_provider = None
        for data_provider in self.data_providers:
            if data_provider.dsd.model_id == fact_address_template_name:
                found_data_provider = data_provider
        if found_data_provider == None:
            message = f"There is no data provider defined for fact address template '{fact_address_template_name}'."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        found_dp_field = found_data_provider.field_lookup(fact_address_field_name)
        if not found_dp_field:
            message = f"Fact address field '{fact_address_field_name}' is not defined in data provider's template '{fact_address_template_name}'"
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Check if type of fact accress field is same as field in json object
        if dp_field != None and found_dp_field.type != dp_field.type:
            message = f"Type missmatch in field '{json_field.name}'. Expected type '{dp_field.type}'. Given type '{found_dp_field.type}'"
            raise AkashicError(message, line, col, ErrType.SEMANTIC)
  

    def check_binding_variable(self, var, dp_field=None):
        var_entry = self.variable_table.lookup(var.var_name)
        line, col = get_model(var)._tx_parser.pos_to_linecol(var._tx_position)

        if var_entry == None:
            message = "Undefined variable {0}.".format(var.var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        if var_entry.var_type != VarType.BINDING:
            message = "Cannot reference non-binding variable in RHS of the rule."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        entry_type = var_entry.value["content_type"]
        if dp_field != None and entry_type != dp_field.type:
            message = f"Type missmatch in field '{dp_field.field_name}'. "\
                      f"Expected type '{dp_field.type}'. Given type is "\
                      f"'{entry_type}'."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)


    def separate_data_from_other_fields(self, json_object, dp_field_list):
        # Collect all non-data fields
        other_json_fields = []
        for json_field in json_object.field_list:
            json_field_ok = False
            for dp_field in dp_field_list:
                if json_field.name == dp_field.field_name:
                    json_field_ok = True
                    break
            if not json_field_ok:
                other_json_fields.append(json_field)

        # Create json_field_list without 'other-json-fields'
        data_json_fields = []
        for json_field in json_object.field_list:
            if not json_field in other_json_fields:
                data_json_fields.append(json_field)

        return (data_json_fields, other_json_fields)



    def check_model_refs_and_build_clips_func_call_args(self, 
                                                        other_json_fields,
                                                        dp_ref_foreign_models,
                                                        json_object, 
                                                        model_name):
        # Check refs and collect actual refs from non-data fields
        json_refs = []
        for ref in dp_ref_foreign_models:
            ref_ok = False

            for o_json_field in other_json_fields:
                if ref.field_name == o_json_field.name:
                    ref_ok = True
                    json_refs.append(o_json_field)
                    break
            
            if not ref_ok:
                line, col = get_model(json_object)._tx_parser \
                            .pos_to_linecol(json_object._tx_position)
                message = f"Foreign model reference field "\
                          f"'{ref.field_name}' is omitted from the "\
                          f"operation request for model '{model_name}'."
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

        arg_list = []
        for ref in json_refs:
            arg_list.append('"' + json_field.name + '"')
            arg_list.append('"' + str(json_field.value) + '"')

        return arg_list



    def check_data_fields(self,data_json_fields, dp_field_list,
                          can_reflect, model_name, web_op_name):

        # Check types and create args
        for dp_field in dp_field_list:
            json_field_ok = False

            for json_field in data_json_fields:
                if json_field.name == dp_field.field_name:
                    json_field_ok = True

                    given_type = py_to_clips_type(
                                    json_field.value.__class__)

                    if (given_type != None) and (given_type != dp_field.type):
                        line, col = get_model(json_field)._tx_parser \
                                .pos_to_linecol(json_field._tx_position)

                        message = f"Field '{json_field.name}' "\
                                    f"contains data with wrong type. "\
                                    f"Expected type is {dp_field.type}. "\
                                    f"Given type is {given_type}."
                        raise AkashicError(message, line, col, 
                                            ErrType.SEMANTIC)
                    break 

            if (((dp_field.use_for_create and web_op_name == "CREATE") or \
            (dp_field.use_for_update and web_op_name == "UPDATE")) and \
            (not json_field_ok) and can_reflect) or \
            ((not json_field_ok) and not can_reflect):

                line, col = get_model(json_field)._tx_parser \
                .pos_to_linecol(json_field._tx_position)
                message = f"Field '{dp_field.field_name}' "\
                          f"is omitted from the operation request "\
                          f"on model '{model_name}'."
                raise AkashicError(message, line, col, ErrType.SEMANTIC)


    def get_dp_field(self, field_name, data_provider):
        if data_provider == None:
            return None

        for dp_field in data_provider.dsd.fields:
            if dp_field.field_name == field_name:
                return dp_field
        return None


    def build_clips_func_call_args(self, data_json_fields, data_provider=None):
        arg_list = []
        for json_field in data_json_fields:
            
            given_type = py_to_clips_type(json_field.value.__class__)
            if given_type == None:
                # If json_field_value is FACT_ADDRESS_VAR
                if json_field.value.__class__.__name__ == "ValueLocator":
                    dp_field = self.get_dp_field(json_field.name,
                                                 data_provider)
                    self.check_fact_address_def(json_field, dp_field)

                    # Build clips command args
                    arg_list.append('"' + json_field.name + '"')
                    arg_list.append('(str-cat (fact-slot-value ' + 
                                    json_field.value.var_name + ' ' + 
                                    json_field.value.field_name + '))')
                                    
                elif json_field.value.__class__.__name__ == "RHS_VARIABLE":
                    dp_field = self.get_dp_field(json_field.name,
                                                 data_provider)
                    self.check_binding_variable(json_field.value, dp_field)

                    var_entry = self.variable_table.lookup(json_field.value.var_name)
                    value = var_entry.value

                    # Build clips command args
                    arg_list.append('"' + json_field.name + '"')
                    arg_list.append('(str-cat ' + value["content"] + ')')
            else:
                # Add field name
                arg_list.append('"' + json_field.name + '"')
                # Add field value
                arg_list.append('"' + str(json_field.value) + '"')

        return arg_list



    def rhs_statement(self, rhs):
        if rhs.stat.__class__.__name__ == "CLIPS_CODE":
            clips_command = remove_quotes(rhs.stat.clips_code)
            self.rhs_clips_command_list.append(to_clips_quotes(clips_command))



    def create_statement(self, create_s):
        # Find data provider for given model
        data_provider = self.find_data_provider(create_s.model_name, create_s)

        # Exit if reflection is needed, but DSD cannot reflect
        if create_s.reflect and not data_provider.dsd.can_reflect:
            line, col = get_model(create_s)._tx_parser \
            .pos_to_linecol(create_s._tx_position)
            message = f"Model '{create_s.model_name}' does not support "\
                      f"web reflection."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Exit if reflects on web, but does not have createApi
        if (create_s.reflect) and not hasattr(data_provider.dsd.apis, 'create'):
            line, col = get_model(create_s)._tx_parser \
            .pos_to_linecol(create_s._tx_position)
            message = f"Model '{create_s.model_name}' does not support "\
                      f"CREATE operation."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Check field list for duplicate fileds
        self.check_field_list_for_duplicates(create_s.json_object.field_list, 
                                             create_s)

        # Split data into data fields and other fields
        data_json_fields, other_json_fields = \
            self.separate_data_from_other_fields(create_s.json_object,
                                                 data_provider.dsd.fields)

        for a in data_json_fields:
            print("-- " + a.name)

        # Check DATA field names and types
        self.check_data_fields(
            data_json_fields,
            data_provider.dsd.fields,
            create_s.reflect,
            create_s.model_name,
            "CREATE")

        # Build DATA argument list
        data_arg_list = self.build_clips_func_call_args(data_json_fields,
                                                        data_provider)

        ref_arg_list = []
        if (data_provider.dsd.can_reflect and \
            hasattr(data_provider.dsd.apis.create, 'ref_foreign_models')):
            ref_arg_list = \
                self.check_model_refs_and_build_clips_func_call_args(
                    other_json_fields, 
                    data_provider.dsd.apis.create.ref_foreign_models,
                    create_s.json_object,
                    create_s.model_name)

        arg_array = list([
            create_s.model_name,
            "\"reflect\"",
            '"' + str(create_s.reflect) + '"',
            "\"data-len\"",
            '"' + str(len(data_arg_list)) + '"',
            *data_arg_list,
            "\"ref-len\"",
            '"' + str(len(ref_arg_list)) + '"',
            *ref_arg_list
        ])

        clips_command = "(create_func " + " ".join(arg_array) + ")"
        # self.rhs_clips_command_list.append(clips_command)

        # Direct call of function data_bridge function - for testing purpose
        self.data_bridge.create_func(arg_array)



    def return_statement(self, return_s):
        # Check field list for duplicate fileds
        self.check_field_list_for_duplicates(return_s.json_object.field_list, 
                                             return_s)

        # Build DATA argument list
        data_arg_list = self.build_clips_func_call_args(
            return_s.json_object.field_list)

        arg_array = list([
            "\"data-len\"",
            '"' + str(len(data_arg_list)) + '"',
            *data_arg_list
        ])

        clips_command = "(return_func " + " ".join(arg_array) + ")"
        self.rhs_clips_command_list.append(clips_command)

        # Direct call of function data_bridge function - for testing purpose
        # self.data_bridge.return_func(arg_array)
    
    def update_statement(self, update_s):
        pass

    def delete_statement(self, delete_s):
        pass
