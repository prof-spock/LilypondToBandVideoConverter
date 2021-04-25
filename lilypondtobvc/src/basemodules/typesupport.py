# typesupport - provides simple type checking functions
#
# author: Dr. Thomas Tensi, 2014

#====================

def isInteger (value):
    """tells whether value is an integer"""

    result = isinstance(value, int)
    return result

#--------------------

def isString (value):
    """tells whether value is a string"""

    result = isinstance(value, str)
    return result
