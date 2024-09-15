# validitychecker - allows checking of validity of values (typically
#                   of input parameters from the command line)
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import os
import re
import sys

import basemodules.typesupport as typesupport
from basemodules.operatingsystem import OperatingSystem
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, Object, String
from basemodules.ttbase import iif, iif2, isStdPython

if isStdPython:
    import subprocess

#====================

class ValidityChecker:
    """Provides checking of validity of values (typically command line
       parameters). Typically assumes that a check failure is fatal."""

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
                        prefix : String,
                        typeName : String,
                        valueName : String,
                        value : Object,
                        failureCausesExit : Boolean):
        result = (prefix + ": checking %s for being %s (%r) "
                  + iif(failureCausesExit, "with", "without")
                  + " failure on exit")
        result = result % (valueName, typeName, value)
        # remove any template characters in result string
        result = result.replace("%", "§")
        return result

    #--------------------

    @classmethod
    def _checkForType (cls,
                       kind : String,
                       kindName : String,
                       valueName : String,
                       value : Object,
                       failureCausesExit : Boolean = True) -> Boolean:
        Logging.trace(cls._checkTemplate(">>", kindName, valueName, value,
                                         failureCausesExit))

        message = "%s must be %s: %r" % (valueName, kindName, value)
        isOkay = isinstance(value, kind)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

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
            result = template % (value, valueName)

        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def isOfKind (cls,
                  value : Object,
                  valueName : String,
                  kind : String,
                  failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> named <valueName> has <kind>;
           otherwise gives <message> and exits program when
           <failureCausesExit> is set"""

        Logging.trace(">>: value = %r, valueName = %s, kind = %r,"
                      + " failureCausesExit = %s",
                      value, valueName, kind, failureCausesExit)

        if kind not in _kindToCheckProcMap:
            isOkay = False
        else:
            isOkay = _kindToCheckProcMap[kind](value, valueName,
                                               failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay
    
    #--------------------

    @classmethod
    def isBoolean (cls,
                   value : Object,
                   valueName : String,
                   failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           a boolean, otherwise gives <message> and exits program when
           <failureCausesExit> is set."""

        Logging.trace(">>: value = %r, valueName = %s,"
                      + " failureCausesExit = %s",
                      value, valueName, failureCausesExit)

        isOkay = cls._checkForType(bool, "a boolean", valueName, value,
                                   failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isBooleanString (cls,
                         value : String,
                         valueName : String,
                         failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           a boolean string, otherwise gives <message> and exits
           program when <failureCausesExit> is set."""

        Logging.trace(">>: value = %r, valueName = %s,"
                      + " failureCausesExit = %s",
                      value, valueName, failureCausesExit)

        value = str(value)
        isOkay = value.lower() in ["true", "false"]
        message = "%s must be a boolean string: %r" % (valueName, value)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isDirectory (cls,
                     pathName : String,
                     valueName : String = None,
                     failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether directory given by <pathName> is readable,
           otherwise gives <message> and exits program when
           <failureCausesExit> is set."""

        Logging.trace(cls._checkTemplate(">>", "a directory", valueName,
                                         pathName, failureCausesExit))

        template = "Directory %r (%s) is not readable."
        message = cls._constructErrorMessage(template, pathName, valueName)
        isOkay = os.path.isdir(pathName)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isExecutableCommand (cls,
                             commandName : String,
                             valueName : String = None,
                             failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether executable given by <commandName> can be
           executed, otherwise gives <message> and exits program when
           <failureCausesExit> is set."""

        Logging.trace(cls._checkTemplate(">>", "an executable command",
                                         valueName, commandName,
                                         failureCausesExit))

        template = "Command %r (%s) cannot be executed."
        message = cls._constructErrorMessage(template, commandName,
                                             valueName)

        if not isStdPython:
            isOkay = False
        else:
            try:
                subprocess.run(commandName,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                isOkay = True
            except:
                isOkay = False

            if not isOkay:
                try:
                    subprocess.call(commandName)
                    isOkay = True
                except:
                    pass

        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isInteger (cls,
                   value : String,
                   valueName : String,
                   failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           an integer or long integer, otherwise exits program with a
           message."""

        Logging.trace(cls._checkTemplate(">>", "an integer", valueName,
                                         value, failureCausesExit))

        message = "%s must be an integer: %r" % (valueName, value)
        isOkay = typesupport.isInteger(value)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isList (cls,
                value : String,
                valueName : String,
                failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           a list, otherwise gives <message> and exits program when
           <failureCausesExit> is set."""

        Logging.trace(">>: value = %r, valueName = %s,"
                      + " failureCausesExit = %s",
                      value, valueName, failureCausesExit)

        isOkay = cls._checkForType(list, "a list", valueName, value,
                                   failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isMap (cls,
               value : String,
               valueName : String,
               failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           a map, otherwise gives <message> and exits program when
           <failureCausesExit> is set."""

        Logging.trace(">>: value = %r, valueName = %s,"
                      + " failureCausesExit = %s",
                      value, valueName, failureCausesExit)

        isOkay = cls._checkForType(dict, "a map", valueName, value,
                                   failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isNatural (cls,
                   value : String,
                   valueName : String,
                   zeroIsIncluded : Boolean = True,
                   failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           a positive integer or long integer, otherwise gives
           <message> and exits program when <failureCausesExit> is
           set.  When <zeroIsIncluded> is set, also zero is
           acceptable."""

        kindName = "a " + iif(zeroIsIncluded, "", "positive ") + "natural"
        Logging.trace(cls._checkTemplate(">>", kindName, valueName,
                                         value, failureCausesExit))
        message = ("%s must be %s: %r" % (valueName, kindName, value))
        isOkay = (typesupport.isInteger(value)
                  and (value > 0 or value == 0 and zeroIsIncluded))
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isNumberString (cls,
                        value : String,
                        valueName : String,
                        realIsAllowed : Boolean,
                        rangeKind : String = "",
                        failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether string <value> with name <valueName> is
           representation of a correct number. <realIsAllowed> tells
           whether non-integer values are okay, <rangeKind> gives an
           boundary condition about the range."""

        Logging.trace(">>: %s = %r (%s), realIsOk = %r, rangeKind = %r,"
                      + " failureCausesExit = %s",
                      valueName, value, type(value), realIsAllowed,
                      rangeKind, failureCausesExit)

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
        cls.isValid(isOkay, errorTemplate % (valueName, value),
                    failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isReadableFile (cls,
                        pathName : String,
                        valueName : String = None,
                        failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether file given by <pathName> is readable,
           otherwise gives <message> and exits program when
           <failureCausesExit> is set."""

        Logging.trace(cls._checkTemplate(">>", "a readableFile",
                                         valueName, pathName,
                                         failureCausesExit))
        template = "File %r (%s) is not readable."
        message = cls._constructErrorMessage(template, pathName, valueName)
        isOkay = False if pathName is None else os.path.isfile(pathName)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isReal (cls,
                value : String,
                valueName : String,
                failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           a real number, otherwise gives <message> and exits program
           when <failureCausesExit> is set."""

        Logging.trace(">>: value = %r, valueName = %s,"
                      + " failureCausesExit = %s",
                      value, valueName, failureCausesExit)

        isOkay = cls._checkForType(float, "a real number", valueName,
                                   value, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isString (cls,
                  value : String,
                  valueName : String,
                  failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           a unicode string, otherwise gives <message> and exits
           program when <failureCausesExit> is set."""

        Logging.trace(cls._checkTemplate(">>", "a (unicode) string",
                                         valueName, value,
                                         failureCausesExit))

        message = "%s must be a string: %r" % (valueName, value)
        isOkay = typesupport.isString(value)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isStringList (cls,
                      value : String,
                      valueName : String,
                      failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is
           a (unicode) string list, otherwise gives <message> and
           exits program when <failureCausesExit> is set."""

        Logging.trace(cls._checkTemplate(">>", "a (unicode) string list",
                                         valueName, value,
                                         failureCausesExit))

        message = "%s must be a string list: %r" % (valueName, value)
        isOkay = typesupport.isStringList(value)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isStringMap (cls,
                     value : String,
                     valueName : String,
                     failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether <value> of variable given by <valueName> is a
           map from (unicode) strings to other objects, otherwise exits
           program with a message."""

        Logging.trace(cls._checkTemplate(">>", "a (unicode) string map",
                                         valueName, value,
                                         failureCausesExit))
        message = "%s must be a string map: %r" % (valueName, value)
        isOkay = typesupport.isStringMap(value)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isWritableFile (cls,
                        pathName : String,
                        valueName : String = None,
                        failureCausesExit : Boolean = True) -> Boolean:
        """Checks whether file given by <pathName> is writable,
           otherwise gives <message> and exits program when
           <failureCausesExit> is set."""

        Logging.trace(cls._checkTemplate(">>", "a writable file",
                                         valueName, pathName,
                                         failureCausesExit))

        template = "File %r (%s) cannot be written."
        message = cls._constructErrorMessage(template, pathName, valueName)
        directoryName = ("???" if pathName is None
                         else OperatingSystem.dirname(pathName))
        directoryName = iif(directoryName == "", ".", directoryName)
        Logging.trace("--: dir = %r", directoryName)
        isOkay = os.path.isdir(directoryName)
        cls.isValid(isOkay, message, failureCausesExit)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def isValid (cls,
                 condition : Boolean,
                 message : String,
                 failureCausesExit : Boolean = True):
        """Checks whether <condition> holds, otherwise gives <message>
           and exits program when <failureCausesExit> is set."""

        Logging.trace("--: checking condition (%r),"
                      + " otherwise failure is %r",
                      condition, message)

        if not condition:
            Logging.traceError(message)

            if failureCausesExit:
                sys.exit("ERROR: " + message)

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
