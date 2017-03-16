# -*- coding: utf-8-unix -*-
# mla_overallsettings -- services for access to the global configuration file
#                        of makeLilypondAll

#====================

from configurationfile import ConfigurationFile
from simplelogging import Logging
from ttbase import convertStringToList
from validitychecker import ValidityChecker

#====================

class VideoDeviceType:
    """This class encapsulates the settings for a video device used
       for video generation."""

    #--------------------

    def __init__ (self):
        self.name = None
        self.fileNameSuffix = None
        self.targetVideoDirectory = None
        self.resolution = None
        self.height = None
        self.width = None
        self.topBottomMargin = None
        self.leftRightMargin = None
        self.systemSize = None
        self.subtitleColor = None
        self.subtitleFontSize = None

    #--------------------

    def __repr__ (self):
        clsName = self.__class__.__name__
        st = (("%s(name = %s, fileNameSuffix = %s, targetVideoDirectory = %s,"
               + " resolution = %s, height = %s, width = %s,"
               + " topBottomMargin = %s, leftRightMargin = %s,"
               + " systemSize = %s, subtitleColor = %s, subtitleFontSize = %s")
              %
              (clsName, self.name, self.fileNameSuffix,
               self.targetVideoDirectory, self.resolution, self.height,
               self.width, self.topBottomMargin, self.leftRightMargin,
               self.systemSize, self.subtitleColor, self.subtitleFontSize))
        return st

#====================

class MLA_OverallSettings:
    """This class encapsulates the settings read from a global
       configuration file like e.g. the commands for ffmpeg, sox,
       etc. as well as file name templates."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _adaptVideoDeviceList (self, st):
        """Converts video device data encoded in <st> into a list
           of video devices"""

        Logging.trace(">>: %s", st)

        errorPosition, errorMessage, table = \
            ConfigurationFile.parseTableDefinitionString(st)

        result = []

        if errorPosition < 0:
            fieldNameList = [ "fileNameSuffix", "targetVideoDirectory",
                              "resolution", "height", "width",
                              "topBottomMargin", "leftRightMargin",
                              "systemSize", "subtitleColor",
                              "subtitleFontSize" ]
            errorMessage = ""
            
            for deviceName in table.keys():
                device = VideoDeviceType()
                device.name = deviceName
                info = table[deviceName]
                Logging.trace("--: converting %s = %s", deviceName, info)

                for fieldName in fieldNameList:
                    if info.get(fieldName) is None:
                        errorMessage = "no value for %s" % fieldName

                if errorMessage != "":
                    break

                device.fileNameSuffix       = info["fileNameSuffix"]
                device.targetVideoDirectory = info["targetVideoDirectory"]
                device.resolution           = info["resolution"]
                device.height               = info["height"]
                device.width                = info["width"]
                device.topBottomMargin      = info["topBottomMargin"]
                device.leftRightMargin      = info["leftRightMargin"]
                device.systemSize           = info["systemSize"]
                device.subtitleColor        = info["subtitleColor"]
                device.subtitleFontSize     = info["subtitleFontSize"]

                result.append(device)

        Logging.trace("<<: %s", result)
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        self.aacCommand                     = "aac"
        self.ffmpegCommand                  = "ffmpeg"
        self.fluidsynthCommand              = "fluidsynth"
        self.humanizerConfigurationFileName = "styleHumanization.cfg"
        self.soundProcessorConfigFileName   = "soundProcessing.cfg"
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
        self.videoDeviceList                = []
        self.videoFrameRate                 = 10
        self.videoScalingFactor             = 4

    #--------------------

    def __repr__ (self):
        """Returns the string representation of <self>"""

        className = self.__class__.__name__
        st = (("%s("
               + "aacCommand = '%s', ffmpegCommand = '%s',"
               + " fluidsynthCommand = '%s',"
               + " humanizerConfigurationFileName = '%s',"
               + " soundProcessorConfigFileName = '%s',"
               + " lilypondCommand = '%s', lilypondMacroIncludePath = '%s',"
               + " loggingFilePath = '%s', mp4boxCommand = '%s',"
               + " soundFontDirectoryPath = '%s', soundFontNameList = %s,"
               + " soxCommand = '%s', targetDirectoryPath = '%s',"
               + " tempAudioDirectoryPath = '%s',"
               + " tempLilypondFilePath = '%s', videoDeviceList = %s,"
               + " videoFrameRate = %5.3f, videoScalingFactor = %d)")
              % (className,
                 self.aacCommand, self.ffmpegCommand, self.fluidsynthCommand,
                 self.humanizerConfigurationFileName,
                 self.soundProcessorConfigFileName, self.lilypondCommand,
                 self.lilypondMacroIncludePath, self.loggingFilePath,
                 self.mp4boxCommand, self.soundFontDirectoryPath,
                 self.soundFontNameList, self.soxCommand,
                 self.targetDirectoryPath, self.tempAudioDirectoryPath,
                 self.tempLilypondFilePath, self.videoDeviceList,
                 self.videoFrameRate, self.videoScalingFactor))
        return st

    #--------------------

    def checkValidity (self):
        """Checks the validity of data read from the configuration
           file"""

        Logging.trace(">>")

        ValidityChecker.isString(self.ffmpegCommand, "ffmpegCommand")
        ValidityChecker.isString(self.fluidsynthCommand, "fluidsynthCommand")
        ValidityChecker.isString(self.humanizerConfigurationFileName,
                                 "humanizerConfigurationFileName")
        ValidityChecker.isString(self.soundProcessorConfigFileName,
                                 "soundProcessorConfigFileName")
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
        self.aacCommand = getValueProc("aacCommand", None)
        self.ffmpegCommand = getValueProc("ffmpegCommand")
        self.fluidsynthCommand = getValueProc("fluidsynthCommand")
        self.humanizerConfigurationFileName = \
                 getValueProc("humanizerConfigurationFileName")
        self.soundProcessorConfigFileName = \
                 getValueProc("soundProcessorConfigurationFileName")
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
        videoDeviceList = getValueProc("videoDeviceList", "")
        self.videoDeviceList = self._adaptVideoDeviceList(videoDeviceList)
        self.videoFrameRate = getValueProc("videoFrameRate", 10.0)
        self.videoScalingFactor = getValueProc("videoScalingFactor", 4)


        Logging.trace("<<")
