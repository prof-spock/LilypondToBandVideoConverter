# -*- coding: utf-8-unix -*-
# logging - provides primitive logging with logging levels
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import atexit
import codecs
import sys
from ttbase import iif

#====================

class Logging:
    """Provides some primitive logging."""

    Level_none     = 0
    Level_error    = 1
    Level_standard = 2
    Level_verbose  = 3
    
    _referenceLevel = Level_none
    _fileName       = ""
    _fileIsOpen     = None
    _file           = None

    # --------------------
    # LOCAL FEATURES
    # --------------------

    @classmethod
    def _callingFunctionName (cls):
        """Returns function name of calling function.  Some functions
        are filtered out (like those from UI) and the class name is
        prepended."""

        callerDepth = 1
        found = False

        while not found:
            currentFrame = sys._getframe(callerDepth)
            functionName = currentFrame.f_code.co_name
            found = (functionName not in ("log", "trace",
                                          "check", "pre", "post",
                                          "_internalCheck"))

            if not found:
                callerDepth = callerDepth + 1
            else:
                # check whether this is a method in a class using
                # python conventions
                localVariableList = currentFrame.f_locals
                hasSelfVariable   = ("self" in localVariableList)
                hasClsVariable    = ("cls" in localVariableList)

                if hasSelfVariable:
                    variable = localVariableList["self"]
                    className = variable.__class__.__name__
                elif hasClsVariable:
                    className = localVariableList["cls"].__name__
                else:
                    className = ""

                functionName = (className + iif(className > "", ".", "")
                                + functionName)

        return functionName

    #--------------------

    @classmethod
    def _closeFileConditionally (cls):
        if cls._fileIsOpen:
            cls._file.close()
        
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, referenceLevel, fileName=""):
        """Defines logging target file via <fileName> and also
           logging reference level."""

        cls._referenceLevel = referenceLevel
        cls._fileName       = fileName
        cls._fileIsOpen     = False
        atexit.register(cls._closeFileConditionally)

    #--------------------

    @classmethod
    def finalize (cls):
        """Ends logging."""

        cls._closeFileConditionally()

    #--------------------

    @classmethod
    def log (cls, st, level=Level_standard):
        """Writes <st> as a line to log file, when <level> is below or
           equal to the reference level."""

        st += '\n'

        if cls._referenceLevel >= level:
            # log message is significant 

            if cls._fileName == "":
                sys.stderr.write(st)
            else:
                if not cls._fileIsOpen:
                    cls._file = codecs.open(cls._fileName, "w", "utf-8",
                                            errors='replace')
                    cls._fileIsOpen = True
 
                cls._file.write(st)


    #--------------------

    @classmethod
    def trace (cls, template, *argumentList):
        """Writes <argumentList> formatted by <template> together with
           function name to log file."""

        functionName = cls._callingFunctionName()
        hasStandardPrefix = (template[0:2] in (">>", "<<", "--"))

        if not hasStandardPrefix:
            template = iif(len(template) > 0, "--:", "--") + template

        st = template[0:2] + functionName + template[2:] % argumentList
        cls.log(st, cls.Level_verbose)
