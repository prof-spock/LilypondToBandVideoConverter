# operatingsystem -- provides simple facilities for access of operating
#                    system services
#
# author: Dr. Thomas Tensi, 2014

#====================

import inspect
import os
import os.path
import shutil
import sys
import subprocess

from .simplelogging import Logging
from .simpletypes import Boolean, String, StringList, Tuple
from .stringutil import newlineReplacedString
from .typesupport import isString, toUnicodeString

#====================

class OperatingSystem:
    """Encapsulates access to operating system functions."""

    nullDevice = open(os.devnull)
    pathSeparator = os.sep

    #--------------------

    @classmethod
    def basename (cls,
                  fileName : String,
                  extensionIsShown : Boolean = True) -> String:
        """Returns <fileName> without leading path."""

        shortFileName = os.path.basename(fileName)
        partList = os.path.splitext(shortFileName)
        result = (shortFileName if extensionIsShown else partList[0])
        return result

    #--------------------

    @classmethod
    def copyFile (cls,
                  sourceFileName : String,
                  targetName : String,
                  targetDirectoryCreationIsForced : Boolean = False):
        """Copies file with <sourceFileName> to either file or
           directory target with <targetName>; if
           <targetDirectoryCreationIsForced>, target directory is
           created when it does not exist"""

        Logging.trace(">>: %r -> %r", sourceFileName, targetName)

        isOkay = True

        if cls.hasDirectory(targetName):
            directoryName = targetName
        else:
            directoryName = cls.dirname(targetName)

        if not cls.hasDirectory(directoryName):
            if targetDirectoryCreationIsForced:
                os.makedirs(directoryName, exist_ok=True)
            else:
                errorMessage = "cannot create directory %s"
                cls.showMessageOnConsole(errorMessage % directoryName)
                Logging.traceError(errorMessage, directoryName)
                isOkay = False

        if isOkay:
            shutil.copy2(sourceFileName, targetName)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def currentDirectoryPath (cls) -> String:
        """Returns current directory of program."""

        Logging.trace(">>")
        result = os.getcwd()
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def dirname (cls,
                 filePath : String) -> String:
        """Returns directory of <filePath>."""

        pathSeparatorA = "/"
        pathSeparatorB =  "\\"
        resultA, _, _ = filePath.rpartition(pathSeparatorA)
        resultB, _, _ = filePath.rpartition(pathSeparatorB)
        result = resultB if len(resultB) > len(resultA) else resultA
        return result

    #--------------------

    @classmethod
    def executeCommand (cls,
                        command : StringList,
                        abortOnFailure : Boolean = False) -> Tuple:
        """Processes <command> (specified as list) in operating
           system.  When <abortOnFailure> is set, any non-zero return
           code aborts the program at once.  Returns completion code
           and string returned by command in stdout and stderr"""

        Logging.trace(">>: %r", command)

        completedProcess = subprocess.run(command,
                                          stdout = subprocess.PIPE,
                                          stderr = subprocess.STDOUT)

        loggingString = completedProcess.stdout
        loggingString = loggingString.decode()
        completionCode = completedProcess.returncode

        if abortOnFailure and completionCode != 0:
            message = ("ERROR: return code %d for %s"
                       % (completionCode, " ".join(command)))
            Logging.trace("--: %s", message)
            sys.exit("%s%n%s" % (loggingString, message))

        result = (completionCode, loggingString)
        Logging.trace("<<: (%s, %r)",
                      completionCode, newlineReplacedString(loggingString))
        return result

    #--------------------

    @classmethod
    def fullFilePath (cls,
                      fileName : String) -> String:
        """Tells the full file path for <fileName>"""

        Logging.trace(">>")

        if cls.isAbsoluteFileName(fileName):
            result = fileName
        else:
            result = "%s/%s" % (cls.currentDirectoryPath(), fileName)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def hasFile (cls,
                 fileName : String) -> Boolean:
        """Tells whether <fileName> signifies a file."""

        return isString(fileName) and os.path.isfile(fileName)

    #--------------------

    @classmethod
    def hasDirectory (cls,
                      directoryName : String) -> Boolean:
        """Tells whether <directoryName> signifies a directory."""

        return isString(directoryName) and os.path.isdir(directoryName)

    #--------------------

    @classmethod
    def homeDirectoryPath (cls) -> String:
        """Returns home directory path."""

        Logging.trace(">>")

        result = os.getenv("HOMEPATH")
        result = result if result is not None else os.getenv("HOME")
        result = result if result is not None else os.path.expanduser("~")
        result = toUnicodeString(result)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def isAbsoluteFileName (cls,
                            fileName : String) -> Boolean:
        """Tells whether <fileName> is absolute"""

        Logging.trace(">>")
        result = (len(fileName) > 2
                  and (fileName[1] == ":"
                       or fileName.startswith("\\")
                       or fileName.startswith("/")))
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def loggingDirectoryPath (cls) -> String:
        """Returns logging directory path."""

        Logging.trace(">>")

        result = os.getenv("LOGS")
        result = result if result is not None else cls.tempDirectoryPath()
        result = toUnicodeString(result)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def moveFile (cls,
                  sourceFileName : String,
                  targetName : String):
        """Moves file with <sourceFileName> to either file or
           directory target with <targetName>."""

        Logging.trace(">>: %r -> %r", sourceFileName, targetName)

        if cls.hasDirectory(targetName):
            directoryName = targetName
        else:
            directoryName = cls.dirname(targetName)

        if not cls.hasDirectory(directoryName):
            os.makedirs(directoryName, exist_ok=True)

        shutil.copy(sourceFileName, targetName)
        os.remove(sourceFileName)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def programIsAvailable (cls,
                            programName : String,
                            option : String) -> Boolean:
        """Checks whether program with <programName> can be called."""

        nullDevice = open(os.devnull, 'w')

        try:
            callResult = subprocess.call([programName, option],
                                         stdout=nullDevice)
        except:
            callResult = 1

        return (callResult == 0)

    #--------------------

    @classmethod
    def removeFile (cls,
                    fileName : String,
                    fileIsKept : Boolean = False):
        """Removes file with <fileName> permanently."""

        Logging.trace(">>: %r", fileName)

        if fileIsKept:
            Logging.trace("--: not removed %r", fileName)
        elif not cls.hasFile(fileName):
            Logging.trace("--: file already nonexisting %r", fileName)
        else:
            Logging.trace("--: removing %r", fileName)
            os.remove(fileName)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def scriptFilePath (cls) -> String:
        """Returns file path of calling script."""

        Logging.trace(">>")

        result = os.path.abspath(inspect.stack()[1][1])

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def showMessageOnConsole (cls,
                              message : String,
                              newlineIsAppended : Boolean = True):
        """Shows <message> on console (stderr) for giving a trace information
           to user; <newlineIsAppended> tells whether a newline is added at
           the end of the message"""

        Logging.trace("--: %r", message)
        st = message + ("\n" if newlineIsAppended else "")
        sys.stderr.write(st)
        sys.stderr.flush()

    #--------------------

    @classmethod
    def tempDirectoryPath (cls) -> String:
        """Returns temporary directory path."""

        Logging.trace(">>")

        result = os.getenv("TMP")
        result = result if result is not None else os.getenv("TEMP")
        result = toUnicodeString(result)

        Logging.trace("<<: %r", result)
        return result
