# logging - provides primitive logging with logging levels
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import atexit
import io
import sys

from basemodules.python2and3support import isPython2
from basemodules.ttbase import iif

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
    _fileIsKeptOpen = None
    _file           = None
    _isEnabled      = True

    _buffer = []
    # buffers log data before log file is opened, otherwise a
    # write-through will be done

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

    @classmethod
    def _openOrCreateFile (cls, isNew):
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
    def _writeLine (cls, st):
        """Reopens logging file and writes single line <st>"""

        if cls._isEnabled:
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
    def _writeStringDirectly (cls, st):
        """Writes <st> to logging file"""

        if isPython2:
            st = unicode(st)
            
        cls._file.write(st)

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls):
        """Starts logging"""

        cls._writeLine("START LOGGING")
        atexit.register(cls._closeFileConditionally)
    
    #--------------------

    @classmethod
    def setEnabled (cls, isEnabled):
        """Sets logging to active or inactive"""

        cls._isEnabled = isEnabled

    #--------------------

    @classmethod
    def setLevel (cls, loggingLevel):
        """Sets logging reference level to <loggingLevel>"""

        cls._referenceLevel = loggingLevel

    #--------------------

    @classmethod
    def setFileName (cls, fileName, isKeptOpen=True):
        """Sets file name for logging to <fileName>; if <isKeptOpen>
           is set, the logging file is not closed after each log entry"""

        if cls._fileName == fileName:
            cls._writeLine("logging file %s already open => skip" % fileName)
        else:
            cls._fileName       = fileName
            cls._fileIsKeptOpen = isKeptOpen
            cls._openOrCreateFile(True)

            if cls._file is None:
                cls._fileName = ""
            else:
                for line in cls._buffer:
                    cls._writeStringDirectly(line)

                cls._buffer = []

            if not cls._fileIsKeptOpen:
                cls._file.close()

    #--------------------

    @classmethod
    def finalize (cls):
        """Ends logging."""

        cls._writeLine("END LOGGING")
        cls._closeFileConditionally()

    #--------------------

    @classmethod
    def log (cls, st, level=Level_standard):
        """Writes <st> as a line to log file, when <level> is below or
           equal to the reference level."""

        if cls._referenceLevel >= level:
            # log message is significant 
            cls._writeLine(st)

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