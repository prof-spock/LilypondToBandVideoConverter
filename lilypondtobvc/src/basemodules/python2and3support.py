# -*- coding: utf-8-unix -*-
# Python2And3Support - provides functions for supporting both
#                      Python 2 and 3

#====================

import sys

#====================

isPython2 = (sys.version_info < (3,))
isPython3 = not isPython2

#====================

def isInteger (value):
    """Python version independent version of integer type check"""

    isOkay = isinstance(value, int)
    
    if isPython2 and not isOkay:
        isOkay = isinstance(value, long)
        
    return isOkay

#--------------------

def isString (value):
    """Python version independent version of string type check"""

    isOkay = isinstance(value, str)

    if isPython2 and not isOkay:
        isOkay = isinstance(value, unicode)

    return isOkay

#--------------------

def toUnicodeString (st):
    """Converts plain string <st> to unicode string and returns it"""

    return st if (isPython3 or isinstance(st, unicode)) else unicode(st)
