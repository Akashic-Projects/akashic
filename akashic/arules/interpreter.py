from textx import metamodel_from_file
from textx.export import metamodel_export, model_export

from os.path import join, dirname

from akashic.arules.symbol_table import SymbolTable, Type, Entry


# Should be transpiler
class RulesInterpreter(object):

    def __init__(self, data_provider):
        self.data_provider = data_provider
        self.symbol_table = SymbolTable()

        processors = {
            'RHSStatement': self.rhs_statement
            'NegationExpression': self.negation_expression,
            'LogicExpression': self.logic_expression,
            'CompExpression': self.comp_expression,
            'PlusMinusExpr': self.plus_minus_expr,
            'MulDivExpr': self.mul_div_expr,
            'SqrExpr': self.sqr_expr,
            'Factor': self.factor,
            'STRING_C': self.string_c,
            'DataLocator': self.data_locator,
        }

        this_folder = dirname(__file__)
        self.meta_model = metamodel_from_file(join(this_folder, 'meta_model.tx'), debug=False)
        self.meta_model.register_obj_processors(processors)

        self.rule = None


    def load(self, akashic_rule):
        self.rule = self.meta_model.model_from_str(akashic_rule)


    # For testing -> extracting data after processing
    def get_data(self):
        print("\n")
        print(str(self.rule.rhs.statements[0].func.var) + " = " + str(self.rule.rhs.statements[0].expr))

    def rhs_statement(self, rhss):
        pass

    def negation_expression(self, neg):
        if neg.operator != "not":
            return neg.operand

        if neg.operand.__class__ == bool or neg.operand.__class__ == int or neg.operand.__class__ == float or neg.operand.__class__ == str:
            return not neg.operand 
           

    def logic_expression(self, logic):
        if len(logic.operands) < 2:
            return logic.operands[0]

        if ((logic.operands[0].__class__ == bool or logic.operands[0].__class__ == int or logic.operands[0].__class__ == float or logic.operands[0].__class__ == str)
            and (logic.operands[1].__class__ == bool or logic.operands[1].__class__ == int or logic.operands[1].__class__ == float or logic.operands[1].__class__ == str)):
            
            val = None
            if logic.operator[0] == 'and':
                val = logic.operands[0] and logic.operands[1]
            if logic.operator[0] == 'or':
                val = logic.operands[0] or logic.operands[1]

            return val


    def comp_expression(self, comp):
        if len(comp.operands) < 2:
            return comp.operands[0]

        if ((comp.operands[0].__class__ == int or comp.operands[0].__class__ == float)
            and (comp.operands[1].__class__ == int or comp.operands[1].__class__ == float)
            or (comp.operands[0].__class__ == str and comp.operands[1].__class__ == str)):
            
            val = None
            if comp.operator[0] == '==':
                val = comp.operands[0] == comp.operands[1]
            if comp.operator[0] == '!=':
                val = comp.operands[0] != comp.operands[1]
            if comp.operator[0] == '<':
                val = comp.operands[0] < comp.operands[1]
            if comp.operator[0] == '>':
                val = comp.operands[0] > comp.operands[1]
            if comp.operator[0] == '<=':
                val = comp.operands[0] <= comp.operands[1]
            if comp.operator[0] == '>=':
                val = comp.operands[0] >= comp.operands[1]

            return val


    def plus_minus_expr(self, plus_minus):
        if len(plus_minus.operands) < 2:
            return plus_minus.operands[0]

        if ((plus_minus.operands[0].__class__ == int or plus_minus.operands[0].__class__ == float)
            and (plus_minus.operands[1].__class__ == int or plus_minus.operands[1].__class__ == float)):
            
            val = None
            if plus_minus.operator[0] == '+':
                val = plus_minus.operands[0] + plus_minus.operands[1]
            if plus_minus.operator[0] == '-':
                val = plus_minus.operands[0] - plus_minus.operands[1]
            
            return val



    def mul_div_expr(self, mul_div):
        if len(mul_div.operands) < 2:
            return mul_div.operands[0]
        
        if ((mul_div.operands[0].__class__ == int or mul_div.operands[0].__class__ == float)
            and (mul_div.operands[1].__class__ == int or mul_div.operands[1].__class__ == float)):
            
            val = None
            if mul_div.operator[0] == '*':
                val = mul_div.operands[0] * mul_div.operands[1]
            if mul_div.operator[0] == '/':
                val = mul_div.operands[0] / mul_div.operands[1]
            
            return val



    def sqr_expr(self, sqr):
        if len(sqr.operands) < 2:
            return sqr.operands[0]
      
        if ((sqr.operands[0].__class__ == int or sqr.operands[0].__class__ == float)
        and (sqr.operands[1].__class__ == int or sqr.operands[1].__class__ == float)):
            return sqr.operands[0] ** sqr.operands[1]


    def factor(self, factor):
        #print("Class of operand: " + factor.value.__class__.__name__)
        return factor.value


    def string_c(self, s):
        return s.val


    def data_locator(self, loc):
        links = loc.link_expr.links
        for l in links:
            print("link: " + str(l))

        for a in loc.attributes:
            print("attribute: " + str(a))