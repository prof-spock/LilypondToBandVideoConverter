# -*- coding: utf-8-unix -*-
# mla_overallsettings -- services for access to the global configuration file
#                        of makeLilypondAll

#====================

import datetime
import re

from configurationfile import ConfigurationFile
from operatingsystem import OperatingSystem
from simplelogging import Logging
from ttbase import convertStringToList, iif, isInRange
from validitychecker import ValidityChecker

#--------------------

def checkSingleParameter (parameterName, kind, getValueProc,
                          defaultValue=None):
    """Checks whether parameter given by <parameterName> acquired by
       <getValueProc> with default <defaultValue> is of <kind>, stops program
       if not"""

    value = getValueProc(parameterName, defaultValue)

    if kind == "STR":
        ValidityChecker.isString(value, parameterName)
    elif kind == "NAT":
        ValidityChecker.isNatural(value, parameterName)
    elif kind == "BOOL":
        ValidityChecker.isBoolean(value, parameterName)
    elif kind == "FLT":
        ValidityChecker.isFloat(value, parameterName)
    elif kind == "DIR":
        ValidityChecker.isDirectory(value, parameterName)
    elif kind == "RFILE":
        ValidityChecker.isReadableFile(value, parameterName)
            

#====================
# TYPE DEFINITIONS
#====================

