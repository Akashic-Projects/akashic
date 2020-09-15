
def resolve_expr_type(operation_name, o1_type, o2_type):
    if operation_name == 'sqr':
        if o1_type == "FLOAT" or o2_type == "FLOAT":
            return "FLOAT"
        else:
            return "INTEGER"
    
    elif operation_name == 'mul':
        if o1_type == "FLOAT" or o2_type == "FLOAT":
            return "FLOAT"
        else:
            return "INTEGER"
    
    elif operation_name == 'div':
        return "FLOAT"

    
    elif operation_name == 'plus_minus':
        if o1_type == "FLOAT" or o2_type == "FLOAT":
            return "FLOAT"
        elif o1_type == "STRING" or o2_type == "STRING":
            return "STRING"
        else:
            return "INTEGER"
    
    elif operation_name == 'comp':
        if ((o1_type in ["INTEGER", "FLOAT"] 
        and o2_type in  ["INTEGER", "FLOAT"])
        or  (o1_type == "STRING" 
        and o2_type == "STRING")
        or  (o1_type == "BOOLEAN" 
        and o2_type == "BOOLEAN")):
            return "BOOLEAN"
        else: 
            return 1

    elif operation_name == 'logic':
        return "BOOLEAN"