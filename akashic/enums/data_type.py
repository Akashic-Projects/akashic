from enum import Enum

class DataType(Enum):
    """ DataType enum class

    We use this class to define type of data generated
    inside of transpiler loop
    """

    def __str__(self):
        return str(self.name)

    INTEGER  = 1
    FLOAT    = 2
    STRING   = 3
    BOOLEAN  = 5