

class VariableAlreadyDefinedError(Exception):
    pass


class SyntacticError(Exception):
    def __init(self, message):
        self.message = message


class SemanticError(Exception):
    def __init(self, message):
        self.message = message