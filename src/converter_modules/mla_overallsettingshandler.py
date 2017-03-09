# -*- coding: utf-8 -*-
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
        self.humanizerConfigurationFilePath = "styleHumanization.cfg"
        self.lilypondCommand                = "lilypond"
        self.lilypondMacroIncludePath       = "/"
        self.loggingFilePath                = ("C:/temp/logs"
                                               + "/makeLilypondAll.log")
        self.mp4boxCommand                  = "mp4box"
        self.soundFontDirectoryPath         = "C:/temp/soundfonts"
        self.soundFontNameList              = ""
        self.soxCommand                     = "sox"
        self.targetDirectoryPath            = "generated"
        self.tempAudioDirectoryPath         = "/temp"
        self.tempLilypondFilePath           = "temp.ly"
        self.videoFrameRate                 = 10
        self.videoScalingFactor             = 4

    #--------------------

    def __str__ (self):
        """Returns the string representation of <self>"""

        className = self.__class__.__name__
        st = (("%s("
               + "aacCommand = '%s', ffmpegCommand = '%s',"
               + " fluidsynthCommand = '%s',"
               + " humanizerConfigurationFilePath = '%s',"
               + " lilypondCommand = '%s', lilypondMacroIncludePath = '%s',"
               + " loggingFilePath = '%s', mp4boxCommand = '%s',"
               + " soundFontDirectoryPath = '%s', soundFontNameList = %s,"
               + " soxCommand = '%s', targetDirectoryPath = '%s',"
               + " tempAudioDirectoryPath = '%s',"
               + " tempLilypondFilePath = '%s', videoFrameRate = %5.3f,"
               + " videoScalingFactor = %d)")
              % (className,
                 self.aacCommand, self.ffmpegCommand, self.fluidsynthCommand,
                 self.humanizerConfigurationFilePath, self.lilypondCommand,
                 self.lilypondMacroIncludePath, self.loggingFilePath,
                 self.mp4boxCommand, self.soundFontDirectoryPath,
                 self.soundFontNameList, self.soxCommand,
                 self.targetDirectoryPath, self.tempAudioDirectoryPath,
                 self.tempLilypondFilePath, self.videoFrameRate,
                 self.videoScalingFactor))
        return st

    #--------------------

    def checkValidity (self):
        """Checks the validity of data read from the configuration
           file"""

        Logging.trace(">>")

        ValidityChecker.isString(self.aacCommand, "aacCommand")
        ValidityChecker.isString(self.ffmpegCommand, "ffmpegCommand")
        ValidityChecker.isString(self.fluidsynthCommand, "fluidsynthCommand")
        ValidityChecker.isString(self.humanizerConfigurationFilePath,
                                 "humanizerConfigurationFilePath")
        ValidityChecker.isString(self.lilypondCommand, "lilypondCommand")
        ValidityChecker.isString(self.lilypondMacroIncludePath,
                                 "lilypondMacroIncludePath")
        ValidityChecker.isString(self.loggingFilePath, "loggingFilePath")
        ValidityChecker.isString(self.mp4boxCommand, "mp4boxCommand")
        ValidityChecker.isString(self.soundFontDirectoryPath,
                                 "soundFontDirectoryPath")
        ValidityChecker.isString(self.soxCommand, "soxCommand")
        ValidityChecker.isString(self.targetDirectoryPath,
                                 "targetDirectoryPath")
        ValidityChecker.isString(self.tempAudioDirectoryPath,
                                 "tempAudioDirectoryPath")
        ValidityChecker.isString(self.tempLilypondFilePath,
                                 "tempLilypondFilePath")
        ValidityChecker.isFloat(self.videoFrameRate, "videoFrameRate")
        ValidityChecker.isNatural(self.videoScalingFactor,
                                  "videoScalingFactor")

        Logging.trace("<<: %s", str(self))

    #--------------------

    def readFile (self, configurationFilePath):
        """Reads data from configuration file with
           <configurationFilePath> into <self>."""

        Logging.trace(">>: '%s'", configurationFilePath)

        configurationFile = ConfigurationFile(configurationFilePath)
        getValueProc = configurationFile.getValue

        # read all values
        self.aacCommand = getValueProc("aacCommand")
        self.ffmpegCommand = getValueProc("ffmpegCommand")
        self.fluidsynthCommand = getValueProc("fluidsynthCommand")
        self.humanizerConfigurationFilePath = \
                 getValueProc("humanizerConfigurationFilePath")
        self.lilypondCommand = getValueProc("lilypondCommand")
        self.lilypondMacroIncludePath = \
                 getValueProc("lilypondMacroIncludePath")
        self.loggingFilePath = getValueProc("loggingFilePath", "")
        self.mp4boxCommand = getValueProc("mp4boxCommand")
        self.soundFontDirectoryPath = getValueProc("soundFontDirectoryPath")
        self.soundFontNameList = \
                 convertStringToList(getValueProc("soundFontNames"))
        self.soxCommand = getValueProc("soxCommand")
        self.targetDirectoryPath = getValueProc("targetDirectoryPath", ".")
        self.tempLilypondFilePath = getValueProc("tempLilypondFilePath",
                                                 "temp.ly")
        self.tempAudioDirectoryPath = getValueProc("tempAudioDirectoryPath",
                                                   ".")
        self.videoFrameRate = getValueProc("videoFrameRate", 10.0)
        self.videoScalingFactor = getValueProc("videoScalingFactor", 4)

        Logging.trace("<<")
