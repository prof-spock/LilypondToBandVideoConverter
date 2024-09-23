# typesupport - provides simple type checking functions
#
# author: Dr. Thomas Tensi, 2014

#====================

import re
import sys

from basemodules.simpletypes import Boolean, Integer, Object, Real, \
                                    String

#====================

_integerRegExp = re.compile(r"\-?[0-9]+")
_realRegExp    = re.compile(r"\-?[0-9]+(\.[0-9]+)?")

#--------------------
#--------------------

def isInteger (value : Object) -> Boolean:
    """tells whether value is an integer"""

    result = isinstance(value, int)
    return result

#--------------------

def isIntegerString (value : String) -> Boolean:
    """tells whether value is an integer value as a string"""

    return _integerRegExp.match(value)

#--------------------

def isRealString (value : String) -> Boolean:
    """tells whether value is a real value as a string"""

    return _realRegExp.match(value)

#--------------------

def isString (value : Object) -> Boolean:
    """Tells whether value is a string"""

    result = isinstance(value, str)
    return result

#--------------------

def isStringList (value : Object) -> Boolean:
    """Tells whether value is a string list"""

    isOkay = isinstance(value, list)

    if isOkay:
        isOkay = all([isString(x) for x in value])

    return isOkay

#--------------------

def isStringMap (value : Object) -> Boolean:
    """Tells whether value is a string map"""

    isOkay = isinstance(value, dict)

    if isOkay:
        isOkay = all([isString(x) for x in value.keys()])

    return isOkay

#--------------------

# support for python version 2
toUnicodeString = unicode if sys.version_info[0] == 2 else str
