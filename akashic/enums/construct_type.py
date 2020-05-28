from enum import Enum

class ConstructType(Enum):
    """ ConstructType enum class

    We use this class to define type of construct
    generated inside of transpiler loop
    """

    def __str__(self):
        return str(self.name)

    WORKABLE            = 1
    VARIABLE            = 2
    NORMAL_EXP         = 3
    FUNCTION_CALL       = 4
    SPECIAL_CON_EXP     = 5 # Special Conditional Expression 
    NOTHING             = 6