class _ConfigDataGlobal:
    """Represents all configuration data that is global e.g. the command paths
       for generation. Note that this categorization is just for systematics,
       any configuration variable can be set per song."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _adaptVideoDeviceList (cls, st):
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
                device = _VideoDeviceType()
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

    @classmethod
    def initialize (cls, configData):
        """Initializes global attributes of <configData>"""

        configData.aacCommand                     = "aac"
        configData.ffmpegCommand                  = "ffmpeg"
        configData.fluidsynthCommand              = "fluidsynth"
        configData.humanizerConfigurationFileName = "styleHumanization.cfg"
        configData.lilypondCommand                = "lilypond"
        configData.loggingFilePath                = ("C:/temp/logs"
                                                     + "/makeLilypondAll.log")
        configData.mp4boxCommand                  = "mp4box"
        configData.soundFontDirectoryPath         = "C:/temp/soundfonts"
        configData.soundFontNameList              = ""
        configData.soundProcessorConfigFileName   = "soundProcessing.cfg"
        configData.soxCommand                     = "sox"
        configData.soxGlobalOptions               = ""
        configData.targetDirectoryPath            = "generated"
        configData.tempAudioDirectoryPath         = "/temp"
        configData.tempLilypondFilePath           = "temp.ly"
        configData.videoDeviceList                = []
        configData.videoFrameRate                 = 10
        configData.videoScalingFactor             = 4

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the global attributes of
           <configData>"""

        className = cls.__name__
        st = (("%s("
               + "aacCommand = '%s', ffmpegCommand = '%s',"
               + " fluidsynthCommand = '%s',"
               + " humanizerConfigurationFileName = '%s',"
               + " soundProcessorConfigFileName = '%s',"
               + " lilypondCommand = '%s', mp4boxCommand = '%s',"
               + " loggingFilePath = '%s',"
               + " soundFontDirectoryPath = '%s', soundFontNameList = %s,"
               + " soxCommand = '%s', soxGlobalOptions = '%s',"
               + " targetDirectoryPath = '%s', tempAudioDirectoryPath = '%s',"
               + " tempLilypondFilePath = '%s', videoDeviceList = %s,"
               + " videoFrameRate = %5.3f, videoScalingFactor = %d)")
              % (className,
                 configData.aacCommand, configData.ffmpegCommand,
                 configData.fluidsynthCommand,
                 configData.humanizerConfigurationFileName,
                 configData.soundProcessorConfigFileName,
                 configData.lilypondCommand, configData.mp4boxCommand,
                 configData.loggingFilePath,
                 configData.soundFontDirectoryPath,
                 configData.soundFontNameList,
                 configData.soxCommand, configData.soxGlobalOptions,
                 configData.targetDirectoryPath,
                 configData.tempAudioDirectoryPath,
                 configData.tempLilypondFilePath,
                 configData.videoDeviceList, configData.videoFrameRate,
                 configData.videoScalingFactor))
        return st

    #--------------------

    @classmethod
    def checkValidity (cls, getValueProc):
        """Checks the validity of data to be read from the configuration
           file for the global attributes"""

        Logging.trace(">>")

        checkSingleParameter("aacCommand", "STR", getValueProc, "")
        checkSingleParameter("ffmpegCommand", "STR", getValueProc)
        checkSingleParameter("fluidsynthCommand", "STR", getValueProc)
        checkSingleParameter("humanizerConfigurationFileName", "STR",
                             getValueProc)
        checkSingleParameter("soundProcessorConfigurationFileName", "STR",
                             getValueProc)
        checkSingleParameter("lilypondCommand", "STR", getValueProc)
        checkSingleParameter("loggingFilePath", "STR", getValueProc, "")
        checkSingleParameter("mp4boxCommand", "STR", getValueProc)
        checkSingleParameter("soundFontDirectoryPath", "STR", getValueProc)
        checkSingleParameter("soxCommand", "STR", getValueProc)
        checkSingleParameter("soxGlobalOptions", "STR", getValueProc, "")
        checkSingleParameter("targetDirectoryPath", "STR", getValueProc, ".")
        checkSingleParameter("tempAudioDirectoryPath", "STR", getValueProc)
        checkSingleParameter("tempLilypondFilePath", "STR", getValueProc, "")
        checkSingleParameter("videoDeviceList", "STR", getValueProc, "")
        checkSingleParameter("videoFrameRate", "FLT", getValueProc, 10.0)
        checkSingleParameter("videoScalingFactor", "NAT", getValueProc, 4)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, getValueProc):
        """Reads global configuration data via <getValueProc> from
           configuration file into <configData>."""

        Logging.trace(">>")

        configData.aacCommand = getValueProc("aacCommand", "")
        configData.ffmpegCommand = getValueProc("ffmpegCommand")
        configData.fluidsynthCommand = getValueProc("fluidsynthCommand")
        configData.humanizerConfigurationFileName = \
                 getValueProc("humanizerConfigurationFileName")
        configData.soundProcessorConfigFileName = \
                 getValueProc("soundProcessorConfigurationFileName")
        configData.lilypondCommand = getValueProc("lilypondCommand")
        configData.loggingFilePath = getValueProc("loggingFilePath", "")
        configData.mp4boxCommand = getValueProc("mp4boxCommand")
        configData.soundFontDirectoryPath = \
          getValueProc("soundFontDirectoryPath")
        configData.soundFontNameList = \
                 convertStringToList(getValueProc("soundFontNames"))
        configData.soxCommand = getValueProc("soxCommand")
        configData.soxGlobalOptions = getValueProc("soxGlobalOptions", "")
        configData.targetDirectoryPath = \
          getValueProc("targetDirectoryPath", ".")
        configData.tempLilypondFilePath = getValueProc("tempLilypondFilePath",
                                                       "temp.ly")
        configData.tempAudioDirectoryPath = \
          getValueProc("tempAudioDirectoryPath", ".")
        videoDeviceList = getValueProc("videoDeviceList", "")
        configData.videoDeviceList = \
          cls._adaptVideoDeviceList(videoDeviceList)
        configData.videoFrameRate = getValueProc("videoFrameRate", 10.0)
        configData.videoScalingFactor = getValueProc("videoScalingFactor", 4)

        Logging.trace("<<")

#====================

