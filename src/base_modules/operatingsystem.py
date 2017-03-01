# operatingsystem -- provides simple facilities for access of operating
#                    system services

#====================

import inspect
import os
import os.path
from simplelogging import Logging
import shutil
import sys
import subprocess

#====================

class OperatingSystem:
    """Encapsulates access to operating system functions."""

    nullDevice = open(os.devnull)
    pathSeparator = os.sep

    #--------------------

    @classmethod
    def basename (cls, fileName):
        """Returns <fileName> without extension."""

        return os.path.splitext(fileName)[0]

    #--------------------

    @classmethod
    def dirname (cls, filePath):
        """Returns directory of <filePath>."""

        return os.path.dirname(filePath)

    #--------------------

    @classmethod
    def executeCommand (cls, command, commandIsShownOnly=False,
                        stdin=None, stdout=None, stderr=None):
        """Processes <command> (specified as list) in operating
          system. When <commandIsShownOnly> is set, there is only logging,
          no execution."""

        Logging.trace("--: executing '%s'", repr(command))

        if not commandIsShownOnly:
            subprocess.call(command,
                            stdin=stdin, stdout=stdout, stderr=stderr)

    #--------------------

    @classmethod
    def hasFile (cls, fileName):
        """Tells whether <fileName> signifies a file."""

        return os.path.isfile(fileName)

    #--------------------

    @classmethod
    def moveFile (cls, sourceFileName, targetName):
        """Moves file with <sourceFileName> to either file or
           directory target with <targetName>."""

        Logging.trace(">>: %s -> %s", sourceFileName, targetName)
        shutil.move(sourceFileName, targetName)
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
    def removeFile (cls, fileName, debuggingIsActive=False):
        """Removes file with <fileName> permanently."""

        Logging.trace(">>: %s", fileName)

        if debuggingIsActive:
            Logging.trace("--: not removed because of debugging '%s'",
                          fileName)
        elif not cls.hasFile(fileName):
            Logging.trace("--: file already nonexisting '%s'", fileName)
        else:
            Logging.trace("--: removing '%s'", fileName)
            os.remove(fileName)


    #--------------------

    @classmethod
    def scriptFileName (cls):
        """Returns file name of calling script."""

        Logging.trace(">>")

        result = os.path.abspath(inspect.stack()[1][1])

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def showMessageOnConsole (cls, message):
        """Shows <message> on console (stderr) for giving a trace
           information to user"""

        Logging.trace("--: %s", message)
        sys.stderr.write(message + "\n")
