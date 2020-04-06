
def resolve_types(operation_name, o1_type, o2_type):
    if operation_name == 'sqr':
        if o1_type == "FLOAT" or o2_type == "FLOAT":
            return "FLOAT"
        else:
            return "INTEGER"