class _ConfigDataAlbum:
    """Represents all configuration data that is considered to be related to an
       album like e.g. the name of the album or the album artist for
       generation. Note that this categorization is just for systematics, any
       configuration variable can be set per song."""

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes album related attributes of <configData>"""

        configData.albumArtFilePath         = None
        configData.albumName                = None
        configData.targetFileNamePrefix     = None
        configData.artistName               = None
        configData.audioTargetDirectoryPath = None
        configData.useHardVideoSubtitles    = None

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the album related
           attributes of <configData>"""

        st = (("%s("
               + "albumArtFilePath = '%s', albumName = '%s',"
               + " artistName = '%s', audioTargetDirectoryPath = '%s',"
               + " targetFileNamePrefix = %s,"
               + " useHardVideoSubtitles = %s)")
              % (cls.__name__,
                 configData.albumArtFilePath, configData.albumName,
                 configData.artistName, configData.audioTargetDirectoryPath,
                 configData.targetFileNamePrefix,
                 configData.useHardVideoSubtitles))

        return st
               
    #--------------------

    @classmethod
    def checkValidity (cls, getValueProc):
        """Checks the validity of data to be read from the configuration
           file for the album attributes"""

        Logging.trace(">>")

        # type checks
        checkSingleParameter("albumArtFilePath", "RFILE", getValueProc)
        checkSingleParameter("albumName", "STR", getValueProc, "")
        checkSingleParameter("artistName", "STR", getValueProc, "")
        checkSingleParameter("audioTargetDirectoryPath", "DIR", getValueProc)
        checkSingleParameter("targetFileNamePrefix", "STR",
                             getValueProc, "")
        checkSingleParameter("useHardVideoSubtitles", "BOOL", getValueProc,
                             True)
        checkSingleParameter("videoVoiceList", "STR", getValueProc)

        Logging.trace("<<")
        
    #--------------------

    @classmethod
    def read (cls, configData, getValueProc):
        """Reads album configuration data via <getValueProc> from
           configuration file into <configData>."""

        Logging.trace(">>")

        configData.albumName = getValueProc("albumName", "")
        configData.artistName = getValueProc("artistName", "")
        configData.audioTargetDirectoryPath = \
                 getValueProc("audioTargetDirectoryPath", "")
        configData.targetFileNamePrefix = \
          getValueProc("targetFileNamePrefix", "")
        configData.useHardVideoSubtitles = \
          getValueProc("useHardVideoSubtitles", True)
        configData.year = getValueProc("year", datetime.date.today().year)

        Logging.trace("<<")

#====================

