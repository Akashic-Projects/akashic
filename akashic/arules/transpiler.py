import uuid
from os.path import join, dirname

from textx import metamodel_from_file, metamodel_from_str
from textx.export import metamodel_export, model_export
from textx.model import get_model
from textx.exceptions import TextXSyntaxError, TextXSemanticError

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

    def __init__(self, env_provider, is_assistance_session=False, debug=True):
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
        
        self.debug = debug

        self.env_provider = env_provider
        self.data_providers = env_provider.data_providers
        self.functions = env_provider.functions

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
            'LHS_CLIPS_CODE':   self.lhs_clips_code,
            'RHS_CLIPS_CODE':   self.rhs_clips_code,

            'SpecialBinaryLogicExpression': \
                self.special_binary_logic_expression,
            'SpecialSingularLogicExpression': \
                self.special_singular_logic_expression,
            'TestSingularLogicExpression': \
                self.test_singular_logic_expression,

            'ZeroArgFunction':      self.zero_arg_function,
            'OneArgFunction':       self.one_arg_function,
            'OnePlusArgFunction':   self.one_plus_arg_function,

            'LogicExpression':  self.logic_expression,
            'CompExpression':   self.comp_expression,
            'PlusMinusExpr':    self.plus_minus_expr,
            'MulDivExpr':       self.mul_div_expr,
            'SqrExpr':          self.sqr_expr,
            'Factor':           self.factor,
            'DataLocator':      self.data_locator,
            'LHSValueLocator':  self.lhs_value_locator,
            'VARIABLE':         self.variable,

            #### RHS processors
            'RHSStatement':     self.rhs_statement,
            'CreateStatement':  self.create_statement,
            'ReturnStatement':  self.return_statement,
            'UpdateStatement':  self.update_statement,
            'DeleteStatement':  self.delete_statement,
        }

        # this_folder = dirname(__file__)
        # self.meta_model = metamodel_from_file(
        #                     join(this_folder, 'meta_model.tx'), debug=False)
        self.meta_model = metamodel_from_str(self.env_provider.rule_mm, 
                                             debug=False)
        self.meta_model.register_obj_processors(processors)

        # Get builder classes
        self.clips_statement_builder = ClipsStatementBuilder()

        self.rule = None
        self.tranpiled_rule = None

        self.is_assistance_session = is_assistance_session
        self.is_assistance_rule = False
        self.assistance_clips_command_list = []



    def load(self, akashic_rule):
        """ Loads akashic_rule from given string

        Parameters
        ----------
        akashic_rule : str
            String containing Akashic rule

        Raises
        ------
        AkashicError
            If infinite left recursion is detected.
        """

        try:
            self.rule = self.meta_model.model_from_str(akashic_rule)
        except RecursionError as re:
            message = "Infinite left recursion is detected. " \
                      "There was unknown syntactic error."
            raise AkashicError(message, 0, 0, ErrType.SYNTACTIC)
        except TextXSyntaxError as syntaxError:
            raise AkashicError(
                syntaxError.message, 
                syntaxError.line, 
                syntaxError.col, 
                ErrType.SYNTACTIC
            )
        except TextXSemanticError as semanticError:
            raise AkashicError(
                semanticError.message, 
                semanticError.line, 
                semanticError.col, 
                ErrType.SEMANTIC
            )
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



    def check_func_num_of_args(self,func, n):
        line, col = get_model(func)._tx_parser \
                    .pos_to_linecol(func._tx_position)

        length = 0
        if isinstance(func.args, list): 
            length = len(func.args)
        else:
            length = 1

        if int(n) >= 0 and length != int(n):
            message = "Function '{0}' must have {1} arguments." \
                        .format(func.func_name, int(n))
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        if int(n) <= -1 and length < (-1) * int(n):
            message = "Function '{0}' must have at least {1} arguments." \
                        .format(func.func_name, (-1) * int(n))
            raise AkashicError(message, line, col, ErrType.SEMANTIC)



