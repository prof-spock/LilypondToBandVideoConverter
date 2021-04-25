# validitychecker - allows checking of validity of values (typically
#                   of input parameters from the command line)
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import os
import re
import sys

import basemodules.typesupport as typesupport
from .simplelogging import Logging
from .ttbase import iif

#====================

class ValidityChecker:
    """Provides checking of validity of values (typically command line
       parameters). Assumes that a check failure is fatal."""

    @classmethod
    def _checkTemplate (cls, typeName, valueName, value):
        result = "--: checking %r for being %s (%r)"
        result = result % (valueName, typeName, value)
        return result

    #--------------------

    @classmethod
    def _checkForType (cls, kind, kindName, valueName, value):
        Logging.trace(cls._checkTemplate(kindName, valueName, value))
        message = "%r must be %s: %s" % (valueName, kindName, value)
        cls.isValid(isinstance(value, kind), message)

    #--------------------

    @classmethod
    def _constructErrorMessage (cls, template, value, valueName):
        """Makes an error message from <template> and <value>
           depending on whether <valueName> is given or not."""

        if valueName is None:
            result = template % (value, "")
        else:
            result = template % (value, " (" + valueName + ")")

        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def isOfKind (cls, value, valueName, kind):
        """Checks whether <value> named <valueName> has <kind>; otherwise
           exits program with an appropriate message"""

        Logging.trace(">>: value = %r, valueName = %r, kind = %r",
                      value, valueName, kind)

        if kind == "B":
            cls.isBoolean(value, valueName)
        elif kind == "N":
            cls.isInteger(value, valueName)
        elif kind == "PN":
            cls.isInteger(value, valueName)
        elif kind == "I":
            cls.isInteger(value, valueName)
        elif kind == "F":
            cls.isFloat(value, valueName)
        elif kind == "S":
            cls.isString(value, valueName)
        elif kind == "SL":
            cls.isStringList(value, valueName)
        elif kind == "SM":
            cls.isStringMap(value, valueName)
        elif kind == "RF":
            cls.isReadableFile(value, valueName)
        elif kind == "WF":
            cls.isWritableFile(value, valueName)
        elif kind == "WD":
            cls.isDirectory(value, valueName)

        Logging.trace("<<")
    
    #--------------------

    @classmethod
    def isBoolean (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           a boolean, otherwise exits program with a message."""

        cls._checkForType(bool, "a boolean", valueName, value)

    #--------------------

    @classmethod
    def isDirectory (cls, pathName, valueName=None):
        """Checks whether directory given by <pathName> is readable,
           otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a directory", valueName, pathName))
        template = "Directory '%s'%s is not readable."
        message = cls._constructErrorMessage(template, pathName, valueName)
        cls.isValid(os.path.isdir(pathName), message)

    #--------------------

    @classmethod
    def isInteger (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           an integer or long integer, otherwise exits program with a
           message."""

        Logging.trace(cls._checkTemplate("an integer", valueName, value))
        message = "%s must be an integer: %r" % (valueName, value)
        cls.isValid(typesupport.isInteger(value), message)

    #--------------------

    @classmethod
    def isFloat (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           a float, otherwise exits program with a message."""

        cls._checkForType(float, "a float", valueName, value)

    #--------------------

    @classmethod
    def isList (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           a list, otherwise exits program with a message."""

        cls._checkForType(list, "a list", valueName, value)

    #--------------------

    @classmethod
    def isMap (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           a map, otherwise exits program with a message."""

        cls._checkForType(dict, "a map", valueName, value)

    #--------------------

    @classmethod
    def isNatural (cls, value, valueName, zeroIsIncluded=True):
        """Checks whether <value> of variable given by <valueName> is
           a positive integer or long integer, otherwise exits
           program with a message.  When <zeroIsIncluded> is set, also
           zero is acceptable."""

        kindName = "a " + iif(zeroIsIncluded, "", "positive ") + "natural"
        Logging.trace(cls._checkTemplate(kindName, valueName, value))
        message = ("%s must be %s: %r" % (valueName, kindName, value))
        cls.isValid(typesupport.isInteger(value)
                    and (value > 0 or value == 0 and zeroIsIncluded),
                    message)

    #--------------------

    @classmethod
    def isNumberString (cls, value, valueName, floatIsAllowed, rangeKind=""):
        """Checks whether string <value> with name <valueName> is
           representation of a correct number. <floatIsAllowed> tells
           whether non-integer values are okay, <rangeKind> gives an
           boundary condition about the range."""

        Logging.trace(">>: %s = %r (%s), floatIsOk = %r, rangeKind = %r",
                      valueName, value, type(value), floatIsAllowed, rangeKind)

        floatRegexp   = re.compile(r"^\-?[0-9]+(\.[0-9]*)?$")
        integerRegexp = re.compile(r"^\-?[0-9]+$")

        value = str(value)
        isOkay = (integerRegexp.match(value) is not None)

        if floatIsAllowed and not isOkay:
            isOkay = (floatRegexp.match(value) is not None)

        if not isOkay:
            errorTemplate = iif(floatIsAllowed, "a number", "an integer")
            errorTemplate = "%s must be " + errorTemplate + " - %s"
        elif rangeKind == "":
            errorTemplate = "%s%s"
        else:
            if rangeKind == ">0":
                errorTemplate = "positive"
                isOkay = (float(value) > 0)
            elif rangeKind == ">=0":
                errorTemplate = "positive or zero"
                isOkay = (float(value) >= 0)

            errorTemplate = "%s must be " + errorTemplate + " - %r"

        cls.isValid(isOkay, errorTemplate % (valueName, value))

        Logging.trace("<<: %r", isOkay)

    #--------------------

    @classmethod
    def isReadableFile (cls, pathName, valueName=None):
        """Checks whether file given by <pathName> is readable,
           otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a readableFile",
                                         valueName, pathName))
        template = "File '%s'%s is not readable."
        message = cls._constructErrorMessage(template, pathName, valueName)
        cls.isValid(os.path.isfile(pathName), message)

    #--------------------

    @classmethod
    def isString (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           a unicode string, otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a (unicode) string",
                                         valueName, value))
        message = "%r must be a string: %r" % (valueName, value)
        cls.isValid(typesupport.isString(value), message)

    #--------------------

    @classmethod
    def isWritableFile (cls, pathName, valueName=None):
        """Checks whether file given by <pathName> is writable,
           otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a writable file",
                                         valueName, pathName))
        template = "File '%s'%s cannot be written."
        message = cls._constructErrorMessage(template, pathName, valueName)
        directoryName = os.path.dirname(pathName)
        directoryName = iif(directoryName == "", ".", directoryName)
        Logging.trace("--: dir = %r", directoryName)
        cls.isValid(os.path.isdir(directoryName), message)

    #--------------------

    @classmethod
    def isValid (cls, condition, message):
        """Checks whether <condition> holds, otherwise exits program
           with <message>."""

        Logging.trace("--: checking condition (%s),"
                      + " otherwise failure is %r",
                      repr(condition), message)

        if not condition:
            message = "ERROR: " + message
            Logging.log(message)
            sys.exit(message)
