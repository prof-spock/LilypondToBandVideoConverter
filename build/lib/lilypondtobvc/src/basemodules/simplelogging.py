# logging - provides primitive logging with logging levels
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import atexit
import io
import sys
import time

from .simpletypes import Boolean, Natural, String
from .ttbase import adaptToRange, iif
from .typesupport import toUnicodeString

#====================

class Logging:
    """Provides some primitive logging."""

    Level_none     = 0
    Level_error    = 1
    Level_standard = 2
    Level_verbose  = 3
    
    _referenceLevel             = Level_none
    _fileName                   = ""
    _fileIsOpen                 = None
    _fileIsKeptOpen             = None
    _file                       = None
    _isEnabled                  = True
    _timeIsLogged               = True
    _timeFactor                 = 1
    _timeFractionalPartTemplate = ""
    _timeFractionalDigitCount   = 0
    _previousTimestamp          = 0
    _timeOfDayString            = ""

    _buffer = []
    # buffers log data before log file is opened, otherwise a
    # write-through will be done

    # --------------------
    # LOCAL FEATURES
    # --------------------

    @classmethod
    def _callingFunctionName (cls) -> String:
        """Returns function name of calling function.  Some functions
        are filtered out (like those from UI) and the class name is
        prepended."""

        callerDepth = 1
        found = False

        while not found:
            currentFrame = sys._getframe(callerDepth)
            functionName = currentFrame.f_code.co_name
            found = (functionName not in ("log", "trace", "traceError",
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

    @classmethod
    def _currentTimeOfDay (cls) -> String:
        """Returns current time of day in seconds as string"""

        currentTimestamp = time.time()
        
        if currentTimestamp != cls._previousTimestamp:
            cls._previousTimestamp = currentTimestamp
            st = time.strftime("%H%M%S")

            if cls._timeFractionalDigitCount > 0:
                fractionalPart = currentTimestamp - int(currentTimestamp)
                fractionalPart *= cls._timeFactor
                st += cls._timeFractionalPartTemplate % fractionalPart
                
            cls._timeOfDayString = st

        return cls._timeOfDayString
        
    #--------------------

    @classmethod
    def _openOrCreateFile (cls,
                           isNew : Boolean):
        """Creates or reopens logging file depending on value of
           <isNew>"""

        if cls._fileName == "":
            cls._file = None
        elif cls._fileName == "STDERR":
            cls._file = sys.stderr
        else:
            mode = iif(isNew, "wt", "at")
            cls._file = io.open(cls._fileName, mode,
                                encoding="utf-8", errors='replace')

        cls._fileIsOpen = (cls._file is not None)
  
    #--------------------

    @classmethod
    def _writeLine (cls,
                    st : String):
        """Reopens logging file and writes single line <st>"""

        st = st + '\n'

        if cls._fileName == "":
            # no output file => put line to buffer
            cls._buffer.append(st)
        else:
            if not cls._fileIsKeptOpen:
                cls._openOrCreateFile(False)

            if cls._file is None:
                # output file cannot be accessed => put line to buffer
                cls._buffer.append(st)
            else:
                cls._writeStringDirectly(st)

            if not cls._fileIsKeptOpen:
                cls._file.close()

    #--------------------

    @classmethod
    def _writeStringDirectly (cls,
                              st : String):
        """Writes <st> to logging file"""

        st = toUnicodeString(st)
        cls._file.write(st)

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls):
        """Starts logging"""

        cls._referenceLevel = cls.Level_none
        cls._fileName       = ""
        cls._fileIsOpen     = False
        cls._isEnabled      = True
        cls._buffer.clear()

        header = "START LOGGING -*- coding:utf-8 -*-"
        cls._writeLine(header)
        atexit.register(cls._closeFileConditionally)
    
    #--------------------

    @classmethod
    def finalize (cls):
        """Ends logging."""

        footer = "END LOGGING"
        cls._writeLine(footer)
        cls._closeFileConditionally()

    #--------------------
    #--------------------

    @classmethod
    def setEnabled (cls,
                    isEnabled : Boolean):
        """Sets logging to active or inactive"""

        cls._isEnabled = isEnabled

    #--------------------

    @classmethod
    def setLevel (cls,
                  loggingLevel : Natural):
        """Sets logging reference level to <loggingLevel>"""

        cls._referenceLevel = loggingLevel

    #--------------------

    @classmethod
    def setFileName (cls,
                     fileName : String,
                     isKeptOpen : Boolean = True):
        """Sets file name for logging to <fileName>; if <isKeptOpen>
           is set, the logging file is not closed after each log entry"""

        if cls._fileName == fileName:
            cls._writeLine("logging file %s already open => skip"
                           % fileName)
        else:
            cls._fileName       = fileName
            cls._fileIsKeptOpen = isKeptOpen
            cls._openOrCreateFile(True)

            if cls._file is None:
                cls._fileName = ""
            else:
                for line in cls._buffer:
                    cls._writeStringDirectly(line)

                cls._buffer.clear()

            if not cls._fileIsKeptOpen:
                cls._file.close()

    #--------------------

    @classmethod
    def setTracingWithTime (cls,
                            timeIsLogged : Boolean,
                            fractionalDigitCount : Natural = 0):
        """Sets logging of time when tracing to active or inactive;
           <fractionalDigitCount> gives the number of fractional
           digits for the time logged"""

        fractionalDigitCount = adaptToRange(fractionalDigitCount, 0, 3)

        cls._timeIsLogged               = timeIsLogged
        cls._timeFractionalDigitCount   = fractionalDigitCount
        cls._timeFactor                 = 10 ** fractionalDigitCount
        cls._timeFractionalPartTemplate = \
            ".%0" + "%1d" % fractionalDigitCount + "d"

    #--------------------

    @classmethod
    def log (cls,
             st : String,
             level : Natural = Level_standard):
        """Writes <st> as a line to log file, when <level> is below or
           equal to the reference level."""

        if cls._referenceLevel >= level and cls._isEnabled:
            # log message is significant 
            cls._writeLine(st)

    #--------------------

    @classmethod
    def trace (cls,
               template : String,
               *argumentList):
        """Writes <argumentList> formatted by <template> together with
           function name to log file."""

        if cls._isEnabled:
            functionName = cls._callingFunctionName()
            hasStandardPrefix = (template[0:2] in (">>", "<<", "--"))

            if not hasStandardPrefix:
                template = (iif(len(template) > 0, "--:", "--")
                            + template)

            if cls._timeIsLogged:
                timeString = " (" + cls._currentTimeOfDay() + ")"
            else:
                timeString = ""

            st = template[0:2] + functionName + timeString
            template = template[2:]

            # workaround for JYTHON
            try:
                st += template % argumentList
            except:
                st += template + " ###JYTHON CONVERSION ERROR###"

            st = st.replace("\n", "#")
            cls.log(st, cls.Level_verbose)

    #--------------------

    @classmethod
    def traceError (cls,
                    template : String,
                    *argumentList):
        """Writes <argumentList> formatted by <template> together with
           function name to log file as an error entry."""

        cls.trace("--: ERROR - " + template, *argumentList)