# ----------------------------------------------------------------
# LEFT HAND SIDE SECTION
# ----------------------------------------------------------------

    def rule(self, rule):
        if self.is_assistance_rule:
            self.lhs_clips_command_list = []
            self.rhs_clips_command_list = self.assistance_clips_command_list

        # Salience is SYSTEM by default (if self.is_assistance_rule == True)
        clips_salience = "\n\t(declare (salience 10000))\n"

        # Read salience
        if hasattr(rule, 'salience') and not self.is_assistance_rule:
            if isinstance(rule.salience, str) and rule.salience == "\"system\"":
                clips_salience = "\n\t(declare (salience 10000))\n"
        
            elif isinstance(rule.salience, int) :
                if rule.salience < -10000:
                    line, col = get_model(rule)._tx_parser \
                                .pos_to_linecol(rule._tx_position)
                    message = "Rule salience cannot be lower than -10 000."
                    raise AkashicError(message, line, col, ErrType.SEMANTIC)
                elif rule.salience > 9000:
                    line, col = get_model(rule)._tx_parser \
                                .pos_to_linecol(rule._tx_position)
                    message = "Rule salience cannot higher than 9 000."
                    raise AkashicError(message, line, col, ErrType.SEMANTIC)
                else:
                    clips_salience = "\n\t(declare (salience " + \
                                    str(rule.salience) + "))\n"
            else:
                line, col = get_model(rule)._tx_parser \
                            .pos_to_linecol(rule._tx_position)
                message = "Salience must be integer between " \
                          "-10 000 and 9 000 or \"system\""
                raise AkashicError(message, line, col, ErrType.SEMANTIC)


        # Read run_once data
        # Override read_once if self.is_assistance_rule == True
        if (hasattr(rule, 'run_once') and \
        rule.run_once == True) and \
        not self.is_assistance_rule:
            run_once_rhs_expression = \
                "(assert (__RuleToRemove (rule_name \"{0}\")) )" \
                .format(rule.rule_name)
            self.rhs_clips_command_list.append(run_once_rhs_expression)


        # Check if rule scheduled for deletion
        # Prevent it from getting into agenda
        run_once_lhs_expression = \
            "(not " \
                "(__RuleToRemove " \
                    "(rule_name ?rn&: (= (str-compare ?rn \"{0}\") 0))" \
                ")" \
            ")".format(rule.rule_name)
        self.lhs_clips_command_list.insert(0, run_once_lhs_expression)
        
        # Check if rule is blocked
        # Prevent it from getting into agenda
        block_check_lhs_expression = \
            "(not " \
                "(__RuleToBlock " \
                   "(rule_name ?rn&: (= (str-compare ?rn \"{0}\") 0))" \
                ")" \
            ")".format(rule.rule_name)
        self.lhs_clips_command_list.insert(0, block_check_lhs_expression)

        # Prevent all non assistance related rules from running,
        # during assistance process
        if not self.is_assistance_session:
            assistance_check_lhs_expression = \
                "(not (__AssistanceOn) )"
            self.lhs_clips_command_list.insert(
                    0, assistance_check_lhs_expression)
        
        # FINALLY BUILD THE RULE
        lhs_commands = ["\t" + comm for comm in self.lhs_clips_command_list]
        rhs_commands = ["\t" + comm for comm in self.rhs_clips_command_list]

        clips_rule = "(defrule " + rule.rule_name + clips_salience + \
                     "\n" + \
                     "\n".join(lhs_commands) + \
                     "\n\t=>\n" + \
                     "\n".join(rhs_commands) + "\n)"

        if self.debug:
            print("\n\nTRANSPILED RULE: ")
            print(clips_rule)
            print("\n\n")
        self.tranpiled_rule = clips_rule



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



    def lhs_clips_code(self, cc):
        clips_command = remove_quotes(cc.clips_code)
        self.lhs_clips_command_list.append(to_clips_quotes(clips_command))
        return 0



    def rhs_clips_code(self, cc):
        clips_command = remove_quotes(cc.clips_code)
        self.rhs_clips_command_list.append(to_clips_quotes(clips_command))
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
                      .format(fav.var_name)
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
                      .format(bv.var_name)
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
            print("DLT from bind: ")
            print(str(self.data_locator_table))
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
            self.get_data_provider(singular.template, bline, bcol)
            clips_command = '(' + singular.template + ')'
            if not singular.operator:
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

        print("\n\nData locator table:")
        print(str( self.data_locator_table))
        print("\n")

        print("\n\nData locator vars:")
        print(str( self.data_locator_vars))
        print("\n")

        print("\n\nSINGULAR OPERAND: ")
        print(singular.operand["content"] + "\n\n")

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

        print("\n\nSINGULAR OPERAND AFTER BUILD: ")
        print(clips_command + "\n\n")

        # Extract used template name
        template = self.clips_statement_builder.get_template(
            self.data_locator_table, 
            self.data_locator_vars
        )

        # Rotate defined variables for next special expression
        self.rotate_used_data_locator_vars()
        self.clear_after_binding_var()
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
        # Rotate defined variables for next special expression
        self.rotate_used_data_locator_vars()
        self.clear_after_binding_var()
        self.data_locator_vars = []

        return 0



    def zero_arg_function(self, func):
        if not func.func_name in self.functions:
            line, col = get_model(obj)._tx_parser \
                        .pos_to_linecol(obj._tx_position)
            message = "Function '{0}' is not defined in any bridge." \
                        .format(func.func_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)
            
        return self.generic_function(func)



    def one_arg_function(self, func):
        if hasattr(func, "template") and func.template != '':
            bline, bcol = get_model(func)._tx_parser \
                         .pos_to_linecol(func._tx_position)
            self.get_data_provider(func.template, bline, bcol)
            clips_content = "(length$ (find-all-facts ((?fct {0})) TRUE)))" \
                            .format(func.template)
            
            resolved_c_type = "INTEGER"
            return {
                "content": clips_content,
                "content_type": resolved_c_type,
                "construct_type": ConstructType.COUNT_FUNC_CALL,
                "_tx_position": (bline, bcol)
            }

        if func.func_name == "not":
            self.check_func_num_of_args(func, 1)
            return self.negation_function(func)
        elif func.func_name == 'count':
            self.check_func_num_of_args(func, 1)
            return self.count_function(func)
        elif func.func_name == 'str':
            self.check_func_num_of_args(func, 1)
            return self.str_function(func)
        else:
            if not func.func_name in self.functions:
                line, col = get_model(func)._tx_parser \
                            .pos_to_linecol(func._tx_position)
                message = "Function '{0}' is not defined in any bridge." \
                          .format(func.func_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
            
            self.check_func_num_of_args(func, 1)
            return self.generic_function(func)



    def one_plus_arg_function(self, func):
        if not func.func_name in self.functions:
            line, col = get_model(func)._tx_parser \
                        .pos_to_linecol(func._tx_position)
            message = "Function '{0}' is not defined in any bridge." \
                        .format(func.func_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)
        
        self.check_func_num_of_args(func, len(func.args))
        return self.generic_function(func)



    def negation_function(self, neg_f):
        result = neg_f.args
        bline, bcol = get_model(neg_f)._tx_parser \
                      .pos_to_linecol(neg_f._tx_position)

        if result["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
            line, col = result["_tx_position"]
            message = "Negation argument type INTEGER, FLOAT or BOOLEAN " \
                      "is expected, but '{0}' found." \
                      .format(result["content_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        if result["content_type"] == ConstructType.WORKABLE:
            clips_content = not result["content"]
            return {
                "content": clips_content, 
                "content_type": py_to_clips_type(clips_content.__class__),
                "construct_type": ConstructType.WORKABLE,
                "_tx_position": (bline, bcol)
            }
        else:
            clips_content = '(not ' + \
                            str(translate_if_c_bool(result["content"])) + \
                            ')'

            resolved_c_type = "BOOLEAN"
            return {
                "content": clips_content, 
                "content_type": resolved_c_type,
                "construct_type": ConstructType.NORMAL_EXP,
                "_tx_position": (bline, bcol)
            }



    def count_function(self, count_f):
        result = count_f.args
        bline, bcol = get_model(count_f)._tx_parser \
                      .pos_to_linecol(count_f._tx_position)

        if result["construct_type"] != ConstructType.NORMAL_EXP:
            line, col = result["_tx_position"]
            message = "Count operation argument must be expression. " \
                      "{0} given.".format(result["construct_type"])
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Build count command if present
        clips_content = self.clips_statement_builder.build_count_pattern(
            self.data_locator_table, 
            self.data_locator_vars, 
            result["content"]
        )

        resolved_c_type = "INTEGER"
        return {
            "content": clips_content,
            "content_type": resolved_c_type,
            "construct_type": ConstructType.COUNT_FUNC_CALL,
            "_tx_position": (bline, bcol)
        }



    def str_function(self, str_f):
        result = str_f.args
        bline, bcol = get_model(str_f)._tx_parser \
                      .pos_to_linecol(str_f._tx_position)

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



    def generic_function(self, generic):
        bline, bcol = get_model(generic)._tx_parser \
                      .pos_to_linecol(generic._tx_position)

        clips_args = []
        if hasattr(generic, "args"):
            args = []
            if isinstance(generic.args, list):
                args = generic.args
            else:
                args.append(generic.args)

            for arg in args:
                c_arg = ""
                if arg["construct_type"] == ConstructType.WORKABLE:
                    c_arg = '"' + str(arg["content"]) + '"'
                else:
                    c_arg = str(arg["content"])
                clips_args.append(c_arg)
                clips_args.append('"' + arg["content_type"] + '"')

        clips_content = "(" + \
                        generic.func_name + ' ' + \
                        " ".join(clips_args) + \
                        ")"
        
        resolved_c_type = self.functions[generic.func_name]["return_type"]
        construct_type = ConstructType.NORMAL_EXP

        return {
            "content": clips_content,
            "content_type": resolved_c_type,
            "construct_type": construct_type,
            "_tx_position": (bline, bcol)
        }



    def logic_expression(self, logic):
        result = logic.operands[0]
        bline, bcol = get_model(logic)._tx_parser \
                      .pos_to_linecol(logic._tx_position)

        l = len(logic.operands)
        i = 1
        while i < l:
            current = logic.operands[i]
            
            if result["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
                line, col = result["_tx_position"]
                message = "Logic operation argument type INTEGER, FLOAT " \
                          "or BOOLEAN is expected, but '{0}' found." \
                          .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if current["content_type"] not in ["INTEGER", "FLOAT", "BOOLEAN"]:
                line, col = current["_tx_position"]
                message = "Logic operation argument type INTEGER, FLOAT " \
                          "or BOOLEAN is expected, but '{0}' found." \
                          .format(current["content_type"])
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
                      str(translate_if_c_bool(current["content"])) + \
                      ')'

                resolved_c_type = resolve_expr_type(
                    "logic", 
                    result["content_type"], 
                    current["content_type"]
                )

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
                message = "Comparison operation of type INTEGER, FLOAT " \
                          "or STRING is expected, but '{0}' found." \
                          .format(result["content_type"])
                print("----" + str(result["content"]))
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if current["content_type"] not in ["INTEGER", "FLOAT", "STRING"]:
                line, col = current["_tx_position"]
                message = "Comparison operation of type INTEGER, FLOAT " \
                          "or STRING is expected, but '{0}' found." \
                          .format(current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            # Resolve eq operaator
            if comp.operator[i-1] == '==':
                operator = '='
            else:
                operator = comp.operator[i-1]

            if ((result["construct_type"]  == ConstructType.WORKABLE \
            and current["construct_type"] == ConstructType.WORKABLE) \
            and ((result["content_type"] in ["INTEGER", "FLOAT"] \
            and current["content_type"] in ["INTEGER", "FLOAT"]) \
            or  (result["content_type"] == "STRING" and \
            current["content_type"] == "STRING"))):
                   
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
                if result["content_type"] == "STRING" and \
                result["construct_type"]  == ConstructType.WORKABLE:
                    op1 = "\"" + result["content"] + "\""
                else:
                    op1 = result["content"]

                if current["content_type"] == "STRING" and \
                current["construct_type"]  == ConstructType.WORKABLE:
                    op2 = "\"" + current["content"] + "\""
                else:
                    op2 = current["content"]
                    
                op1 = translate_if_c_bool(op1)
                op2 = translate_if_c_bool(op2)

                op1_type = result["content_type"]
                op2_type = current["content_type"]

                val = self.clips_statement_builder \
                      .build_string_comparison_expr(
                            op1, op1_type, op2, op2_type, operator)

                resolved_c_type = resolve_expr_type(
                        "comp", 
                        result["content_type"], 
                        current["content_type"]
                )

                # Check if type is resolved correctly
                if resolved_c_type == 1:
                    line, col = result["_tx_position"]
                    message = "Incompatible operand types " \
                              "present in comparison expression."
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
                message = "Addition or subtraction operand type INTEGER " \
                          "or FLOAT is expected, '{0}' but found." \
                          .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
               
            if current["content_type"] not in ["INTEGER", "FLOAT","STRING"]:
                line, col = current["_tx_position"]
                message = "Addition or subtraction operand type INTEGER " \
                          "or FLOAT is expected, but '{0}' found." \
                          .format(current["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            operator = plus_minus.operator[i-1]

            if result["construct_type"]  == ConstructType.WORKABLE \
            and current["construct_type"] == ConstructType.WORKABLE:
                if result["content_type"] == "STRING" \
                or current["content_type"] == "STRING":
                    if operator == '+':
                        val = '"' + str(result["content"]) + \
                              str(current["content"]) + '"'
                    elif operator == '-':
                        line, col = result["_tx_position"]
                        message = "Cannot perform operation 'minus' " \
                                    "on strings."
                        raise AkashicError(message, line, col, 
                                            ErrType.SEMANTIC)

                        val = result["content"] - current["content"]
                elif operator == '+':
                    val = result["content"] + current["content"]
                elif operator == '-':
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
                            result_content = '"' + \
                                             str(result["content"]) + \
                                             '"'
                    else:
                        result_content = str(result["content"]) 

                    if current["construct_type"] == ConstructType.WORKABLE:
                        if current["content_type"] != "STRING": 
                            current_content = str(current["content"]) 
                        else: 
                            current_content = '"' + \
                                              str(current["content"]) + \
                                              '"'
                    else:
                        current_content = str(current["content"]) 

                    val = '(str-cat ' + ' ' + \
                          result_content + ' ' + \
                          current_content + ')'
                    resolved_c_type = resolve_expr_type(
                        "plus_minus", 
                        result["content_type"], 
                        current["content_type"]
                    )

                else:
                    val = '(' + operator + ' ' + \
                        str(result["content"]) + ' ' + \
                        str(current["content"]) + ')'
                    resolved_c_type = resolve_expr_type(
                        "plus_minus", 
                        result["content_type"], 
                        current["content_type"]
                    )

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
        bline, bcol = get_model(mul_div)._tx_parser \
                      .pos_to_linecol(mul_div._tx_position)

        l = len(mul_div.operands)
        i = 1
        while i < l:
            current = mul_div.operands[i]

            if result["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = result["_tx_position"]
                message = "Multiplication or division operand type INTEGER " \
                          "or FLOAT is expected, but '{0}' found." \
                          .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = current["_tx_position"]
                message = "Multiplication or division operand type INTEGER " \
                          "or FLOAT is expected, but '{0}' found." \
                          .format(current["content_type"])
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
                val = '(' + operator + ' ' + \
                      str(result["content"]) + ' ' + \
                      str(current["content"]) + \
                      ')'

                oper_name = "mul"
                if operator == '/':
                    oper_name = "div"
                resolved_c_type = resolve_expr_type(
                    oper_name, 
                    result["content_type"], 
                    current["content_type"]
                )

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
        bline, bcol = get_model(sqr)._tx_parser \
                      .pos_to_linecol(sqr._tx_position)

        l = len(sqr.operands)
        i = 1
        while i < l:
            current = sqr.operands[i]
           
            if result["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = result["_tx_position"]
                message = "Exponentiation or root extraction operand type " \
                          "INTEGER or FLOAT is expected, but '{0}' found." \
                          .format(result["content_type"])
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            if current["content_type"] not in ["INTEGER", "FLOAT"]:
                line, col = current["_tx_position"]
                message = "Exponentiation or root extraction operand type " \
                          "INTEGER or FLOAT is expected, but '{0}' found." \
                          .format(current["content_type"])
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
                val = '(' + operator + ' ' + \
                      str(result["content"]) + ' ' + \
                      str(current["content"]) + \
                      ')'

                resolved_c_type = resolve_expr_type(
                    "sqr", 
                    result["content_type"], 
                    current["content_type"]
                )

                result = {
                    "content": val, 
                    "content_type": resolved_c_type,
                    "construct_type": ConstructType.NORMAL_EXP,
                    "_tx_position": (bline, bcol)
                }

            i += 1
        return result



    def factor(self, factor):
        line, col = get_model(factor)._tx_parser \
                    .pos_to_linecol(factor._tx_position)

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
            # Enters when factor class is: VARIABLE or 
            # DataLocator VALUE ENTRY
            return factor.value



    def variable(self, var):
        var_entry = self.variable_table.lookup(var.var_name)
        if var_entry == None:
            line, col = get_model(var)._tx_parser \
                        .pos_to_linecol(var._tx_position)
            message = "Undefined variable {0}.".format(var.var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)
        else:
            # Add used variables from current variable to the list of 
            # globally used variables
            self.data_locator_vars = list(set(self.data_locator_vars) | \
                                          set(var_entry.used_variables))
            return var_entry.value




    def build_query(self, template_name, field_name, dl_obj):
        self.is_assistance_rule = True

        line_start, col_start = get_model(dl_obj)._tx_parser.pos_to_linecol(
                                    dl_obj._tx_position)
        line_end, col_end = get_model(dl_obj)._tx_parser.pos_to_linecol(
                                    dl_obj._tx_position_end)

        unique_rule_name = str(uuid.uuid4()).replace('-', '')
        arg_array = list([
            '"' + unique_rule_name + '"',
            '"' + template_name + '"',
            '"' + field_name + '"',
            '"' + str(line_start) + '"',
            '"' + str(col_start) + '"',
            '"' + str(line_end) + '"',
            '"' + str(col_end) + '"'
        ])

        clips_command = "(process_query " + " ".join(arg_array) + ")"
        self.assistance_clips_command_list.append(clips_command)

        arg_array = list([
            '"query_rule_name_return"',
            '"data-len"',
            '"3"',
            '"query_rule_name"',
            '"' + "__query_rule_" + unique_rule_name + '"',
            '"STRING"'
        ])

        # Return the name of query RULE to be undefined later
        clips_command = "(return_func " + " ".join(arg_array) + ")"
        self.assistance_clips_command_list.append(clips_command)

        # Turns on the engine's assistance mode ON,
        # This means taht all non query RULES will not be executed
        clips_command = "(assert (__AssistanceOn (id \"something\")) )"
        self.assistance_clips_command_list.append(clips_command)

        print("COMMS:")
        print(self.assistance_clips_command_list)
        # Use direct call to bridge - for debugging
        # self.env_provider.bridges["DataBridge"].process_query(*arg_array)

        return 0


        

    def data_locator(self, data_locator):
        # Get needed data
        template_name = data_locator.template_conn_expr.templates[0]
        field_name = data_locator.field

        # Get position of token
        line, col = get_model(data_locator)._tx_parser \
                    .pos_to_linecol(data_locator._tx_position)

        # Search for existing entry in data locator table
        field = self.data_locator_table.lookup(template_name, field_name)
        if field and field.var_name:
            # Build data query if needed
            if hasattr(data_locator, 'is_query') and \
            data_locator.is_query != None and \
            data_locator.is_query != "":
                print("THEREE IS ????*")
                self.build_query(template_name, field_name, data_locator)

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
                message = "There is no data provider defined for " \
                          "template connection '{0}'." \
                          .format(template_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)
            
            found_dp_field = found_data_provider.field_lookup(field_name)

            if not found_dp_field:
                message = "Template field '{0}' is not defined in data " \
                          "provider's template '{1}'" \
                          .format(field_name, template_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            # Generate new variable and add new entry 
            # to the data locator table
            gen_var_name = self.variable_table.add_helper_var({
                "content": template_name + "." + field_name,
                "content_type": found_dp_field.type,
                "construct_type": ConstructType.NOTHING,
            })
            self.data_locator_vars.append(gen_var_name)
            self.data_locator_table.add(
                template_name, 
                field_name, 
                gen_var_name, 
                found_dp_field
            )

            # Build data query if needed
            if hasattr(data_locator, 'is_query') and \
            data_locator.is_query != None and \
            data_locator.is_query != "":
                print("THEREE IS ????*")
                self.build_query(template_name, field_name, data_locator)
            
            return {
                "content": gen_var_name,
                "content_type": found_dp_field.type,
                "construct_type": ConstructType.VARIABLE,
                "_tx_position": (line, col)
            }



    def check_fact_address_def(self, var_name, field_name, line, col):
        var_entry = self.variable_table.lookup(var_name)
        
        if not var_entry:
            message = "Variable '{0}' is not defined." \
                      .format(var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)
        
        if var_entry.var_type != VarType.FACT_ADDRESS:
            message = "Variable '{0}' is not fact address." \
                      .format(var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        if not "model_id" in var_entry.value:
            message = "Variable '{0}' does not point to any fact." \
                      .format(var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Extract information 
        fact_address_model_id = var_entry.value["model_id"]
        fact_address_field_name = field_name
        
        # Check semantics of fact_address model name and 
        # fact_address field name
        found_data_provider = self.get_data_provider(fact_address_model_id,
                                                     line, 
                                                     col)
        if found_data_provider == None:
            message = "There is no data provider defined for " \
                      "fact address template '{0}'." \
                      .format(fact_address_model_id)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        found_dp_field = self.get_dp_field(fact_address_field_name,
                                           found_data_provider)
        if found_dp_field == None:
            message = "Fact address field '{0}' is not defined in " \
                      "data provider's template '{1}'" \
                      .format(fact_address_field_name,
                              fact_address_model_id)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)



    def lhs_value_locator(self, lhs_vl):
        line, col = get_model(lhs_vl)._tx_parser \
                    .pos_to_linecol(lhs_vl._tx_position)

        self.check_fact_address_def(
            lhs_vl.var_name, 
            lhs_vl.field_name, 
            line, 
            col
        )

        found_field_type = self.get_value_locator_type (
            lhs_vl.var_name, 
            lhs_vl.field_name, 
            line, 
            col
        )

        clips_content = '(fact-slot-value ' + \
                        lhs_vl.var_name + ' ' + \
                        lhs_vl.field_name + ')'

        return {
            "content": clips_content,
            "content_type": found_field_type,
            "construct_type": ConstructType.VARIABLE,
            "_tx_position": (line, col)
        }


# ----------------------------------------------------------------
# RIGHT HAND SIDE SECTION
# ----------------------------------------------------------------


    def get_data_provider(self, model_id, err_line, err_col):
        data_provider = None
        for ds in self.data_providers:
            if ds.dsd.model_id == model_id:
                data_provider = ds

        if not data_provider:
            message = "DSD model with name '{0}' does not exist." \
                        .format(model_id)
            raise AkashicError(message, err_line, err_col, ErrType.SEMANTIC)

        return data_provider



    def get_dp_field(self, field_name, data_provider):
        if data_provider == None:
            return None

        for dp_field in data_provider.dsd.fields:
            if dp_field.field_name == field_name:
                return dp_field
        return None



    def get_json_field(self, field_name, json_field_list):
        if json_field_list == None:
            return None

        for json_field in json_field_list:
            if json_field.name == field_name:
                return json_field
        return None



    def get_value_locator_type(self, var_name, field_name, err_line, err_col):
        var_entry = self.variable_table.lookup(var_name)
        if not "model_id" in var_entry.value:
            message = "Variable '{0}' does not reference any model." \
                      "Therefore it cannot be used as data locator." \
                      .format(var_name)
            raise AkashicError(message, err_line, err_col, ErrType.SEMANTIC)

        data_provider = self.get_data_provider(var_entry.value["model_id"], 
                                               err_line, 
                                               err_col)
        dp_field = self.get_dp_field(field_name, data_provider)
        return dp_field.type

    

    def get_binding_var_type(self, var_name):
        var_entry = self.variable_table.lookup(var_name)
        return var_entry.value["content_type"]



    def check_fact_address_def_rhs(self, json_field, dp_field):
        line, col = get_model(json_field.value)._tx_parser \
                    .pos_to_linecol(json_field.value._tx_position)

        # Check fact address definition aka. data locator
        self.check_fact_address_def(
            json_field.value.var_name,
            json_field.value.field_name,
            line,
            col
        )

        # Check if type of fact accress field is 
        # same as field in json object
        found_dp_field_type = self.get_value_locator_type (
            json_field.value.var_name,
            json_field.value.field_name,
            line,
            col
        )
        if dp_field != None and found_dp_field_type != dp_field.type:
            message = "Type missmatch in field '{0}'. " \
                      "Expected type '{1}'. " \
                      "Given type '{2}'" \
                      .format(json_field.name,
                              dp_field.type,
                              found_dp_field.type)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)



    def check_binding_variable(self, var_obj, dp_field=None):
        line, col = get_model(var_obj)._tx_parser \
                    .pos_to_linecol(var_obj._tx_position)

        var_entry = self.variable_table.lookup(var_obj.var_name)
        
        if var_entry == None:
            message = "Undefined variable {0}.".format(var_obj.var_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        if var_entry.var_type != VarType.BINDING:
            message = "Cannot reference non-binding " \
                      "variable in RHS of the rule."
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        entry_type = var_entry.value["content_type"]
        if dp_field != None and entry_type != dp_field.type:
            message = "Type missmatch in field '{0}'. " \
                      "Expected type '{1}'. Given type is '{2}'." \
                      .format(dp_field.field_name,
                              dp_field.type,
                              entry_type)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)



    def get_primary_key_fields(self, json_object, data_provider):
        data_fields = []
        for dp_field in data_provider.dsd.fields:
            if dp_field.use_as == '\"primary-key\"':
                json_field = self.get_json_field(dp_field.field_name,
                                                 json_object.field_list)
                if json_field != None:
                    data_fields.append((json_field, dp_field))
                else:
                    line, col = get_model(json_object)._tx_parser \
                                .pos_to_linecol(json_object._tx_position)
                    message = "Primary key field '{0}' is omitted " \
                              "from the operation request." \
                              .format(dp_field.field_name)
                    raise AkashicError(message, line, col, ErrType.SEMANTIC)
        return data_fields




    def get_data_fields(self, json_object, data_provider):
        data_fields = []
        for dp_field in data_provider.dsd.fields:
            json_field = self.get_json_field(dp_field.field_name,
                                             json_object.field_list)
            if json_field != None:
                data_fields.append((json_field, dp_field))
            else:
                line, col = get_model(json_object)._tx_parser \
                            .pos_to_linecol(json_object._tx_position)
                message = "Field '{0}' is omitted from the " \
                          "operation request." \
                          .format(dp_field.field_name)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

        return data_fields



    def get_ref_fields(self, json_object, api_operation_obj):
        ref_fields = []
        for ref in api_operation_obj.ref_models:
            json_field = self.get_json_field(ref.url_placement,
                                             json_object.field_list)

            if json_field == None:
                line, col = get_model(json_object)._tx_parser \
                    .pos_to_linecol(json_object._tx_position)
                message = "Foreign model reference field " \
                          "'{0}' is omitted from the " \
                          "operation request." \
                          .format(ref.url_placement)
                raise AkashicError(message, line, col, ErrType.SEMANTIC)

            line, col = get_model(json_field)._tx_parser \
                    .pos_to_linecol(json_field._tx_position)

            data_provider = self.get_data_provider(ref.model_id, line, col)
            dp_field = self.get_dp_field(ref.field_name, data_provider)

            ref_fields.append((json_field, dp_field))
        
        return ref_fields

    

    def analyse_fields(self, fields):
        analysed_fields = []
        for json_field, dp_field in fields:
            err_line, err_col = get_model(json_field)._tx_parser \
                                .pos_to_linecol(json_field._tx_position)

            given_type = py_to_clips_type(json_field.value.__class__)
            json_field_type = None
            json_field_class = None

            if given_type == None:
                if json_field.value.__class__.__name__ == "RHSValueLocator":
                    self.check_fact_address_def_rhs(json_field, dp_field)

                    json_field_type = self.get_value_locator_type(
                        json_field.value.var_name,
                        json_field.value.field_name,
                        err_line,
                        err_col
                    )
                    json_field_class = "RHSValueLocator"

                elif json_field.value.__class__.__name__ == "RHS_VARIABLE":
                    self.check_binding_variable(json_field.value, dp_field)

                    json_field_type = self.get_binding_var_type(
                        json_field.value.var_name
                    )
                    json_field_class = "RHS_VARIABLE"
            
            else:
                if dp_field != None and given_type != dp_field.type:
                    message = "Field '{0}' contains data with " \
                              "wrong type. Expected type is {1}. " \
                              "Found type is {2}." \
                              .format(json_field.name,
                                      dp_field.type,
                                      given_type)
                    raise AkashicError(message, err_line, err_col, 
                                        ErrType.SEMANTIC)
                json_field_type = py_to_clips_type(json_field.value.__class__)
                json_field_class = "NORMAL"

            analysed_fields.append(
                (json_field,
                 json_field_type,
                 json_field_class,
                 dp_field)
            )

        return analysed_fields



    def compile_fields(self, fields):
        arg_list = []

        for json_field, \
        json_field_type, \
        json_field_class, \
        dp_field in fields:

            if json_field_class == "RHSValueLocator":
                arg_list.append('"' + json_field.name + '"')
                arg_list.append('(str-cat (fact-slot-value ' + 
                                json_field.value.var_name + ' ' + 
                                json_field.value.field_name + '))')
                arg_list.append('"' + json_field_type + '"')

            elif json_field_class == "RHS_VARIABLE":
                arg_list.append('"' + json_field.name + '"')

                var_entry = self.variable_table \
                                .lookup(json_field.value.var_name)

                if var_entry.value["content_type"] != "STRING":
                    arg_list.append('(str-cat ' + var_entry.value["content"] + ')')
                elif  var_entry.value["construct_type"] == ConstructType.WORKABLE:
                    arg_list.append('"' + var_entry.value["content"] + '"')
                else:
                     arg_list.append(var_entry.value["content"])
                
                arg_list.append('"' + json_field_type + '"')

            elif json_field_class == "NORMAL":
                arg_list.append('"' + json_field.name + '"')
                arg_list.append('"' + str(json_field.value) + '"')
                arg_list.append('"' + json_field_type + '"')

        return arg_list



    def checkout_duplicates(self, json_field_list, err_line, err_col):
        for i in range(0, len(json_field_list)):
            for j in range(i+1, len(json_field_list)):
                if json_field_list[i].name == json_field_list[j].name:
                    message = "Duplicate fields with name '{0}' detected." \
                              .format(json_field_list[i].name)
                    raise AkashicError(message, 
                                       err_line, 
                                       err_col, 
                                       ErrType.SEMANTIC)


    def check_api_vs_reflect(self, 
                            data_provider,
                            rhs_operation_obj, 
                            api_operation_name):

        # Exit if reflection is needed,
        # but DSD cannot reflect
        if rhs_operation_obj.reflect and \
        not data_provider.dsd.can_reflect:
            line, col = get_model(rhs_operation_obj)._tx_parser \
            .pos_to_linecol(rhs_operation_obj._tx_position)
            message = "Model '{0}' does not support " \
                      "web reflection." \
                      .format(rhs_operation_obj.model_id)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)

        # Exit if reflection is needed, 
        # but DSD does not have given operation api
        if (rhs_operation_obj.reflect) and \
        not hasattr(data_provider.dsd.apis, api_operation_name):
            line, col = get_model(rhs_operation_obj)._tx_parser \
            .pos_to_linecol(rhs_operation_obj._tx_position)
            message = "Model '{0}' does not support " \
                      "'{1}' operation." \
                      .format(rhs_operation_obj.model_id,
                              api_operation_name)
            raise AkashicError(message, line, col, ErrType.SEMANTIC)



##############################################################
#### Model processors

    def rhs_statement(self, rhs):
        if rhs.stat.__class__.__name__ == "CLIPS_CODE":
            clips_command = remove_quotes(rhs.stat.clips_code)
            self.rhs_clips_command_list.append(to_clips_quotes(clips_command))

    

    def create_update_generic(self, 
                              rhs_operation_obj, 
                              api_operation_name):

        line, col = get_model(rhs_operation_obj)._tx_parser \
                    .pos_to_linecol(rhs_operation_obj._tx_position)

        # Find data provider for given model
        data_provider = self.get_data_provider(rhs_operation_obj.model_id,
                                               line, 
                                               col)

        # Check reflection option against settings in DSD
        self.check_api_vs_reflect(data_provider,
                                  rhs_operation_obj, 
                                  api_operation_name)

        # Check field list for duplicate fileds
        self.checkout_duplicates(rhs_operation_obj.json_object.field_list,
                                 line, 
                                 col)

        # DO NOT GET REFS IF NOT REFLECT
        # Separate data and do primary field checks
        data_fields = self.get_data_fields(rhs_operation_obj.json_object,
                                           data_provider)
        
        ref_fields = []
        if rhs_operation_obj.reflect:
            ref_fields = self.get_ref_fields(rhs_operation_obj.json_object,
                                            getattr(data_provider.dsd.apis,
                                                    api_operation_name))
        
        # Do forther analysis and checks on data,
        # and generate prep structure for compilation
        a_data_fields = self.analyse_fields(data_fields)
        a_ref_fields = self.analyse_fields(ref_fields)

        # Compile prep structure to the list of CLIPS function args
        data_arg_list = self.compile_fields(a_data_fields)
        ref_arg_list = self.compile_fields(a_ref_fields)

        arg_array = list([
            '"' + rhs_operation_obj.model_id + '"',
            "\"reflect\"",
            '"' + str(rhs_operation_obj.reflect) + '"',
            "\"data-len\"",
            '"' + str(len(data_arg_list)) + '"',
            *data_arg_list,
            "\"ref-len\"",
            '"' + str(len(ref_arg_list)) + '"',
            *ref_arg_list
        ])

        return arg_array




    def create_statement(self, create_s):
        arg_array = self.create_update_generic(
            create_s,
            'create'
        )

        clips_command = "(create_func " + " ".join(arg_array) + ")"
        self.rhs_clips_command_list.append(clips_command)

        # Use direct call to bridge - for debugging
        # self.env_provider.bridges["DataBridge"].create_func(*arg_array)
    


    def update_statement(self, update_s):
        arg_array = self.create_update_generic(
            update_s,
            'update'
        )

        clips_command = "(update_func " + " ".join(arg_array) + ")"
        self.rhs_clips_command_list.append(clips_command)

        # Use direct call to bridge - for debugging
        # self.env_provider.bridges["DataBridge"].update_func(*arg_array)



    def return_statement(self, return_s):
        line, col = get_model(return_s)._tx_parser \
                    .pos_to_linecol(return_s._tx_position)

        # Check field list for duplicate fileds
        self.checkout_duplicates(return_s.json_object.field_list,
                                 line, 
                                 col)

        all_fields = [(json_field, None) for json_field in \
                     return_s.json_object.field_list]

        # Do forther analysis and checks on data,
        # and generate prep structure for compilation
        a_all_fields = self.analyse_fields(all_fields)

        # Compile prep structure to the list of CLIPS function args
        all_arg_list = self.compile_fields(a_all_fields)

        arg_array = list([
            '"' + return_s.tag + '"',
            "\"data-len\"",
            '"' + str(len(all_arg_list)) + '"',
            *all_arg_list
        ])

        clips_command = "(return_func " + " ".join(arg_array) + ")"
        self.rhs_clips_command_list.append(clips_command)

        # Use direct call to bridge - for debugging
        #self.env_provider.bridges["DataBridge"].return_func(*arg_array)



    def delete_statement(self, delete_s):
        line, col = get_model(delete_s)._tx_parser \
                    .pos_to_linecol(delete_s._tx_position)

        # Find data provider for given model
        data_provider = self.get_data_provider(delete_s.model_id,
                                               line, 
                                               col)

        # Check reflection option against settings in DSD
        self.check_api_vs_reflect(data_provider,
                                  delete_s, 
                                  'delete')

        # Check field list for duplicate fileds
        self.checkout_duplicates(delete_s.json_object.field_list,
                                 line, 
                                 col)

        # Take only refs
        if delete_s.reflect:
            ref_fields = self.get_ref_fields(delete_s.json_object, 
                                            getattr(data_provider.dsd.apis, 
                                                    'delete'))
        else:
            ref_fields = self.get_primary_key_fields(delete_s.json_object,
                                                     data_provider)
        
        # Do forther analysis and checks on data,
        # and generate prep structure for compilation
        a_ref_fields = self.analyse_fields(ref_fields)

        # Compile prep structure to the list of CLIPS function args
        ref_arg_list = self.compile_fields(a_ref_fields)

        arg_array = list([
            '"' + delete_s.model_id + '"',
            "\"reflect\"",
            '"' + str(delete_s.reflect) + '"',
            "\"ref-len\"",
            '"' + str(len(ref_arg_list)) + '"',
            *ref_arg_list
        ])

        clips_command = "(delete_func " + " ".join(arg_array) + ")"
        self.rhs_clips_command_list.append(clips_command)

        # Use direct call to bridge - for debugging
        # self.env_provider.bridges["DataBridge"].delete_func(*arg_array)

