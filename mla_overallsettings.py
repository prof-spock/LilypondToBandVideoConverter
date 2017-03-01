# mla_overallsettings -- services for access to the global configuration file
#                        of makeLilypondAll

#====================

from configurationfile import ConfigurationFile
from simplelogging import Logging
from ttbase import convertStringToList
from validitychecker import ValidityChecker

#====================

class MLA_OverallSettings:
    """This class encapsulates the settings read from a global
       configuration file like e.g. the commands for ffmpeg, sox,
       etc. as well as file name templates."""

    #--------------------

    def __init__ (self):
        self.aacCommand                     = "aac"
        self.ffmpegCommand                  = "ffmpeg"
        self.fluidsynthCommand              = "fluidsynth"
        self.humanizerConfigurationFileName = "styleHumanization.cfg"
        self.lilypondCommand                = "lilypond"
        self.lilypondMacroIncludePath       = "/"
        self.loggingFileName                = ("C:/temp/logs"
                                               + "/makeLilypondAll.log")
        self.moveCommand                    = "mv"
        self.soundFontDirectoryName         = "C:/temp/soundfonts"
        self.soundFontNameList              = ""
        self.soxCommand                     = "sox"
        self.targetDirectoryName            = "generated"
        self.tempAudioDirectoryPath         = "/temp"
        self.tempLilypondFileName           = "temp.ly"

    #--------------------

    def __str__ (self):
        """Returns the string representation of <self>"""

        className = self.__class__.__name__
        st = (("%s("
               + "aacCommand = '%s', ffmpegCommand = '%s',"
               + " fluidsynthCommand = '%s',"
               + " humanizerConfigurationFileName = '%s',"
               + " lilypondCommand = '%s', lilypondMacroIncludePath = '%s',"
               + " loggingFileName = '%s', moveCommand = '%s',"
               + " soundFontDirectoryName = '%s', soundFontNameList = %s,"
               + " soxCommand = '%s', targetDirectoryName = '%s',"
               + " tempAudioDirectoryPath = '%s',"
               + " tempLilypondFileName = '%s')")
              % (className,
                 self.aacCommand, self.ffmpegCommand, self.fluidsynthCommand,
                 self.humanizerConfigurationFileName, self.lilypondCommand,
                 self.lilypondMacroIncludePath, self.loggingFileName,
                 self.moveCommand, self.soundFontDirectoryName,
                 self.soundFontNameList, self.soxCommand,
                 self.targetDirectoryName, self.tempAudioDirectoryPath,
                 self.tempLilypondFileName))
        return st

    #--------------------

    def checkValidity (self):
        """Checks the validity of data read from the configuration
           file"""

        Logging.trace(">>")

        ValidityChecker.isString(self.aacCommand, "aacCommand")
        ValidityChecker.isString(self.ffmpegCommand, "ffmpegCommand")
        ValidityChecker.isString(self.fluidsynthCommand, "fluidsynthCommand")
        ValidityChecker.isString(self.humanizerConfigurationFileName,
                                 "humanizerConfigurationFileName")
        ValidityChecker.isString(self.lilypondCommand, "lilypondCommand")
        ValidityChecker.isString(self.lilypondMacroIncludePath,
                                 "lilypondMacroIncludePath")
        ValidityChecker.isString(self.loggingFileName, "loggingFileName")
        ValidityChecker.isString(self.moveCommand, "moveCommand")
        ValidityChecker.isString(self.soundFontDirectoryName,
                                 "soundFontDirectoryName")
        ValidityChecker.isString(self.soxCommand, "soxCommand")
        ValidityChecker.isString(self.targetDirectoryName,
                                 "targetDirectoryName")
        ValidityChecker.isString(self.tempAudioDirectoryPath,
                                 "tempAudioDirectoryPath")
        ValidityChecker.isString(self.tempLilypondFileName,
                                 "tempLilypondFileName")

        Logging.trace("<<: %s", str(self))

    #--------------------

    def readFile (self, configurationFileName):
        """Reads data from configuration file with
           <configurationFileName> into <self>."""

        Logging.trace(">>: '%s'", configurationFileName)

        configurationFile = ConfigurationFile(configurationFileName)
        getValueProc = configurationFile.getValue

        # read all values
        self.aacCommand = getValueProc("aacCommand", True)
        self.ffmpegCommand = getValueProc("ffmpegCommand", True)
        self.fluidsynthCommand = getValueProc("fluidsynthCommand", True)
        self.humanizerConfigurationFileName = \
                 getValueProc("humanizerConfigurationFileName", True)
        self.lilypondCommand = getValueProc("lilypondCommand", True)
        self.lilypondMacroIncludePath = \
                 getValueProc("lilypondMacroIncludePath", True)
        self.loggingFileName = getValueProc("loggingFileName", True)
        self.moveCommand = getValueProc("moveCommand", True)
        self.soundFontDirectoryName = getValueProc("soundFontDirectoryName",
                                                   True)
        self.soundFontNameList = \
                 convertStringToList(getValueProc("soundFontNames", True))
        self.soxCommand = getValueProc("soxCommand", True)
        self.targetDirectoryName = getValueProc("targetDirectoryName", True)
        self.tempLilypondFileName = getValueProc("tempLilypondFileName",
                                                 True)
        self.tempAudioDirectoryPath = getValueProc("tempAudioDirectoryPath",
                                                   True)

        Logging.trace("<<")