class _ConfigDataSong:
    """Represents all configuration data for a song like e.g. the voice names
       or the song title. Note that this categorization is just for
       systematics, any configuration variable can be set per song."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _convertToVoiceMap (cls, configData,
                            voiceNames, midiChannels, midiInstruments,
                            midiVolumes, panPositions, audioVolumes,
                            reverbLevels, soundVariants):
        """Converts strings read from configuration file to voice name
           list and map to voice descriptors"""

        Logging.trace(">>")

        configData.voiceNameList = convertStringToList(voiceNames)

        midiChannelList    = convertStringToList(midiChannels, kind="I")
        midiInstrumentList = convertStringToList(midiInstruments, kind="I")
        midiVolumeList     = convertStringToList(midiVolumes, kind="I")
        panPositionList    = convertStringToList(panPositions)
        audioVolumeList    = convertStringToList(audioVolumes)
        reverbLevelList    = convertStringToList(reverbLevels, kind="F")
        soundVariantList   = convertStringToList(soundVariants)

        configData.voiceNameToVoiceDataMap = {}

        for i in xrange(len(configData.voiceNameList)):
            voiceDescriptor = _VoiceDescriptor()
            voiceName = configData.voiceNameList[i]
            voiceDescriptor.voiceName      = voiceName
            voiceDescriptor.midiChannel    = midiChannelList[i]
            voiceDescriptor.midiInstrument = midiInstrumentList[i]
            voiceDescriptor.midiVolume     = midiVolumeList[i]
            voiceDescriptor.panPosition    = panPositionList[i]
            voiceDescriptor.audioVolume    = audioVolumeList[i]
            voiceDescriptor.reverbLevel    = reverbLevelList[i]
            voiceDescriptor.soundVariant   = soundVariantList[i]
            configData.voiceNameToVoiceDataMap[voiceName] = voiceDescriptor

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _splitParallelTrackInfo (cls, configData, parallelTrackInfo):
        """Splits string <parallelTrackInfo> given for parallel track
           into file path, track volume and shift offset"""

        Logging.trace(">>: %s", parallelTrackInfo)

        defaultFilePath = ""
        defaultVolume   = 1.0
        defaultOffset   = 0.0
        
        if parallelTrackInfo == "":
            partList = [ defaultFilePath ]
        else:
            partList = parallelTrackInfo.split("/")

        if len(partList) == 1:
            partList.append(str(defaultVolume))

        if len(partList) == 2:
            partList.append(str(defaultOffset))
            
        configData.parallelTrackFilePath = partList[0]
        configData.parallelTrackVolume   = float(partList[1])
        configData.shiftOffset           = float(partList[2])

        Logging.trace("<<: %s", partList)
        
    #--------------------

    @classmethod
    def _splitOptionalVoiceInfo (cls, optionalVoiceNames):
        """Converts string <optionalVoiceNames> to mapping from voice
           name to suffices for album name and song name"""

        Logging.trace(">>: %s", optionalVoiceNames)

        result = {}

        errorPosition, errorMessage, table = \
            ConfigurationFile.parseTableDefinitionString(optionalVoiceNames)

        if errorPosition < 0:
            fieldNameList = [ "songNameSuffix", "albumNameSuffix" ]
            errorMessage = ""

            for voiceName in table.keys():
                info = table[voiceName]
                Logging.trace("--: converting %s = %s", voiceName, info)

                for fieldName in fieldNameList:
                    if info.get(fieldName) is None:
                        errorMessage = "no value for %s" % fieldName

                if errorMessage != "":
                    break

                songNameSuffix  = info["songNameSuffix"]
                albumNameSuffix = info["albumNameSuffix"]
                value = (albumNameSuffix, songNameSuffix)
                result[voiceName] = value
                Logging.trace("--: %s -> %s", voiceName, str(value))

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def _splitOverrideInfo (cls, overrideFiles):
        """Converts string <overrideFiles> to mapping from voice name
           to override file name"""

        Logging.trace(">>: %s", overrideFiles)

        result = {}
        overridePartList = overrideFiles.split(",")

        for part in overridePartList:
            part = part.strip()

            if part > "":
                voiceName, overrideFilePath = part.split(":")
                result[voiceName] = overrideFilePath
                Logging.trace("--: %s -> %s", voiceName, overrideFilePath)

        Logging.trace("<<: %s", str(result))
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes song related attributes of <configData>"""

        configData.debuggingIsActive             = False
        configData.optionalVoiceNameToSuffixMap  = {}
        configData.title                         = "%title%"
        configData.songComposerText              = None
        configData.songYear                      = None
        configData.trackNumber                   = 0
        configData.fileNamePrefix                = "XXXX"
        configData.includeFilePath               = "%includeFilePath%"
        configData.lyricsCountVocals             = 0
        configData.lyricsCountVocalsStandalone   = 0
        configData.lyricsCountBgVocals           = 0
        configData.lyricsCountBgVocalsStandalone = 0
        configData.useSpecialLayoutForExtracts   = False
        configData.styleHumanizationKind         = None
        configData.humanizedVoiceNameSet         = None
        configData.voiceNameList                 = ""
        configData.extractVoiceNameSet           = None
        configData.midiVoiceNameList             = ""
        configData.videoVoiceNameList            = ""
        configData.voiceNameToVoiceDataMap       = {}
        configData.voiceNameToOverrideFileMap    = {}
        configData.parallelTrackFilePath         = ""
        configData.parallelTrackVolume           = 1.0
        configData.shiftOffset                   = None
        configData.measureToTempoMap             = None
        configData.attenuationLevel              = 0

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the song related
           attributes of <configData>"""

        st = (("%s("
               + " debuggingIsActive = %s, title = '%s', fileNamePrefix = %s,"
               + " songComposerText = '%s', songYear = %d,"
               + " includeFilePath = '%s', optionalVoiceNameToSuffixMap = %s,"
               + " trackNumber = %d,"
               + " lyricsCountVocals = %d, lyricsCountVocalsStandalone = %d,"
               + " lyricsCountBgVocals = %d,"
               + " lyricsCountBgVocalsStandalone = %d,"
               + " voiceNameList = %s, extractVoiceNameSet = %s,"
               + " midiVoiceNameList = %s, videoVoiceNameList = %s,"
               + " voiceNameToVoiceDataMap = %s,"
               + " voiceNameToOverrideFileMap = %s,"
               + " styleHumanizationKind = %s, humanizedVoiceNameSet = %s,"
               + " measureToTempoMap = %s, parallelTrackFilePath = '%s',"
               + " parallelTrackVolume = %4.3f, shiftOffset = %5.3f,"
               + " attenuationLevel = %5.3f)")
               % (cls.__name__,
                  configData.debuggingIsActive, configData.title,
                  configData.fileNamePrefix, configData.songComposerText,
                  configData.songYear, configData.includeFilePath,
                  configData.optionalVoiceNameToSuffixMap,
                  configData.trackNumber, configData.lyricsCountVocals,
                  configData.lyricsCountVocalsStandalone,
                  configData.lyricsCountBgVocals,
                  configData.lyricsCountBgVocalsStandalone,
                  configData.voiceNameList, configData.extractVoiceNameSet,
                  configData.midiVoiceNameList, configData.videoVoiceNameList,
                  configData.voiceNameToVoiceDataMap,
                  configData.voiceNameToOverrideFileMap,
                  configData.styleHumanizationKind,
                  configData.humanizedVoiceNameSet,
                  configData.measureToTempoMap,
                  configData.parallelTrackFilePath,
                  configData.parallelTrackVolume, configData.shiftOffset,
                  configData.attenuationLevel))


        return st

    #--------------------

    @classmethod
    def checkValidity (cls, getValueProc):
        """Checks the validity of data to be read from the configuration
           file for the song attributes"""

        Logging.trace(">>")

        checkSingleParameter("title", "STR", getValueProc, "")
        checkSingleParameter("trackNumber", "NAT", getValueProc, 0)
        checkSingleParameter("fileNamePrefix", "STR", getValueProc)
        # checkSingleParameter("includeFilePath", "RFILE", getValueProc)
        checkSingleParameter("debuggingIsActive", "BOOL", getValueProc, False)
        checkSingleParameter("lyricsCountVocals", "NAT", getValueProc)
        checkSingleParameter("lyricsCountVocalsStandalone", "NAT",
                             getValueProc)
        checkSingleParameter("lyricsCountBgVocals", "NAT", getValueProc)
        checkSingleParameter("lyricsCountBgVocalsStandalone", "NAT",
                             getValueProc)
        checkSingleParameter("styleHumanizationKind", "STR", getValueProc)
        checkSingleParameter("composerText", "STR", getValueProc, "")
        checkSingleParameter("year", "NAT", getValueProc, 2000)

        # checkSingleParameter("parallelTrackVolume")
        # checkSingleParameter("shiftOffset")
        checkSingleParameter("attenuationLevel", "FLT", getValueProc, 0.0)

        # if configData.parallelTrackFilePath != "":
        #    ValidityChecker.isReadableFile(configData.parallelTrackFilePath,
        #                                   "parallelTrackFilePath")

        # additional rules
        fileNamePrefix = getValueProc("fileNamePrefix")
        ValidityChecker.isValid(" " not in fileNamePrefix,
                                "'fileNamePrefix' must not contain blanks")
        year = getValueProc("year")
        ValidityChecker.isValid(isInRange(year, 1900, 2100),
                                "'year' must be in a reasonable range")

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, getValueProc):
        """Reads song configuration data via <getValueProc> from
           configuration file into <configData>."""

        Logging.trace(">>")

        configData.title = getValueProc("title")
        configData.trackNumber = getValueProc("trackNumber", 0)
        configData.fileNamePrefix = getValueProc("fileNamePrefix")
        configData.includeFilePath = configData.fileNamePrefix + "-music.ly"
        configData.songComposerText = getValueProc("composerText", "")
        configData.songYear = getValueProc("year", 2000)

        configData.debuggingIsActive = getValueProc("debuggingIsActive", False)
        configData.lyricsCountVocals = getValueProc("lyricsCountVocals")
        configData.lyricsCountVocalsStandalone = \
                 getValueProc("lyricsCountVocalsStandalone")
        configData.lyricsCountBgVocals = getValueProc("lyricsCountBgVocals")
        configData.lyricsCountBgVocalsStandalone = \
                 getValueProc("lyricsCountBgVocalsStandalone")
        configData.styleHumanizationKind = getValueProc("styleHumanizationKind")
        configData.attenuationLevel = getValueProc("attenuationLevel", 0.0)

        humanizedVoiceNames = getValueProc("humanizedVoicesList", "")
        tempoTrack          = getValueProc("tempoTrack")

        voiceNames      = getValueProc("voices")
        midiChannels    = getValueProc("midiChannel")
        midiInstruments = getValueProc("midiInstrument")
        midiVolumes     = getValueProc("midiVolume")
        panPositions    = getValueProc("panPosition")
        audioVolumes    = getValueProc("audioVolume")
        reverbLevels    = getValueProc("reverbLevel")
        soundVariants   = getValueProc("soundVariant")

        extractVoiceNames = getValueProc("extractVoiceList", "")
        midiVoiceNames    = getValueProc("midiVoiceList", "")
        videoVoiceNames = getValueProc("videoVoiceList")

        overrideFiles = getValueProc("overrideFiles", "")
        optionalVoiceNames = getValueProc("optionalVoices", "")
        parallelTrackInfo   = getValueProc("parallelTrack", "")

        cls._splitParallelTrackInfo(configData, parallelTrackInfo)

        configData.optionalVoiceNameToSuffixMap = \
                 cls._splitOptionalVoiceInfo(optionalVoiceNames)
        configData.voiceNameToOverrideFileMap = \
                 cls._splitOverrideInfo(overrideFiles)

        configData.midiVoiceNameList  = convertStringToList(midiVoiceNames)
        configData.videoVoiceNameList = convertStringToList(videoVoiceNames)
        configData.extractVoiceNameSet = \
          set(convertStringToList(extractVoiceNames))
        configData.humanizedVoiceNameSet = \
          set(convertStringToList(humanizedVoiceNames))

        tempoTrackLineList = convertStringToList(tempoTrack, "|")
        configData.measureToTempoMap = \
                 _TempoTrack.measureToTempoMap(tempoTrackLineList)

        cls._convertToVoiceMap(configData, voiceNames, midiChannels,
                               midiInstruments, midiVolumes, panPositions,
                               audioVolumes, reverbLevels, soundVariants)

        Logging.trace("<<: configData = %s", configData)
        
#====================

class _TempoTrack:
    """Represents tempo track with mappings from measure number to
       tempo (in beats per minute) and measure length (in quarters)."""

    _defaultMeasureLength = 4 # quarters

    #--------------------

    @classmethod
    def measureToTempoMap (cls, lineList):
        """Scans <lineList> for mappings from measure number to tempo
           and measure length indications and returns those in a map.
           Note that intermediate measures just maintain the previous
           tempo and length indication (as expected)."""

        Logging.trace(">>: %s", lineList)

        result = {}

        separator = "/"
        mappingRegexp = re.compile(r"(\w+) *-> *([\w\/]+)")
        measureLength = cls._defaultMeasureLength

        for line in lineList:
            line = line.strip(" \t\r\n")

            if line.count == 0 or line.startswith("--"):
                pass
            elif mappingRegexp.search(line):
                matchList = mappingRegexp.match(line)
                measure  = int(matchList.group(1))
                measureLengthAndTempo = matchList.group(2)
                separatorPosition = measureLengthAndTempo.find(separator)

                if separatorPosition < 0:
                    tempo = measureLengthAndTempo
                else:
                    measureLength = measureLengthAndTempo[:separatorPosition]
                    tempo = measureLengthAndTempo[separatorPosition+1:]
                    ValidityChecker.isNumberString(measureLength,
                                                   "tempo track measure length",
                                                   floatIsAllowed=True,
                                                   rangeKind=">0")
                    measureLength = float(measureLength)
                    
                ValidityChecker.isNumberString(tempo, "tempo track tempo",
                                               floatIsAllowed=True,
                                               rangeKind=">0")
                tempo = float(tempo)

                Logging.trace("--: tempo - %d -> %f/%f",
                              measure, measureLength, tempo)
                result[measure] = (tempo, measureLength)

        Logging.trace("<<: %s", repr(result))
        return result
                   
#====================

class _VideoDeviceType:
    """This class encapsulates the settings for a video device used
       for video generation."""

    #--------------------
    # EXPORTED FEATURES
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

    def __str__ (self):
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

class _VoiceDescriptor:
    """Type representing all data for generation of a single voice"""

    def __init__ (self):
        self.voiceName      = None
        self.midiChannel    = None
        self.midiInstrument = None
        self.midiVolume     = None
        self.panPosition    = None
        self.reverbLevel    = None
        self.audioVolume    = None
        self.soundVariant   = None

    #--------------------

    def __str__ (self):
        className = self.__class__.__name__
        st = (("%s("
               + "voice = %s, midiChannel = %s, midiInstrument = %s,"
               + " midiVolume = %s, panPosition = %s, reverb = %s,"
               + " audioVolume = %s, soundVariant = %s)")
               % (className,
                  self.voiceName, self.midiChannel, self.midiInstrument,
                  self.midiVolume, self.panPosition, self.reverbLevel,
                  self.audioVolume, self.soundVariant))
        return st

#====================

class MLA_ConfigurationData:
    """This class encapsulates the settings read from a configuration file like
       e.g. the global commands for ffmpeg, sox, etc. as well as file name
       templates and specifically the song configuration data."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _checkStringLists (self, voiceNames, midiChannels, midiInstruments,
                           midiVolumes, panPositions, audioVolumes,
                           reverbLevels, soundVariants):
        """Checks whether data for voice list and voice data read from
           configuration file is okay."""

        Logging.trace(">>")

        elementsInString = lambda st: len(st.strip().split(","))

        def checkForRequiredLength(st, valueName, elementCount):
            ValidityChecker.isValid(elementsInString(st) == elementCount,
                                    "'%s' must contain %d elements"
                                    % (valueName, elementCount))

        ValidityChecker.isString(voiceNames, "voiceNameList")
        ValidityChecker.isString(midiChannels, "midiChannelList")
        ValidityChecker.isString(midiInstruments, "midiInstrumentList")
        ValidityChecker.isString(midiVolumes, "midiVolumeList")
        ValidityChecker.isString(panPositions, "panPositionList")
        ValidityChecker.isString(reverbLevels, "reverbLevelList")
        ValidityChecker.isString(audioVolumes, "audioVolumeList")
        ValidityChecker.isString(soundVariants, "soundVariantList")

        voiceCount = elementsInString(voiceNames)
        checkForRequiredLength(midiChannels, "midiChannelList", voiceCount)
        checkForRequiredLength(midiInstruments, "midiInstrumentList",
                               voiceCount)
        checkForRequiredLength(midiVolumes, "midiVolumeList", voiceCount)
        checkForRequiredLength(panPositions, "panPositionList", voiceCount)
        checkForRequiredLength(audioVolumes, "audioVolumeList", voiceCount)
        checkForRequiredLength(reverbLevels, "reverbLevelList", voiceCount)
        checkForRequiredLength(soundVariants, "soundVariantList", voiceCount)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _checkValidity (cls, getValueProc):
        """Checks whether all data read from configuration file is
           okay."""

        Logging.trace(">>")

        _ConfigDataGlobal.checkValidity(getValueProc)
        _ConfigDataAlbum.checkValidity(getValueProc)
        _ConfigDataSong.checkValidity(getValueProc)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        _ConfigDataGlobal.initialize(self)
        _ConfigDataAlbum.initialize(self)
        _ConfigDataSong.initialize(self)

    #--------------------

    def __str__ (self):
        """Returns the string representation of <self>"""

        className = self.__class__.__name__
        st = (("%s(%s, %s, %s)")
              % (className,
                 _ConfigDataGlobal.toString(self),
                 _ConfigDataAlbum.toString(self),
                 _ConfigDataSong.toString(self)))

        return st

    #--------------------

    def readFile (self, configurationFilePath, selectedVoiceNameSet):
        """Reads data from configuration file with <configurationFilePath>
           into <self>; <selectedVoiceNameList> gives the set of voices
           selected for processing"""

        Logging.trace(">>: '%s'", configurationFilePath)

        cls = self.__class__
        separator = OperatingSystem.pathSeparator
        scriptFilePath = OperatingSystem.scriptFilePath()
        scriptDirectoryPath = OperatingSystem.dirname(scriptFilePath)
        configSuffix = separator + "config"
        searchPathList = \
          [ OperatingSystem.homeDirectoryPath() + separator + ".ltbvc",
            scriptDirectoryPath + configSuffix,
            OperatingSystem.dirname(scriptDirectoryPath) + configSuffix ]
        ConfigurationFile.setSearchPaths(searchPathList)
        configurationFile = ConfigurationFile(configurationFilePath)
        getValueProc = configurationFile.getValue

        cls._checkValidity(getValueProc)
        
        _ConfigDataGlobal.read(self, getValueProc)
        _ConfigDataAlbum.read(self, getValueProc)
        _ConfigDataSong.read(self, getValueProc)

        if len(self.extractVoiceNameSet) == 0:
            self.extractVoiceNameSet.update(self.voiceNameList)

        if len(self.midiVoiceNameList) == 0:
            self.midiVoiceNameList = list(self.voiceNameList)

        if len(self.videoVoiceNameList) == 0:
            self.videoVoiceNameList = list(self.voiceNameList)

        if len(selectedVoiceNameSet) == 0:
            # when no voices are selected so far, all voices will be
            # used
            selectedVoiceNameSet.update(self.voiceNameList)
            
        Logging.trace("<<: '%s'", self)
