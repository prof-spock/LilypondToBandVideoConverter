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

from .typesupport import isString
from .simplelogging import Logging

#====================

class OperatingSystem:
    """Encapsulates access to operating system functions."""

    nullDevice = open(os.devnull)
    pathSeparator = os.sep

    #--------------------

    @classmethod
    def basename (cls, fileName, extensionIsShown=False):
        """Returns <fileName> without leading path."""

        pathSeparatorPosition = max(fileName.rfind("/"),
                                    fileName.rfind("\\"))
        shortFileName = fileName[pathSeparatorPosition + 1:]

        if extensionIsShown:
            result = shortFileName
        else:
            dotPosition = shortFileName.rfind(".")
            result = shortFileName[:dotPosition]

        return result

    #--------------------

    @classmethod
    def dirname (cls, filePath):
        """Returns directory of <filePath>."""

        return os.path.dirname(filePath)

    #--------------------

    @classmethod
    def executeCommand (cls, command, abortOnFailure=False,
                        stdin=None, stdout=None, stderr=None):
        """Processes <command> (specified as list) in operating
          system. When <abortOnFailure> is set, any non-zero
          return code aborts the program at once."""

        Logging.trace(">>: %r", command)

        completionCode = subprocess.call(command,
                                         stdin=stdin, stdout=stdout,
                                         stderr=stderr)

        if abortOnFailure and completionCode != 0:
            message = ("ERROR: return code %d for %s"
                       % (completionCode, " ".join(command)))
            Logging.log(message)
            sys.exit(message)

        Logging.trace("<<")
        return completionCode

    #--------------------

    @classmethod
    def hasFile (cls, fileName):
        """Tells whether <fileName> signifies a file."""

        return isString(fileName) and os.path.isfile(fileName)

    #--------------------

    @classmethod
    def hasDirectory (cls, directoryName):
        """Tells whether <directoryName> signifies a directory."""

        return isString(directoryName) and os.path.isdir(directoryName)

    #--------------------

    @classmethod
    def homeDirectoryPath (cls):
        """Returns home directory path."""

        Logging.trace(">>")

        result = os.path.expanduser("~")
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def moveFile (cls, sourceFileName, targetName):
        """Moves file with <sourceFileName> to either file or
           directory target with <targetName>."""

        Logging.trace(">>: %r -> %r", sourceFileName, targetName)
        shutil.copy(sourceFileName, targetName)
        os.remove(sourceFileName)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def programIsAvailable (cls, programName, option):
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
    def removeFile (cls, fileName, fileIsKept=False):
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
    def scriptFilePath (cls):
        """Returns file path of calling script."""

        Logging.trace(">>")

        result = os.path.abspath(inspect.stack()[1][1])

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def showMessageOnConsole (cls, message, newlineIsAppended=True):
        """Shows <message> on console (stderr) for giving a trace information
           to user; <newlineIsAppended> tells whether a newline is added at
           the end of the message"""

        Logging.trace("--: %r", message)
        st = message + ("\n" if newlineIsAppended else "")
        sys.stderr.write(st)
        sys.stderr.flush()
