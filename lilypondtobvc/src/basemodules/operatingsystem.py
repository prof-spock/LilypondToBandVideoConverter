# operatingsystem -- provides simple facilities for access of operating
#                    system services
#
# author: Dr. Thomas Tensi, 2014

#====================

import os

from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, String, StringList, Tuple
from basemodules.stringutil import newlineReplacedString, splitAt
from basemodules.typesupport import isString, toUnicodeString
from basemodules.ttbase import iif, isMicroPython, isStdPython

if isStdPython:
    import inspect
    import os.path
    import shutil
    import sys
    import subprocess

# MicroPython constants
_MP_S_IFDIR = 0x4000
_MP_S_IFREG = 0x8000

#====================

class OperatingSystem:
    """Encapsulates access to operating system functions."""

    pathSeparator = os.sep if isStdPython else "/"

    #--------------------
    # PRIVATE FEATURES
    #--------------------

    @classmethod
    def _copyOrMoveFile (cls,
                         sourceFileName : String,
                         destinationName : String,
                         isCopyOperation : Boolean,
                         destinationDirectoryCreationIsForced : Boolean = False):
        """Depending on <isCopyOperation> either copies or moves file
           with <sourceFileName> to either file or directory destination
           with <destinationName>; if <destinationDirectoryCreationIsForced>,
           destination directory is created when it does not exist"""

        Logging.trace(">>: %s %r -> %r",
                      iif(isCopyOperation, "copy", "move"),
                      sourceFileName, destinationName)

        if isStdPython:
            isOkay = True

            if cls.hasDirectory(destinationName):
                directoryName = destinationName
            else:
                directoryName = cls.dirname(destinationName)

            if not cls.hasDirectory(directoryName):
                if destinationDirectoryCreationIsForced:
                    cls.makeDirectory(directoryName)
                else:
                    errorMessage = "cannot create directory %s"
                    cls.showMessageOnConsole(errorMessage % directoryName)
                    Logging.traceError(errorMessage, directoryName)
                    isOkay = False

            if isOkay:
                path = shutil.copy2(sourceFileName, destinationName)
                isOkay = (path is not None)

            if isOkay and not isCopyOperation:
                os.remove(sourceFileName)

        Logging.trace("<<")

    #--------------------
    # EXPORTED METHODS
    #--------------------

    @classmethod
    def basename (cls,
                  fileName : String,
                  extensionIsShown : Boolean = True) -> String:
        """Returns <fileName> without leading path."""

        standardSeparator = "/"
        fileName = fileName.replace("\\", standardSeparator)
        filePartList = fileName.split(standardSeparator)
        shortFileName = filePartList[-1]

        if len(shortFileName) > 2 and shortFileName[1] == ":":
            # remove windows drive indication
            shortFileName = shortFileName[2:]

        if not extensionIsShown:
            shortFileName, extension, _ = splitAt(shortFileName, ".")
            
        result = shortFileName
        return result

    #--------------------

    @classmethod
    def copyFile (cls,
                  sourceFileName : String,
                  destinationName : String,
                  destinationDirectoryCreationIsForced : Boolean = False):
        """Copies file with <sourceFileName> to either file or
           directory destination with <destinationName>; if
           <destinationDirectoryCreationIsForced>, destination directory is
           created when it does not exist"""

        Logging.trace(">>: %r -> %r", sourceFileName, destinationName)
        cls._copyOrMoveFile(sourceFileName, destinationName, True,
                            destinationDirectoryCreationIsForced)
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

        standardSeparator = "/"
        filePath = filePath.replace("\\", standardSeparator)
        filePartList = filePath.split(standardSeparator)

        if len(filePartList) > 1:
            result = standardSeparator.join(filePartList[:-1])
        else:
            result = filePartList[0]

            if len(result) > 2 and result[1] == ":":
                result = result[:2]
            else:
                result = ""

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

        if not isStdPython:
            Logging.traceError("cannot run %s", command)
            completionCode = 1
            loggingString = ""
        else:
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
                sys.exit("%s\n%s" % (loggingString, message))

        result = (completionCode, loggingString)

        Logging.trace("<<: (%s, %r)",
                      completionCode, newlineReplacedString(loggingString))
        return result

    #--------------------

    @classmethod
    def fileNameList (cls,
                      directoryName : String,
                      plainFilesOnly : Boolean) -> StringList:
        """Returns the list of files in <directoryName>; if
           <plainFilesOnly> is set, only plain files are returned,
           otherwise only the names of the sub-directories"""

        Logging.trace(">>: directory = %s, plainFilesOnly = %s",
                      directoryName, plainFilesOnly)

        Logging.trace("--: isMicroPython = %s", isMicroPython)

        if isMicroPython:
            hasPredicateProc = iif(plainFilesOnly,
                                   lambda f: (f[1] % _MP_S_IFREG) != 0,
                                   lambda f: (f[1] % _MP_S_IFDIR) != 0)
            listDirProc = os.ilistdir
            nameSelectionProc = lambda x: x[0]
        else:
            hasPredicateProc = iif(plainFilesOnly,
                                   lambda f: f.is_file(),
                                   lambda f: f.is_dir())
            listDirProc = os.scandir
            nameSelectionProc = lambda x: x.name

        result = [ nameSelectionProc(fileEntry)
                   for fileEntry in listDirProc(directoryName)
                   if hasPredicateProc(fileEntry) ]

        Logging.trace("<<: %r", result)
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
            result = cls.normalizedFileName(result)
                    
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def hasFile (cls,
                 fileName : String) -> Boolean:
        """Tells whether <fileName> signifies a file."""

        checkProc = (os.path.isfile if isStdPython
                     else lambda st: os.stat(st)[0] & _MP_S_IFREG != 0)
        return isString(fileName) and checkProc(fileName)

    #--------------------

    @classmethod
    def hasDirectory (cls,
                      directoryName : String) -> Boolean:
        """Tells whether <directoryName> signifies a directory."""

        checkProc = (os.path.isdir if isStdPython
                     else lambda st: os.stat(st)[0] & _MP_S_IFDIR != 0)
        return isString(directoryName) and checkProc(directoryName)

    #--------------------

    @classmethod
    def homeDirectoryPath (cls) -> String:
        """Returns home directory path."""

        Logging.trace(">>")

        if isMicroPython:
            result = "???"
        else:
            result = os.getenv("HOME")
            result = result if result is not None else os.getenv("HOMEPATH")
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
    def isWritableFile (cls, fileName) -> Boolean:
        """Returns whether file named <fileName> is writable.  Opens it
           for writing and hence clears its contents"""

        Logging.trace(">>: %r", fileName)

        directoryName = cls.dirname(fileName)
        isOkay = cls.hasDirectory(directoryName)

        if isOkay and cls.hasFile(fileName):
            try:
                file = os.open(fileName,
                               os.O_APPEND | os.O_EXCL | os.O_RDWR)
            except OSError:
                isOkay = False

            if isOkay:
                if not isPython2:
                    try:
                        # try the MSWindows file locking
                        import msvcrt
                        msvcrt.locking(file, msvcrt.LK_NBLCK, 1)
                        msvcrt.locking(file, msvcrt.LK_UNLCK, 1)
                    except (OSError, IOError):
                        isOkay = False

                os.close(file)

        Logging.trace("<<: %r", isOkay)
        return isOkay
    
    #--------------------

    @classmethod
    def loggingDirectoryPath (cls) -> String:
        """Returns logging directory path."""

        Logging.trace(">>")

        if isMicroPython:
            result = "???"
        else:
            result = os.getenv("LOGS")
            result = (result if result is not None
                      else cls.tempDirectoryPath())
            result = toUnicodeString(result)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def makeDirectory (cls,
                       directoryName : String):
        """Creates directory named <directoryName>."""

        Logging.trace(">>: %s", directoryName)

        if cls.hasDirectory(directoryName):
            Logging.trace("--: directory already exists")
        elif isMicroPython:
            os.makedir(directoryName)
        else:
            os.makedirs(directoryName, exist_ok=True)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def moveFile (cls,
                  sourceFileName : String,
                  destinationName : String,
                  destinationDirectoryCreationIsForced : Boolean = False):
        """Moves file with <sourceFileName> to either file or
           directory destination with <destinationName>; if
           <destinationDirectoryCreationIsForced>, destination directory is
           created when it does not exist"""

        Logging.trace(">>: %r -> %r", sourceFileName, destinationName)
        cls._copyOrMoveFile(sourceFileName, destinationName, False,
                            destinationDirectoryCreationIsForced)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def normalizedFileName (cls,
                            fileName : String) -> String:
        """Resolves parent and current directory parts in <fileName> and
           returns normalized version"""

        Logging.trace(">>: %s", fileName)

        partList = fileName.replace("\\", "/").split("/")
        result = partList[-1]
        skipCount = 0

        # sanitize path
        for part in reversed(partList[:-1]):
            if skipCount > 0:
                skipCount -= 1
            elif part == ".":
                pass
            elif part == "..":
                skipCount += 1
            else:
                result = part + cls.pathSeparator + result
        
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def programIsAvailable (cls,
                            programName : String,
                            option : String) -> Boolean:
        """Checks whether program with <programName> can be called."""

        if not isStdPython:
            result = False
        else:
            nullDevice = open(os.devnull, 'w')

            try:
                callResult = subprocess.call([programName, option],
                                             stdout=nullDevice)
            except:
                callResult = 1

            result = (callResult == 0)

        return result

    #--------------------

    @classmethod
    def removeFile (cls,
                    fileName : String,
                    fileIsKept : Boolean = False):
        """Removes file with <fileName> permanently."""

        Logging.trace(">>: %r", fileName)

        fileName = cls.normalizedFileName(fileName)

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

        if not isStdPython:
            result = "???"
        else:
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

        if isStdPython:
            st = message + ("\n" if newlineIsAppended else "")
            sys.stderr.write(st)
            sys.stderr.flush()

    #--------------------

    @classmethod
    def tempDirectoryPath (cls) -> String:
        """Returns temporary directory path."""

        Logging.trace(">>")

        if not isStdPython:
            result = "???"
        else:
            result = os.getenv("TMP")
            result = result if result is not None else os.getenv("TEMP")
            result = toUnicodeString(result)

        Logging.trace("<<: %r", result)
        return result
