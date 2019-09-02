from enum import Enum


class ObjType(Enum):
    '''
    Enum to control rendering order of object types
    Lower numbers have higher priority (rendered last)
    '''
    mob = 1
    item = 2
    appliance = 3
    static = 4
