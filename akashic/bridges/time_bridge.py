import datetime

from akashic.util.type_converter import string_to_py_type
from akashic.exceptions import AkashicError, ErrType


class TimeBridge(object):
    """ TimeBridge class
        
    We use this class to store time and date related python
    functions called by CLIPS enviroment
    """

    def __init__(self):
        self.exposed_functions= [
            {
                "function":     self.now,
                "num_of_args":  0,
                "return_type":  "INTEGER"
            },
            {
                "function":     self.str_to_time,
                "num_of_args":  2,
                "return_type":  "INTEGER"
            },
            {
                "function":     self.time_to_str,
                "num_of_args":  2,
                "return_type":  "STRING"
            },
            {
                "function":     self.sub_times,
                "num_of_args":  2,
                "return_type":  "INTEGER"
            }
        ]



    def now(self):
        date_time_obj = datetime.datetime.now()
        return int(date_time_obj.timestamp())



    def str_to_time(self, time_str, type1, time_format, type2):
        print("TIME B str_to_time")
        date_time_obj = datetime.datetime.strptime(time_str, time_format)
        return int(date_time_obj.timestamp())



    def time_to_str(self, time, type1, time_format, type2):
        print("TIME B time_to_str")
        date_time_obj = datetime.datetime.fromtimestamp(int(time))
        return date_time_obj.strftime(time_format)



    def sub_times(self, time1, type1, time2, type2):
        date_time_obj1 = datetime.datetime.fromtimestamp(int(time1))
        date_time_obj2 = datetime.datetime.fromtimestamp(int(time2))

        result = (date_time_obj1 - date_time_obj2).total_seconds()
        print("TIME BETWEEN IN SECS: " + str(result))
        return int(result)