# validitychecker - allows checking of validity of values (typically
#                   of input parameters from the command line)
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import os
from simplelogging import Logging
import sys
from ttbase import iif

#====================

class ValidityChecker:
    """Provides checking of validity of values (typically command line
       parameters). Assumes that a check failure is fatal."""

    @classmethod
    def _checkTemplate (cls, typeName, valueName, value):
        result = "--: checking '%s' for being %s ('%s')"
        result = result % (valueName, typeName, value)
        return result
     
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
    def isBoolean (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           a boolean, otherwise exists program with a message."""

        Logging.trace(cls._checkTemplate("a boolean", valueName, value))
        message = "'%s' must be a boolean: %s" % (valueName, repr(value))
        cls.isValid(isinstance(value, bool), message)

    #--------------------

    @classmethod
    def isDirectory (cls, pathName, valueName=None):
        """Checks whether directory given by <pathName> is readable,
           otherwise exists program with a message."""

        Logging.trace(cls._checkTemplate("a directory", valueName, pathName))
        template = "Directory '%s'%s is not readable."
        message = cls._constructErrorMessage(template, pathName, valueName)
        cls.isValid(os.path.isdir(pathName), message)

    #--------------------

    @classmethod
    def isInteger (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           an integer or long integer, otherwise exists program with a
           message."""

        Logging.trace(cls._checkTemplate("an integer", valueName, value))
        message = "'%s' must be an integer: %s" % (valueName, repr(value))
        cls.isValid(isinstance(value, int) or isinstance(value, long), message)

    #--------------------

    @classmethod
    def isFloat (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           a float, otherwise exists program with a message."""

        Logging.trace(cls._checkTemplate("a float", valueName, value))
        message = "'%s' must be a float: %s" % (valueName, repr(value))
        cls.isValid(isinstance(value, float), message)

    #--------------------

    @classmethod
    def isNatural (cls, value, valueName, zeroIsIncluded=True):
        """Checks whether <value> of variable given by <valueName> is
           a positive integer or long integer, otherwise exists
           program with a message.  When <zeroIsIncluded> is set, also
           zero is acceptable."""

        typeName = "a " + iif(zeroIsIncluded, "", "positive ") + "natural"
        Logging.trace(cls._checkTemplate(typeName, valueName, value))
        message = ("'%s' must be %s: %s" % (valueName, typeName, repr(value)))
        cls.isValid((isinstance(value, int) or isinstance(value, long))
                    and (value > 0 or value == 0 and zeroIsIncluded),
                    message)

    #--------------------

    @classmethod
    def isReadableFile (cls, pathName, valueName=None):
        """Checks whether file given by <pathName> is readable,
           otherwise exists program with a message."""

        Logging.trace(cls._checkTemplate("a readableFile",
                                         valueName, pathName))
        template = "File '%s'%s is not readable."
        message = cls._constructErrorMessage(template, pathName, valueName)
        cls.isValid(os.path.isfile(pathName), message)

    #--------------------

    @classmethod
    def isString (cls, value, valueName):
        """Checks whether <value> of variable given by <valueName> is
           a unicode string, otherwise exists program with a message."""

        Logging.trace(cls._checkTemplate("a unicode string", valueName, value))
        message = "'%s' must be a string: %s" % (valueName, repr(value))
        cls.isValid(isinstance(value, unicode), message)

    #--------------------

    @classmethod
    def isWritableFile (cls, pathName, valueName=None):
        """Checks whether file given by <pathName> is writable,
           otherwise exists program with a message."""

        Logging.trace(cls._checkTemplate("a writable file",
                                         valueName, pathName))
        template = "File '%s'%s cannot be written."
        message = cls._constructErrorMessage(template, pathName, valueName)
        directoryName = os.path.dirname(pathName)
        cls.isValid(os.path.isdir(directoryName), message)

    #--------------------

    @classmethod
    def isValid (cls, condition, message):
        """Checks whether <condition> holds, otherwise exists program
           with <message>."""

        Logging.trace("--: checking condition (%s), otherwise failure is '%s'",
                      repr(condition), message)

        if not condition:
            Logging.log("ERROR: " + message)
            sys.exit(1)
