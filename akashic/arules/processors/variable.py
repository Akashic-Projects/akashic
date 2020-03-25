from akashic.exceptions import SemanticError


def variable(self, var):
    var_entry = self.variable_table.lookup(var.var_name)
    if var_entry == None:
        raise SemanticError("Undefined variable {0}.".format(var.var_name))
    else:
        return var_entry.value