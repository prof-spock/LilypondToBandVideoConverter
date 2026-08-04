# -*- coding: utf-8 -*- 
# logging - provides primitive logging with logging levels
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import sys
import time

from basemodules.simpletypes import Boolean, Natural, String
from basemodules.ttbase import adaptToRange, iif, isMicroPython
from basemodules.typesupport import toUnicodeString

if not isMicroPython:
    import atexit
    import io
    import threading

#====================

class Logging_Level:
    """Defines the levels of logging"""

    # no logging
    noLogging           = 0
    # only logging of errors and assertion failures
    error               = 1
    # logging of errors and abbreviated exit-entry traces
    standardAbbreviated = 2
    # logging of errors and full exit-entry traces
    standard            = 3
    # full logging (including internal traces)
    verbose             = 4

    #--------------------

    @classmethod
    def fromString (cls,
                    st : String) -> String:
        """Converts string <st> to log level, returns noLogging when
           string cannot be converted"""

        result = cls.noLogging
        st = st.lower()
           
        if st == "verbose":
            result = cls.verbose
        elif st == "standard":
            result = cls.standard
        elif st == "standardabbreviated":
            result = cls.standardAbbreviated
        elif st == "error":
            result = cls.error
        else:
            result = cls.noLogging
       
        return result
    
    #--------------------

    @classmethod
    def toString (cls,
                  level : Natural) -> String:
        """Converts <level> to string"""

        if level == cls.verbose:
            result = "verbose"
        elif level == cls.standard:
            result = "standard"
        elif level == cls.standardAbbreviated:
            result = "standardAbbreviated"
        elif level == cls.error:
            result = "error"
        else:
            result = "noLogging"

        return result
        
#====================

