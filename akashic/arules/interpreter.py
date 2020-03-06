from textx import metamodel_from_file
from textx.export import metamodel_export, model_export

from os.path import join, dirname

# Should be transpiler
class RulesInterpreter(object):

    def __init__(self, data_provider):
        self.data_provider = data_provider

        processors = {
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


    def negation_expression(self, neg):
        print("\n--")
        print("neg len: 1")
        print("neg zero op: " + str(neg.operand))
        if neg.operator != "not":
            return neg.operand

        if neg.operand.__class__ == bool or neg.operand.__class__ == int or neg.operand.__class__ == float or neg.operand.__class__ == str:
            print("OP: " + str(neg.operator))
            
            val = not neg.operand 
            print("neg ret value: " + str(val))
            print("--\n")
            return val
           

    def logic_expression(self, logic):
        print("\n--")
        print("logic len: " + str(len(logic.operands)))
        print("logic zero op: " + str(logic.operands[0]))
        if len(logic.operands) < 2:
            return logic.operands[0]

        print("logic one op: " + str(logic.operands[1]))
        if ((logic.operands[0].__class__ == bool or logic.operands[0].__class__ == int or logic.operands[0].__class__ == float or logic.operands[0].__class__ == str)
            and (logic.operands[1].__class__ == bool or logic.operands[1].__class__ == int or logic.operands[1].__class__ == float or logic.operands[1].__class__ == str)):
            
            print("OP: " + str(logic.operator[0]))
            if logic.operator[0] == 'and':
                val = logic.operands[0] and logic.operands[1]
                print("logic ret value: " + str(val))
                print("--\n")
                return val
            if logic.operator[0] == 'or':
                val = logic.operands[0] or logic.operands[1]
                print("logic ret value: " + str(val))
                print("--\n")
                return val



    def comp_expression(self, comp):
        print("\n--")
        print("comp len: " + str(len(comp.operands)))
        print("comp zero op: " + str(comp.operands[0]))
        if len(comp.operands) < 2:
            return comp.operands[0]

        print("comp one op: " + str(comp.operands[1]))
        if ((comp.operands[0].__class__ == int or comp.operands[0].__class__ == float)
            and (comp.operands[1].__class__ == int or comp.operands[1].__class__ == float)
            or (comp.operands[0].__class__ == str and comp.operands[1].__class__ == str)):
            
            print("OP: " + str(comp.operator[0]))
            if comp.operator[0] == '==':
                val = comp.operands[0] == comp.operands[1]
                print("comp ret value: " + str(val))
                print("--\n")
                return val
            if comp.operator[0] == '!=':
                val = comp.operands[0] != comp.operands[1]
                print("comp ret value: " + str(val))
                print("--\n")
                return val
            if comp.operator[0] == '<':
                val = comp.operands[0] < comp.operands[1]
                print("comp ret value: " + str(val))
                print("--\n")
                return val
            if comp.operator[0] == '>':
                val = comp.operands[0] > comp.operands[1]
                print("comp ret value: " + str(val))
                print("--\n")
                return val
            if comp.operator[0] == '<=':
                val = comp.operands[0] <= comp.operands[1]
                print("comp ret value: " + str(val))
                print("--\n")
                return val
            if comp.operator[0] == '>=':
                val = comp.operands[0] >= comp.operands[1]
                print("comp ret value: " + str(val))
                print("--\n")
                return val


    def plus_minus_expr(self, plus_minus):
        print("\n--")
        print("plus len: " + str(len(plus_minus.operands)))
        print("plus zero op: " + str(plus_minus.operands[0]))
        if len(plus_minus.operands) < 2:
            return plus_minus.operands[0]

        print("plus one op: " + str(plus_minus.operands[1]))
        if ((plus_minus.operands[0].__class__ == int or plus_minus.operands[0].__class__ == float)
            and (plus_minus.operands[1].__class__ == int or plus_minus.operands[1].__class__ == float)):
            
            print("OP: " + str(plus_minus.operator[0]))
            if plus_minus.operator[0] == '+':
                val = plus_minus.operands[0] * plus_minus.operands[1]
                print("plus ret value: " + str(val))
                print("--\n")
                return val
            if plus_minus.operator[0] == '-':
                val = plus_minus.operands[0] * plus_minus.operands[1]
                print("plus ret value: " + str(val))
                print("--\n")
                return val



    def mul_div_expr(self, mul_div):
        print("\n--")
        print("mul len: " + str(len(mul_div.operands)))
        print("mul zero op: " + str(mul_div.operands[0]))
        if len(mul_div.operands) < 2:
            return mul_div.operands[0]

        print("mul one op: " + str(mul_div.operands[1]))
        
        if ((mul_div.operands[0].__class__ == int or mul_div.operands[0].__class__ == float)
            and (mul_div.operands[1].__class__ == int or mul_div.operands[1].__class__ == float)):
            
            print("OP: " + str(mul_div.operator[0]))
            if mul_div.operator[0] == '*':
                val = mul_div.operands[0] * mul_div.operands[1]
                print("mul ret value: " + str(val))
                print("--\n")
                return val
            if mul_div.operator[0] == '/':
                val = mul_div.operands[0] / mul_div.operands[1]
                print("mul ret value: " + str(val))
                print("--\n")
                return val



    def sqr_expr(self, sqr):
        print("\n--")
        print("sqr len: " + str(len(sqr.operands)))
        print("sqr zero op: " + str(sqr.operands[0]))
        if len(sqr.operands) < 2:
            return sqr.operands[0]

        print("sqr one op: " + str(sqr.operands[1]))
        
        if ((sqr.operands[0].__class__ == int or sqr.operands[0].__class__ == float)
            and (sqr.operands[1].__class__ == int or sqr.operands[1].__class__ == float)):
            
            print("OP: " + str(comp.operator[0]))

            val = sqr.operands[0] ** sqr.operands[1]
            print("sqr ret value: " + str(val))
            print("--\n")
            return val


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