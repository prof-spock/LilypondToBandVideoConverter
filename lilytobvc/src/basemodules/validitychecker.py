# validitychecker - allows checking of validity of values (typically
#                   of input parameters from the command line)
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import os
import re
import subprocess
import sys

import basemodules.typesupport as typesupport
from .operatingsystem import OperatingSystem
from .simplelogging import Logging
from .simpletypes import Boolean, Object, String
from .ttbase import iif, iif2

#====================

class ValidityChecker:
    """Provides checking of validity of values (typically command line
       parameters). Assumes that a check failure is fatal."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _rangeKindToTemplateMap = {
        ""     : "%s",
        ">0"   : "a positive %s",
        ">=0"  : "a non-negative %s"
    }

    #--------------------

    @classmethod
    def _checkTemplate (cls,
                        typeName : String,
                        valueName : String,
                        value : Object):
        result = "--: checking %s for being %s (%r)"
        result = result % (valueName, typeName, value)
        return result

    #--------------------

    @classmethod
    def _checkForType (cls,
                       kind : String,
                       kindName : String,
                       valueName : String,
                       value : Object):
        Logging.trace(cls._checkTemplate(kindName, valueName, value))
        message = "%s must be %s: %r" % (valueName, kindName, value)
        cls.isValid(isinstance(value, kind), message)

    #--------------------

    @classmethod
    def _constructErrorMessage (cls,
                                template : String,
                                value : Object,
                                valueName : String) -> String:
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
    def isOfKind (cls,
                  value : Object,
                  valueName : String,
                  kind : String):
        """Checks whether <value> named <valueName> has <kind>; otherwise
           exits program with an appropriate message"""

        Logging.trace(">>: value = %r, valueName = %s, kind = %r",
                      value, valueName, kind)

        if kind in _kindToCheckProcMap:
            _kindToCheckProcMap[kind](value, valueName)

        Logging.trace("<<")
    
    #--------------------

    @classmethod
    def isBoolean (cls,
                   value : Object,
                   valueName : String):
        """Checks whether <value> of variable given by <valueName> is
           a boolean, otherwise exits program with a message."""

        cls._checkForType(bool, "a boolean", valueName, value)

    #--------------------

    @classmethod
    def isBooleanString (cls,
                         value : String,
                         valueName : String):
        """Checks whether <value> of variable given by <valueName> is
           a boolean string, otherwise exits program with a message."""

        value = str(value)
        isOkay = value.lower() in ["true", "false"]
        message = "%s must be a boolean string: %r" % (valueName, value)
        cls.isValid(isOkay, message)

    #--------------------

    @classmethod
    def isDirectory (cls,
                     pathName : String,
                     valueName : String = None):
        """Checks whether directory given by <pathName> is readable,
           otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a directory", valueName, pathName))
        template = "Directory %r (%s) is not readable."
        message = cls._constructErrorMessage(template, pathName, valueName)
        cls.isValid(os.path.isdir(pathName), message)

    #--------------------

    @classmethod
    def isExecutableCommand (cls,
                             commandName : String,
                             valueName : String = None):
        """Checks whether executable given by <commandName> can be executed,
           otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("an executable command",
                                         valueName, commandName))
        template = "Command %r (%s) cannot be executed."
        message = cls._constructErrorMessage(template, commandName, valueName)
        try:
            subprocess.run(commandName,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            isOkay = True
        except:
            isOkay = False

        cls.isValid(isOkay, message)

    #--------------------

    @classmethod
    def isInteger (cls,
                   value : String,
                   valueName : String):
        """Checks whether <value> of variable given by <valueName> is
           an integer or long integer, otherwise exits program with a
           message."""

        Logging.trace(cls._checkTemplate("an integer", valueName, value))
        message = "%s must be an integer: %r" % (valueName, value)
        cls.isValid(typesupport.isInteger(value), message)

    #--------------------

    @classmethod
    def isList (cls,
                value : String,
                valueName : String):
        """Checks whether <value> of variable given by <valueName> is
           a list, otherwise exits program with a message."""

        cls._checkForType(list, "a list", valueName, value)

    #--------------------

    @classmethod
    def isMap (cls,
               value : String,
               valueName : String):
        """Checks whether <value> of variable given by <valueName> is
           a map, otherwise exits program with a message."""

        cls._checkForType(dict, "a map", valueName, value)

    #--------------------

    @classmethod
    def isNatural (cls,
                   value : String,
                   valueName : String,
                   zeroIsIncluded : Boolean = True):
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
    def isNumberString (cls,
                        value : String,
                        valueName : String,
                        realIsAllowed : Boolean,
                        rangeKind : String = ""):
        """Checks whether string <value> with name <valueName> is
           representation of a correct number. <realIsAllowed> tells
           whether non-integer values are okay, <rangeKind> gives an
           boundary condition about the range."""

        Logging.trace(">>: %s = %r (%s), realIsOk = %r, rangeKind = %r",
                      valueName, value, type(value), realIsAllowed, rangeKind)

        realRegexp   = re.compile(r"^\-?[0-9]+(\.[0-9]*)?$")
        integerRegexp = re.compile(r"^\-?[0-9]+$")

        value = str(value)
        isOkay = (integerRegexp.match(value) is not None)

        if rangeKind not in ("", ">0", ">=0"):
            rangeKind = ""

        if realIsAllowed and not isOkay:
            isOkay = (realRegexp.match(value) is not None)

        if isOkay:
            isOkay = iif2(rangeKind == ">0",  (float(value) > 0),
                          rangeKind == ">=0", (float(value) >= 0),
                          True)

        typeDesignation = (cls._rangeKindToTemplateMap[rangeKind]
                           % iif(realIsAllowed, "real", "integer"))
        errorTemplate = "%s must be " + typeDesignation + " - %r"
        cls.isValid(isOkay, errorTemplate % (valueName, value))

        Logging.trace("<<: %r", isOkay)

    #--------------------

    @classmethod
    def isReadableFile (cls,
                        pathName : String,
                        valueName : String = None):
        """Checks whether file given by <pathName> is readable,
           otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a readableFile",
                                         valueName, pathName))
        template = "File %r (%s) is not readable."
        message = cls._constructErrorMessage(template, pathName, valueName)
        cls.isValid(os.path.isfile(pathName), message)

    #--------------------

    @classmethod
    def isReal (cls,
                value : String,
                valueName : String):
        """Checks whether <value> of variable given by <valueName> is a real
           number, otherwise exits program with a message."""

        cls._checkForType(float, "a real number", valueName, value)

    #--------------------

    @classmethod
    def isString (cls,
                  value : String,
                  valueName : String):
        """Checks whether <value> of variable given by <valueName> is
           a unicode string, otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a (unicode) string",
                                         valueName, value))
        message = "%s must be a string: %r" % (valueName, value)
        cls.isValid(typesupport.isString(value), message)

    #--------------------

    @classmethod
    def isStringList (cls,
                      value : String,
                      valueName : String):
        """Checks whether <value> of variable given by <valueName> is a
           (unicode) string list, otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a (unicode) string list",
                                         valueName, value))
        message = "%s must be a string list: %r" % (valueName, value)
        cls.isValid(typesupport.isStringList(value), message)

    #--------------------

    @classmethod
    def isStringMap (cls,
                     value : String,
                     valueName : String):
        """Checks whether <value> of variable given by <valueName> is a
           map from (unicode) strings to other objects, otherwise exits
           program with a message."""

        Logging.trace(cls._checkTemplate("a (unicode) string map",
                                         valueName, value))
        message = "%s must be a string map: %r" % (valueName, value)
        cls.isValid(typesupport.isStringMap(value), message)

    #--------------------

    @classmethod
    def isWritableFile (cls,
                        pathName : String,
                        valueName : String = None):
        """Checks whether file given by <pathName> is writable,
           otherwise exits program with a message."""

        Logging.trace(cls._checkTemplate("a writable file",
                                         valueName, pathName))
        template = "File %r (%s) cannot be written."
        message = cls._constructErrorMessage(template, pathName, valueName)
        directoryName = ("???" if pathName is None
                         else OperatingSystem.dirname(pathName))
        directoryName = iif(directoryName == "", ".", directoryName)
        Logging.trace("--: dir = %r", directoryName)
        cls.isValid(os.path.isdir(directoryName), message)

    #--------------------

    @classmethod
    def isValid (cls,
                 condition : Boolean,
                 message : String):
        """Checks whether <condition> holds, otherwise exits program
           with <message>."""

        Logging.trace("--: checking condition (%r),"
                      + " otherwise failure is %r",
                      condition, message)

        if not condition:
            message = "ERROR: " + message
            Logging.log(message)
            sys.exit(message)

#--------------------

_kindToCheckProcMap = {
    "B"  : ValidityChecker.isBoolean,
    "EX" : ValidityChecker.isExecutableCommand,
    "I"  : ValidityChecker.isInteger,
    "N"  : ValidityChecker.isInteger,
    "PN" : ValidityChecker.isInteger,
    "R"  : ValidityChecker.isReal,
    "RF" : ValidityChecker.isReadableFile,
    "S"  : ValidityChecker.isString,
    "SL" : ValidityChecker.isStringList,
    "SM" : ValidityChecker.isStringMap,
    "WD" : ValidityChecker.isDirectory,
    "WF" : ValidityChecker.isWritableFile
}
