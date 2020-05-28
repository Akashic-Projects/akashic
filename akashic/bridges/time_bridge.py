import datetime

from akashic.util.type_converter import py_to_clips_type
from akashic.exceptions import AkashicError, ErrType


class TimeBridge(object):
    """ TimeBridge class
        
    We use this class to store time and date related python
    functions called by CLIPS enviroment
    """


    def str_to_time(self, time_str, time_format):
        if time_str == 'now':
            date_time_obj = datetime.datetime.now()
        else:
            date_time_obj = datetime.datetime.strptime(time_str, time_format)

        return int(date_time_obj.timestamp())



    def time_to_str(self, time, time_format):
        date_time_obj = datetime.datetime.fromtimestamp(int(time))

        return date_time_obj.strftime(time_format)


    def sub_times(self, time1, time2):
        date_time_obj1 = datetime.datetime.fromtimestamp(int(time1))
        date_time_obj2 = datetime.datetime.fromtimestamp(int(time2))

        return (date_time_obj1 - date_time_obj2).total_seconds()