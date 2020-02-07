from textx import metamodel_from_file
from textx.export import metamodel_export, model_export

from os.path import join, dirname

class RulesInterpreter(object):

    def __init__(self):
        processors = {
            'LogicExpression': self.logic_expression,
            'CompExpression': self.comp_expression,
            'PlusMinusExpr': self.plus_minus_expr,
            'MulDivExpr': self.mul_div_expr,
            'SqrExpr': self.sqr_expr,
            'Factor': self.factor,
            'DataLocator': self.data_locator,
        }

        this_folder = dirname(__file__)
        self.meta_model = metamodel_from_file(join(this_folder, 'meta_model.tx'), debug=False)
        self.meta_model.register_obj_processors(processors)

    def interpret(self, akashic_rule):
         self.meta_model.model_from_str(akashic_rule)

    def logic_expression(self, logic):
        pass

    def comp_expression(self, comp):
        pass

    def plus_minus_expr(self, plus_minus):
        pass

    def mul_div_expr(self, mul_div):
        pass

    def sqr_expr(self, sqr):
        pass

    def mul_div_expr(self, mul_div):
        pass

    def factor(self, factor):
        print("Class of operand: " + factor.value.__class__.__name__)

    def data_locator(self, loc):
        links = loc.link_expr.links
        for l in links:
            print("link: " + str(l))

        for a in loc.attributes:
            print("attribute: " + str(a))