
# TODO: Check if BOOLEAN is really needed here
def clips_to_py_type(ctype):
    """ Converts CLIPS type to Python type
    
    Parameters
    ----------
    ctype : str
        CLIPS type, possible values: "INTEGER", "FLOAT", "STRING" and maybe "BOOLEAN"

    Returns
    -------
    ptype: type
        Coresponding python type
    """

    ptype = None
    if ctype == "INTEGER":
        ptype = int
    elif ctype == "FLOAT":
        ptype = float
    elif ctype == "STRING":
        ptype = str
    elif ctype == "BOOLEAN":
        ptype = bool
    return ptype



def py_to_clips_type(ptype):
    """ Converts Python type to CLIPS type
    
    Parameters
    ----------
    ptype : str
        Python type

    Returns
    -------
    ctype: str
        Coresponding CLIPS type
    """

    ctype = None
    if ptype == int:
        ctype = "INTEGER"
    elif ptype == float:
        ctype = "FLOAT"
    elif ptype == str:
        ctype = "STRING"
    elif ptype == bool:
        ctype = "BOOLEAN"
    return ctype