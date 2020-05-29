
from enum import Enum


class ErrType(Enum):
    def __str__(self):
        return str(self.name)

    SEMANTIC  = 1
    SYNTACTIC = 2
    SYSTEM    = 3
    

class AkashicError(Exception):
    def __init__(self, message, line=0, col=0, err_type=None):
        super(AkashicError, self).__init__(message.encode('utf-8'))
        self.message = message
        self.line = line
        self.col = col
        self.err_type = str(err_type)
       
    def __str__(self):
        if self.line and self.col:
            # gcc style error format
            return "{}:{}: error: {}".format(
                str(self.line),
                str(self.col),
                self.message
            )
        else:
            return super(AkashicError, self).__str__()