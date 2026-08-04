# progressmessage - provides a simple progress indication method
#                   with a lead-in message and a final duration indication
#
# author: Dr. Thomas Tensi
# version: 2025-07

#====================
# IMPORTS
#====================

import atexit
import time

from basemodules.operatingsystem import OperatingSystem
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, Natural, String
from basemodules.ttbase import iif

#====================

class ProgressMessage:
    """Encapsulates routines for progress messages on STDERR with a
       duration information"""

    # tells whether progress messages are immediately written to
    # output and non-leaf lines use brackets
    _usesImmediateMessaging = True

    # tells whether time data is displayed
    _timeDataIsDisplayed = True

    # the stack of start times
    _startTimeStack = []

    # the line list for buffering lines (when immediate output is not
    # done)
    _lineList = []

    # the stack of line indices values pointing into line list
    _lineIndexStack = []

    # the list of markers for each indentation level
    _markerList = "=-*o.,"

    # the stack of flags whether message has children or not
    _hasChildrenStack = []

    # the string used for opening a message scope
    _openScopeString = "["
    
    # the string used for closing a message scope
    _closeScopeString = "]"

    #--------------------
    # PRIVATE ROUTINES
    #--------------------

    @classmethod
    def _indentationForStackLevel (cls,
                                   level : Natural) -> String:
        """Returns indentation string for <level>"""

        return " " * (iif(level < 0, 0, level) * 4)

    #--------------------

    @classmethod
    def _reportProcessingEnd (cls,
                              loggingIsActive : Boolean):
        """Terminates current message by the elapsed time"""

        stackLevel = len(cls._startTimeStack)
        startTime = (0 if stackLevel == 0 else cls._startTimeStack.pop())
        endTime   = time.monotonic()
        duration  = endTime - startTime
        timeInformation = iif(cls._timeDataIsDisplayed,
                              " (%.2fs)" %  duration, "")

        if loggingIsActive:
            Logging.trace("--: stackLevel = %d,"
                          + " startTime = %f, endTime = %f,"
                          + " timeInformation = '%s'",
                          stackLevel, startTime, endTime,
                          timeInformation)

        if cls._usesImmediateMessaging:
            hasChildren = (False if len(cls._hasChildrenStack) == 0
                           else cls._hasChildrenStack.pop())

            if not hasChildren:
                line = timeInformation
            else:
                # write a closing bracket indented by level
                line = ("%s  %s %s"
                        % (cls._indentationForStackLevel(stackLevel - 1),
                           cls._closeScopeString, timeInformation))

            OperatingSystem.showMessageOnConsole(line, True)
        else:
            lineIndex = (None if len(cls._lineIndexStack) == 0
                         else cls._lineIndexStack.pop())

            if loggingIsActive:
                Logging.trace("--: lineIndex = %d", lineIndex)

            if lineIndex is not None:
                cls._lineList[lineIndex] += timeInformation

            if len(cls._startTimeStack) == 0:
                # we are done, write all lines to output
                for line in cls._lineList:
                    OperatingSystem.showMessageOnConsole(line, True)

                cls._lineList.clear()

    #--------------------
    # PUBLIC ROUTINES
    #--------------------

    @classmethod
    def initialize (cls,
                    usesImmediateMessaging : Boolean,
                    timeDataIsDisplayed : Boolean):
        """Sets up the progress messaging; <usesImmediateMessaging>
           tells whether progress messages are directly written to
           STDERR, <timeDataIsDisplayed> tells whether duration
           information is shown"""

        Logging.trace(">>: usesImmediateMessaging = %s,"
                      + " timeDataIsDisplayed = %s",
                      usesImmediateMessaging, timeDataIsDisplayed)

        cls._usesImmediateMessaging = usesImmediateMessaging
        cls._timeDataIsDisplayed    = timeDataIsDisplayed

        Logging.trace("<<")
    
    #--------------------

    @classmethod
    def flushBuffer (cls):
        """Flushes line buffer"""

        if not cls._usesImmediateMessaging:
            while len(cls._startTimeStack) > 0:
                cls._reportProcessingEnd(False)

    #--------------------

    @classmethod
    def reportProcessingEnd (cls):
        """Terminates current message by the elapsed time"""

        Logging.trace(">>")
        cls._reportProcessingEnd(True)
        Logging.trace("<<")

    #--------------------
    
    @classmethod
    def reportProcessingStart (cls,
                               message : String):
        """Issues <message> on STDERR about start of processing"""

        Logging.trace(">>: '%s'", message)

        stackLevel = len(cls._startTimeStack)
        Logging.trace("--: stackLevel = %d", stackLevel)
        cls._startTimeStack.append(time.monotonic())
        linePrefix = (cls._indentationForStackLevel(stackLevel)
                      + cls._markerList[stackLevel]
                      + " ")
        line = linePrefix + message

        if cls._usesImmediateMessaging:
            if stackLevel > 0 and not cls._hasChildrenStack[-1]:
                cls._hasChildrenStack[-1] = True
                lineSuffix = " " + cls._openScopeString
                OperatingSystem.showMessageOnConsole(lineSuffix, True)

            cls._hasChildrenStack.append(False)
            OperatingSystem.showMessageOnConsole(line, False)
        else:
            lineIndex  = len(cls._lineList)
            Logging.trace("--: lineIndex = %d", lineIndex)
            cls._lineIndexStack.append(lineIndex)
            cls._lineList.append(line)

        Logging.trace("<<")

#====================
        
atexit.register(ProgressMessage.flushBuffer)