class Logging:
    """Provides some primitive logging."""

   
    _referenceLevel             = Logging_Level.noLogging
    _fileName                   = ""
    _fileIsOpen                 = None
    _fileIsKeptOpen             = None
    _file                       = None
    _isActive                   = True
    _timeIsLogged               = True
    _timeFactor                 = 1
    _timeFractionalPartTemplate = ""
    _timeFractionalDigitCount   = 0
    _previousTimestamp          = 0
    _timeOfDayString            = ""
    _threadIDIsLogged           = False

    # buffer logs data before log file is opened, otherwise a
    # write-through will be done
    _buffer = []

    # the list of function names to be ignored when traversing
    # run-time stack for relevant function names */
    _ignoredFunctionNameList = \
        ("check", "_internalCheck", "log", "post", "pre",
         "trace", "traceError", "_traceWithLevel")

    #-- TRACE PREFICES --
    # length of allowed prefixes for template in a trace call
    _tracePrefixLength = 2

    # trace prefix used for internal traces within a function
    _innerTracePrefix = "--"

    # list of allowed prefixes for template in a entry-exit trace
    # call
    _entryExitPrefixList = (">>", "<<")
  
    # list of allowed prefixes for template in a trace call
    _standardPrefixList = _entryExitPrefixList + (_innerTracePrefix,)

    # --------------------
    # LOCAL FEATURES
    # --------------------

    @classmethod
    def _callingFunctionName (cls) -> String:
        """Returns function name of calling function.  Some functions
        are filtered out (like those from UI) and the class name is
        prepended."""

        if isMicroPython:
            return "..."
        else:
            callerDepth = 1
            found = False

            while not found:
                currentFrame = sys._getframe(callerDepth)
                codeObject = currentFrame.f_code
                functionName = codeObject.co_name
                found = (functionName not in cls._ignoredFunctionNameList)

                if not found:
                    callerDepth = callerDepth + 1
                else:
                    functionName = codeObject.co_qualname

        return functionName

    #--------------------

    @classmethod
    def _closeFileConditionally (cls):
        if cls._fileIsOpen:
            cls._file.close()
            cls._fileIsOpen = False
        
    #--------------------

    @classmethod
    def _currentTimeOfDay (cls) -> String:
        """Returns current time of day in seconds as string"""

        currentTimestamp = time.time()
        
        if currentTimestamp != cls._previousTimestamp:
            cls._previousTimestamp = currentTimestamp

            if not isMicroPython:
                st = time.strftime("%H%M%S")
            else:
                _, _, _, hours, minutes, seconds, _, _ = time.localtime()
                st = "%02d%02d%02d" % (hours, minutes, seconds)

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
        elif cls._fileName.lower() == "stderr":
            cls._file = sys.stderr
        else:
            mode = iif(isNew, "wt", "at")
            cls._file = io.open(cls._fileName, mode,
                                encoding="utf-8", errors='replace')

        cls._fileIsOpen = (cls._file is not None)
  
    #--------------------

    @classmethod
    def _prefixBefore (cls, st, otherSt):
        """Returns part of <st> before <otherSt>; if <otherSt> is not
           in string, the whole string will be returned"""

        splitPosition = st.indexOf(otherSt)
        result = st if splitPosition is None else st[0:splitPosition]
        return result
        
    #--------------------

    @classmethod
    def _traceWithLevel (cls,
                         level : Natural,
                         template : String,
                         *argumentList):
        """Writes <argumentList> formatted by <template> together with
           function name to log file."""

        if cls._isActive and level <= cls._referenceLevel:
            functionName = cls._callingFunctionName()
            prefixLength = cls._tracePrefixLength

            if template[0:prefixLength] not in cls._standardPrefixList:
                template = (cls._innerTracePrefix
                            + iif(len(template) > 0, ":", "")
                            + template)

            if cls._threadIDIsLogged:
                threadID = threading.current_thread().ident
                threadIDString = " [%d]" % threadID
            else:
                threadIDString = ""
                
            if cls._timeIsLogged:
                timeString = " (" + cls._currentTimeOfDay() + ")"
            else:
                timeString = ""

            st = (template[0:prefixLength]
                  + functionName
                  + timeString
                  + threadIDString)
            template = template[prefixLength:]

            # workaround for JYTHON or for mismatch in template and
            # argument list
            try:
                st += template % argumentList
            except:
                st += template + " ###CONVERSION ERROR###"

            if (cls._referenceLevel == Logging_Level.standardAbbreviated
                and st[0:prefixLength] in cls._standardPrefixList):
                # this is the level where the entry-exit data after
                # and including the colon is stripped off
                st = cls._prefixBefore(st, ":")
            
            cls._writeLine(st)

    #--------------------

    @classmethod
    def _writeLine (cls,
                    st : String):
        """Reopens logging file and writes single line <st>"""

        if isMicroPython:
            print(st)
        else:
            for pattern in ("\r\n", "\n", "\r"):
                st = st.replace(pattern, "<BR/>")

            st += '\n'

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

        cls._referenceLevel = Logging_Level.noLogging
        cls._fileName       = ""
        cls._fileIsOpen     = False
        cls._isActive       = True
        cls._buffer.clear()

        header = "START LOGGING -*- coding:utf-8 -*-"
        cls._writeLine(header)

        if not isMicroPython:
            atexit.register(cls._closeFileConditionally)
    
    #--------------------

    @classmethod
    def finalize (cls):
        """Ends logging."""

        footer = "END LOGGING"
        cls._writeLine(footer)

        if not isMicroPython:
            cls._closeFileConditionally()

    #--------------------
    #--------------------

    @classmethod
    def setEnabled (cls,
                    isEnabled : Boolean):
        """Sets logging to active or inactive"""

        cls._isActive = isEnabled

    #--------------------

    @classmethod
    def setLevel (cls,
                  loggingLevel : Logging_Level):
        """Sets logging reference level to <loggingLevel>"""

        cls._referenceLevel = loggingLevel

    #--------------------

    @classmethod
    def setFileName (cls,
                     fileName : String,
                     isKeptOpen : Boolean = True):
        """Sets file name for logging to <fileName>; if <isKeptOpen>
           is set, the logging file is not closed after each log entry"""

        if isMicroPython:
            cls._fileName = ""
        elif cls._fileName == fileName:
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
    def setTracingOfThreadID (cls,
                              threadIDIsLogged : Boolean):
        """Sets logging of threads to active or inactive depending on
           <threadIDIsLogged>"""

        Logging.trace(">>: %s", threadIDIsLogged)

        if isMicroPython:
            Logging.trace("--: multiprocessing not supported in MicroPython")
        else:
            cls._threadIDIsLogged = threadIDIsLogged

        Logging.trace("<<")

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
             level : Natural = Logging_Level.standard):
        """Writes <st> as a line to log file, when <level> is below or
           equal to the reference level."""

        if cls._referenceLevel >= level and cls._isActive:
            # log message is significant 
            cls._writeLine(st)

    #--------------------

    @classmethod
    def trace (cls,
               template : String,
               *argumentList):
        """Writes <argumentList> formatted by <template> together with
           function name to log file."""

        templatePrefix = template[0:cls._tracePrefixLength]
        isEntryExitTrace = templatePrefix in cls._entryExitPrefixList
        logLevel = iif(isEntryExitTrace,
                       Logging_Level.standardAbbreviated,
                       Logging_Level.verbose)
        cls._traceWithLevel(logLevel, template, *argumentList)

    #--------------------

    @classmethod
    def traceError (cls,
                    template : String,
                    *argumentList):
        """Writes <argumentList> formatted by <template> together with
           function name to log file as an error entry."""

        cls._traceWithLevel(Logging_Level.error,
                            "--: ERROR - " + template,
                            *argumentList)
