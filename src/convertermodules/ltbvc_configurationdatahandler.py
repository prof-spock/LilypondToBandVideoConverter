# -*- coding: utf-8-unix -*-
# ltbvc_configurationdatahandler -- services for access to the global
#                                   configuration file of ltbvc
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

import datetime
import re

from configurationfile import ConfigurationFile
from operatingsystem import OperatingSystem
from ltbvc_businesstypes import generateObjectListFromString, \
                                generateObjectMapFromString, \
                                AudioTrack, TempoTrack, \
                                VideoFileKind, VideoTarget, VoiceDescriptor
from regexppattern import RegExpPattern
from simplelogging import Logging
from ttbase import convertStringToList, convertStringToMap, iif, isInRange
from validitychecker import ValidityChecker

#====================

def _checkVariableList (variableNameList, configurationFile):
    """Checks all variables in <variableNameList> to be read from
       <configurationFile>"""

    for variableName in variableNameList:
        _LocalValidator.check(variableName, configurationFile.getValue)

#--------------------

def _getStylesWithNamePrefix (prefix, configurationFile):
    """Returns list of names of styles having <prefix> in
       <configurationFile>"""

    Logging.trace(">>")

    allVariables = configurationFile.getKeySet()
    result = [x for x in allVariables if x.startswith(prefix)]

    Logging.trace("<<: %s", result)
    return result

#--------------------

def _readStylesWithPrefix (prefix, configurationFile):
    """Reads all styles with name <prefix> from <configurationFile>
       and returns them as map"""

    Logging.trace(">>")

    styleNameList = _getStylesWithNamePrefix(prefix, configurationFile)
    result = {}

    for styleName in styleNameList:
        style = configurationFile.getValue(styleName)
        result[styleName] = style

    Logging.trace("<<: %s", result)
    return result

#====================
# TYPE DEFINITIONS
#====================

class _ConfigDataGlobal:
    """Represents all configuration data that is global e.g. the
       command paths for generation. Note that this categorization is
       just for systematics, any configuration variable can be set per
       song."""

    _soundStyleNamePrefix = "soundStyle"

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes global attributes of <configData>"""

        configData.aacCommandLine                = "aac"
        configData.ffmpegCommand                 = "ffmpeg"
        configData.fluidsynthCommand             = "fluidsynth"
        configData.intermediateFileDirectoryPath = "."
        configData.lilypondCommand               = "lilypond"
        configData.loggingFilePath               = ("C:/temp/logs"
                                                   + "/makeLilypondAll.log")
        configData.mp4boxCommand                 = "mp4box"
        configData.soundFontDirectoryPath        = "C:/temp/soundfonts"
        configData.soundFontNameList             = ""
        configData.soundStyleNameToTextMap       = {}
        configData.soxCommandLinePrefix          = "sox"
        configData.targetDirectoryPath           = "generated"
        configData.tempAudioDirectoryPath        = "/temp"
        configData.tempLilypondFilePath          = "./temp.ly"
        configData.videoTargetMap                = {}
        configData.videoFileKindMap              = {}

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the global attributes
           of <configData>"""

        className = cls.__name__
        st = (("%s("
               + "aacCommandLine = '%s', ffmpegCommand = '%s',"
               + " fluidsynthCommand = '%s',"
               + " intermediateFileDirectoryPath = %s,"
               + " lilypondCommand = '%s', mp4boxCommand = '%s',"
               + " loggingFilePath = '%s',"
               + " soundFontDirectoryPath = '%s', soundFontNameList = %s,"
               + " soundStyleNameToTextMap = %s,"
               + " soxCommandLinePrefix = '%s',"
               + " targetDirectoryPath = '%s', tempAudioDirectoryPath = '%s',"
               + " tempLilypondFilePath = '%s', videoTargetMap = %s,"
               + " videoFileKindMap = %s)")
              % (className,
                 configData.aacCommandLine, configData.ffmpegCommand,
                 configData.fluidsynthCommand,
                 configData.intermediateFileDirectoryPath,
                 configData.lilypondCommand, configData.mp4boxCommand,
                 configData.loggingFilePath,
                 configData.soundFontDirectoryPath,
                 configData.soundFontNameList,
                 configData.soundStyleNameToTextMap,
                 configData.soxCommandLinePrefix,
                 configData.targetDirectoryPath,
                 configData.tempAudioDirectoryPath,
                 configData.tempLilypondFilePath,
                 configData.videoTargetMap, configData.videoFileKindMap))
        return st

    #--------------------

    @classmethod
    def checkValidity (cls, configurationFile):
        """Checks the validity of data to be read from
           <configurationFile> for the global attributes"""

        Logging.trace(">>")

        styleNamePrefix = cls._soundStyleNamePrefix
        soundStyleNameList = _getStylesWithNamePrefix(styleNamePrefix,
                                                      configurationFile)

        for styleName in soundStyleNameList:
            _LocalValidator.check(styleName, configurationFile.getValue,
                                  styleNamePrefix + "*")

        variableNameList = \
            [ "aacCommandLine", "ffmpegCommand", "fluidsynthCommand",
              "intermediateFileDirectoryPath", "lilypondCommand",
              "loggingFilePath", "mp4boxCommand",
              "soundFontDirectoryPath", "soxCommandLinePrefix",
              "targetDirectoryPath", "tempAudioDirectoryPath",
              "tempLilypondFilePath", "videoTargetMap",
              "videoFileKindMap" ]
        _checkVariableList(variableNameList, configurationFile)

        # additional checks
        for variableName in ["aacCommandLine", "soxCommandLinePrefix"]:
            commandLine = _LocalValidator.get(variableName,
                                              configurationFile.getValue)
            command = commandLine.split()[0]
            ValidityChecker.isReadableFile(command, variableName)
        
        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads global configuration data from <configurationFile>
           into <configData>."""

        Logging.trace(">>")

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        configData.aacCommandLine = getValueProc("aacCommandLine")
        configData.ffmpegCommand = getValueProc("ffmpegCommand")
        configData.fluidsynthCommand = getValueProc("fluidsynthCommand")
        configData.intermediateFileDirectoryPath = \
            getValueProc("intermediateFileDirectoryPath")
        configData.lilypondCommand = getValueProc("lilypondCommand")
        configData.loggingFilePath = getValueProc("loggingFilePath")
        configData.mp4boxCommand = getValueProc("mp4boxCommand")
        configData.soundFontDirectoryPath = \
            getValueProc("soundFontDirectoryPath")
        configData.soundFontNameList = \
            convertStringToList(getValueProc("soundFontNames"))
        configData.soxCommandLinePrefix = getValueProc("soxCommandLinePrefix")
        configData.targetDirectoryPath = \
            getValueProc("targetDirectoryPath")
        configData.tempLilypondFilePath = \
            getValueProc("tempLilypondFilePath")
        configData.tempAudioDirectoryPath = \
            getValueProc("tempAudioDirectoryPath")
        videoTargetMap = getValueProc("videoTargetMap")
        configData.videoTargetMap = \
            generateObjectMapFromString(videoTargetMap, VideoTarget())
        videoFileKindMap = getValueProc("videoFileKindMap")
        configData.videoFileKindMap = \
            generateObjectMapFromString(videoFileKindMap, VideoFileKind())

        configData.soundStyleNameToTextMap = \
            _readStylesWithPrefix(cls._soundStyleNamePrefix,
                                  configurationFile)

        Logging.trace("<<")

#====================

class _ConfigDataMidiHumanization:
    """Represents all configuration data that covers the MIDI
       humanization; single variable is a mapping from humanization
       style name to humanization style text"""

    _humanizationStyleNamePrefix = "humanizationStyle"

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes midi humanization attributes of <configData>"""

        configData.humanizationStyleNameToTextMap = {}
        configData.humanizedVoiceNameSet          = set()
        configData.voiceNameToVariationFactorMap  = {}

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the midi humanization
           attributes of <configData>"""

        className = cls.__name__
        st = (("%s("
               + "humanizationStyleNameToTextMap = %s,"
               + " humanizedVoiceNameSet = %s,"
               + " voiceNameToVariationFactorMap = %s)")
              % (className,
                 configData.humanizationStyleNameToTextMap,
                 configData.humanizedVoiceNameSet,
                 configData.voiceNameToVariationFactorMap))
        return st

    #--------------------

    @classmethod
    def checkValidity (cls, configurationFile):
        """Checks the validity of data to be read from
           <configurationFile> for the midi humanization attributes"""

        Logging.trace(">>")

        styleNamePrefix = cls._humanizationStyleNamePrefix
        humanizationStyleNameList = \
            _getStylesWithNamePrefix(styleNamePrefix, configurationFile)

        for styleName in humanizationStyleNameList:
            _LocalValidator.check(styleName, configurationFile.getValue,
                                  styleNamePrefix + "*")

        variableNameList = \
            [ "voiceNameToVariationFactorMap", "humanizedVoiceNameSet" ]
        _checkVariableList(variableNameList, configurationFile)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads midi humanization configuration data from
           <configurationFile> into <configData>."""

        Logging.trace(">>")

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        vntvfMap = {}
        tempMap = convertStringToMap(
                      getValueProc("voiceNameToVariationFactorMap"))

        for voiceName, factors in tempMap.items():
            scalingFactors = list(map(lambda x: float(x), factors.split("/")))
            vntvfMap[voiceName] = scalingFactors

        configData.voiceNameToVariationFactorMap = vntvfMap
        configData.humanizedVoiceNameSet = \
            set(convertStringToList(getValueProc("humanizedVoiceNameSet")))
        configData.humanizationStyleNameToTextMap = \
            _readStylesWithPrefix(cls._humanizationStyleNamePrefix,
                                  configurationFile)

        Logging.trace("<<")

#====================

class _ConfigDataNotation:
    """Represents all configuration data that refers to the notation:
       this is the map from phase and voice name to the staff kind and
       the map from phase and voice name to the clef."""

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes notation attributes of <configData>"""

        configData.voiceNameToScoreNameMap         = {}
        configData.phaseAndVoiceNameToClefMap      = {}
        configData.phaseAndVoiceNameToStaffListMap = {}

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the notation
           attributes of <configData>"""

        className = cls.__name__
        st = (("%s("
               + "voiceNameToScoreNameMap = %s,"
               + " phaseAndVoiceNameToClefMap = %s,"
               + " phaseAndVoiceNameToStaffListMap = %s)")
              % (className,
                 configData.voiceNameToScoreNameMap,
                 configData.phaseAndVoiceNameToClefMap,
                 configData.phaseAndVoiceNameToStaffListMap))
        return st

    #--------------------

    @classmethod
    def checkValidity (cls, configurationFile):
        """Checks the validity of data to be read from
           <configurationFile> for the notation attributes"""

        Logging.trace(">>")

        variableNameList = \
          [ "voiceNameToScoreNameMap", "phaseAndVoiceNameToClefMap",
            "phaseAndVoiceNameToStaffListMap" ]

        _checkVariableList(variableNameList, configurationFile)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads notation configuration data from <configurationFile>
           into <configData>."""

        Logging.trace(">>")

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        configData.voiceNameToScoreNameMap = \
            convertStringToMap(getValueProc("voiceNameToScoreNameMap"))
        configData.phaseAndVoiceNameToClefMap = \
            convertStringToMap(getValueProc("phaseAndVoiceNameToClefMap"))
        pAVnToStaffListMap = \
            convertStringToMap(getValueProc("phaseAndVoiceNameToStaffListMap"))

        for phase, voiceNameToStaffListMap in pAVnToStaffListMap.items():
            updatedMap = {}

            for voiceName, staffListString in voiceNameToStaffListMap.items():
                staffList = convertStringToList(staffListString, "/")
                updatedMap[voiceName] = staffList

            pAVnToStaffListMap[phase] = updatedMap
                
        configData.phaseAndVoiceNameToStaffListMap = pAVnToStaffListMap

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
                            midiVolumes, panPositions, audioLevels,
                            reverbLevels, soundVariants):
        """Converts strings read from configuration file to voice name
           list and map to voice descriptors"""

        Logging.trace(">>")

        configData.voiceNameList = convertStringToList(voiceNames)

        midiChannelList    = convertStringToList(midiChannels, kind="I")
        midiInstrumentList = convertStringToList(midiInstruments)
        midiVolumeList     = convertStringToList(midiVolumes, kind="I")
        panPositionList    = convertStringToList(panPositions)
        audioLevelList     = convertStringToList(audioLevels, kind="F")
        reverbLevelList    = convertStringToList(reverbLevels, kind="F")
        soundVariantList   = convertStringToList(soundVariants)

        configData.voiceNameToVoiceDataMap = {}

        for i in range(len(configData.voiceNameList)):
            voiceDescriptor = VoiceDescriptor()
            voiceName = configData.voiceNameList[i]
            voiceDescriptor.voiceName      = voiceName
            voiceDescriptor.midiChannel    = midiChannelList[i]
            voiceDescriptor.midiInstrument = midiInstrumentList[i]
            voiceDescriptor.midiVolume     = midiVolumeList[i]
            voiceDescriptor.panPosition    = panPositionList[i]
            voiceDescriptor.audioLevel     = audioLevelList[i]
            voiceDescriptor.reverbLevel    = reverbLevelList[i]
            voiceDescriptor.soundVariant   = soundVariantList[i]
            configData.voiceNameToVoiceDataMap[voiceName] = voiceDescriptor

        Logging.trace("<<: %s", configData.voiceNameToVoiceDataMap)

    #--------------------

    @classmethod
    def _convertTargetMapping (cls, mapAsString, isLyricsMap):
        """Prepares a map from voice name to lyrics or chord data
           (depending on <isLyricsMap>) based on data in
           <mapAsString>; voice names for lyrics map to a mapping from
           target to lyrics line count, voice names for chords map to
           sets of targets"""

        Logging.trace(">>: map = '%s', isLyrics = %s",
                      mapAsString, isLyricsMap)

        targetAbbrevToNameMap = { "e": "extract", "m": "midi",
                                  "s": "score",   "v": "video" }
        result = {}
        map = convertStringToMap(mapAsString)

        for voiceName, value in map.items():
            entry = iif(isLyricsMap, {}, set())
            targetList = value.split("/")
            Logging.trace("--: targetList(%s) = %s", voiceName, targetList)

            for targetSpec in targetList:
                targetSpec = targetSpec.strip()

                if len(targetSpec) > 0:
                    target, rest = targetSpec[0], targetSpec[1:]
                    Logging.trace("--: target = %s", target)

                    if target in "emsv":
                        target = targetAbbrevToNameMap[target]

                        if not isLyricsMap:
                            entry.update([ target ])
                        else:
                            if rest == "":
                                rest = "1"

                            entry[target] = int(rest)

            result[voiceName] = entry

        Logging.trace("<<: %s", result)
        return result

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
            partList = parallelTrackInfo.split(",")

        if len(partList) == 1:
            partList.append(str(defaultVolume))

        if len(partList) == 2:
            partList.append(str(defaultOffset))

        configData.parallelTrackFilePath = partList[0].strip()
        configData.parallelTrackVolume   = float(partList[1])
        configData.shiftOffset           = float(partList[2])

        Logging.trace("<<: %s", partList)

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes song related attributes of <configData>"""

        configData.intermediateFilesAreKept          = False
        configData.optionalVoiceNameToSuffixMap      = {}
        configData.title                             = "%title%"
        configData.songComposerText                  = None
        configData.songYear                          = None
        configData.trackNumber                       = 0
        configData.countInMeasureCount               = 0
        configData.fileNamePrefix                    = "XXXX"
        configData.includeFilePath                   = "%includeFilePath%"
        configData.voiceNameToLyricsMap              = {}
        configData.voiceNameToChordsMap              = {}
        configData.measureToHumanizationStyleNameMap = None
        configData.voiceNameList                     = ""
        configData.extractVoiceNameSet               = set()
        configData.scoreVoiceNameList                = ""
        configData.midiVoiceNameList                 = ""
        configData.audioVoiceNameSet                 = set()
        configData.voiceNameToVoiceDataMap           = {}
        configData.voiceNameToOverrideFileNameMap    = {}
        configData.parallelTrackFilePath             = ""
        configData.parallelTrackVolume               = 1.0
        configData.shiftOffset                       = None
        configData.measureToTempoMap                 = None
        configData.attenuationLevel                  = 0

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the song related
           attributes of <configData>"""

        st = (("%s("
               + " intermediateFilesAreKept = %s, title = '%s',"
	       + " fileNamePrefix = %s, songComposerText = '%s',"
               + " songYear = %d, includeFilePath = '%s',"
               + " optionalVoiceNameToSuffixMap = %s, trackNumber = %d,"
               + " countInMeasureCount = %d,"
               + " voiceNameToChordsMap = %s, voiceNameToLyricsMap = %s,"
               + " voiceNameList = %s, extractVoiceNameSet = %s,"
               + " midiVoiceNameList = %s,  scoreVoiceNameList = %s,"
               + " audioVoiceNameSet = %s,"
               + " voiceNameToVoiceDataMap = %s,"
               + " voiceNameToOverrideFileNameMap = %s,"
               + " measureToHumanizationStyleNameMap = %s,"
               + " measureToTempoMap = %s, parallelTrackFilePath = '%s',"
               + " parallelTrackVolume = %4.3f, shiftOffset = %5.3f,"
               + " attenuationLevel = %5.3f)")
               % (cls.__name__,
                  configData.intermediateFilesAreKept, configData.title,
                  configData.fileNamePrefix, configData.songComposerText,
                  configData.songYear, configData.includeFilePath,
                  configData.optionalVoiceNameToSuffixMap,
                  configData.trackNumber, configData.countInMeasureCount,
                  configData.voiceNameToChordsMap,
                  configData.voiceNameToLyricsMap,
                  configData.voiceNameList, configData.extractVoiceNameSet,
                  configData.midiVoiceNameList, configData.scoreVoiceNameList,
                  configData.audioVoiceNameSet,
                  configData.voiceNameToVoiceDataMap,
                  configData.voiceNameToOverrideFileNameMap,
                  configData.measureToHumanizationStyleNameMap,
                  configData.measureToTempoMap,
                  configData.parallelTrackFilePath,
                  configData.parallelTrackVolume, configData.shiftOffset,
                  configData.attenuationLevel))

        return st

    #--------------------

    @classmethod
    def checkValidity (cls, configurationFile):
        """Checks the validity of data to be read from
           <configurationFile> for the song attributes"""

        Logging.trace(">>")

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        variableNameList = \
          [ "title", "trackNumber", "countInMeasureCount", "fileNamePrefix",
            "intermediateFilesAreKept", "measureToHumanizationStyleNameMap",
            "composerText", "year", "voiceNameList",
            "midiChannelList", "midiInstrumentList", "midiVolumeList",
            "panPositionList", "audioLevelList", "reverbLevelList",
            "soundVariantList", "attenuationLevel" ]

        _checkVariableList(variableNameList, configurationFile)

        #("includeFilePath", "RFILE")
        # "parallelTrackVolume")
        # "shiftOffset")

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
    def read (cls, configData, configurationFile):
        """Reads song configuration data from <configurationFile> into
           <configData>."""

        Logging.trace(">>")

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        configData.title = getValueProc("title")
        configData.trackNumber = getValueProc("trackNumber")
        configData.countInMeasureCount = getValueProc("countInMeasureCount")
        configData.fileNamePrefix = getValueProc("fileNamePrefix")
        configData.includeFilePath = configData.fileNamePrefix + "-music.ly"
        configData.songComposerText = getValueProc("composerText")
        configData.songYear = getValueProc("year")
        configData.intermediateFilesAreKept = \
                              getValueProc("intermediateFilesAreKept")
        configData.attenuationLevel = getValueProc("attenuationLevel")

        tempoTrack          = getValueProc("measureToTempoMap")

        voiceNames      = getValueProc("voiceNameList")
        midiChannels    = getValueProc("midiChannelList")
        midiInstruments = getValueProc("midiInstrumentList")
        midiVolumes     = getValueProc("midiVolumeList")
        panPositions    = getValueProc("panPositionList")
        audioLevels     = getValueProc("audioLevelList")
        reverbLevels    = getValueProc("reverbLevelList")
        soundVariants   = getValueProc("soundVariantList")

        audioVoiceNames   = getValueProc("audioVoiceNameSet")
        extractVoiceNames = getValueProc("extractVoiceNameSet")
        midiVoiceNames    = getValueProc("midiVoiceNameList")
        scoreVoiceNames   = getValueProc("scoreVoiceNameList")

        voiceNameToLyricsMap = getValueProc("voiceNameToLyricsMap")
        voiceNameToChordsMap = getValueProc("voiceNameToChordsMap")

        overrideFiles      = \
          getValueProc("voiceNameToOverrideFileNameMap")
        optionalVoiceNames = getValueProc("optionalVoices")
        parallelTrackInfo  = getValueProc("parallelTrack")

        cls._splitParallelTrackInfo(configData, parallelTrackInfo)

        configData.voiceNameToOverrideFileNameMap = \
                 convertStringToMap(overrideFiles)
        configData.voiceNameToLyricsMap = \
          cls._convertTargetMapping(voiceNameToLyricsMap, True)
        configData.voiceNameToChordsMap = \
          cls._convertTargetMapping(voiceNameToChordsMap, False)

        configData.audioVoiceNameSet = \
          set(convertStringToList(audioVoiceNames))
        configData.extractVoiceNameSet = \
          set(convertStringToList(extractVoiceNames))
        configData.midiVoiceNameList  = convertStringToList(midiVoiceNames)
        configData.scoreVoiceNameList = convertStringToList(scoreVoiceNames)

        tempoTrackMap = convertStringToMap(tempoTrack)
        configData.measureToTempoMap = \
                 TempoTrack.measureToTempoMap(tempoTrackMap)
        measureToStyleMap = getValueProc("measureToHumanizationStyleNameMap")
        configData.measureToHumanizationStyleNameMap = \
            convertStringToMap(measureToStyleMap)

        cls._convertToVoiceMap(configData, voiceNames, midiChannels,
                               midiInstruments, midiVolumes, panPositions,
                               audioLevels, reverbLevels, soundVariants)

        Logging.trace("<<: configData = %s", configData)

#====================

class _ConfigDataSongGroup:
    """Represents all configuration data that is considered to be
       related to group of songs like e.g. the name of an album or the
       artist for generation. Note that this categorization is
       just for systematics, any configuration variable can be set per
       song."""

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes song group related attributes of
           <configData>"""

        configData.targetFileNamePrefix            = None
        configData.artistName                      = None
        configData.albumName                       = None
        configData.albumArtFilePath                = None
        configData.audioTargetDirectoryPath        = None
        configData.audioGroupNameToVoiceNameSetMap = None
        configData.audioTrackList                  = None

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the song
           group related attributes of <configData>"""

        st = (("%s("
               + "albumArtFilePath = '%s', albumName = '%s',"
               + " artistName = '%s', audioTargetDirectoryPath = '%s',"
               + " targetFileNamePrefix = %s,"
               + " audioGroupNameToVoiceNameSetMap = %s,"
               + " audioTrackList = %s)")
              % (cls.__name__,
                 configData.albumArtFilePath, configData.albumName,
                 configData.artistName, configData.audioTargetDirectoryPath,
                 configData.targetFileNamePrefix,
                 configData.audioGroupNameToVoiceNameSetMap,
                 configData.audioTrackList))

        return st

    #--------------------

    @classmethod
    def checkValidity (cls, configurationFile):
        """Checks the validity of data to be read from
           <configurationFile> for the song group attributes"""

        Logging.trace(">>")

        variableNameList = \
          [ "albumName", "albumArtFilePath", "artistName",
            "audioTargetDirectoryPath", "targetFileNamePrefix",
            "audioGroupToVoicesMap", "audioTrackList" ]
        _checkVariableList(variableNameList, configurationFile)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads song group configuration data from <configurationFile>
           into <configData>."""

        Logging.trace(">>")

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        configData.albumName = getValueProc("albumName")
        configData.artistName = getValueProc("artistName")
        configData.audioTargetDirectoryPath = \
            getValueProc("audioTargetDirectoryPath")
        configData.targetFileNamePrefix = \
            getValueProc("targetFileNamePrefix")
        audioGroupToVoices = getValueProc("audioGroupToVoicesMap")
        audioTrackList = getValueProc("audioTrackList")

        audioGroupToVoicesMap = convertStringToMap(audioGroupToVoices)

        for audioGroupName in audioGroupToVoicesMap.keys():
            st = audioGroupToVoicesMap[audioGroupName]
            voiceNameSet = set(convertStringToList(st, "/"))
            audioGroupToVoicesMap[audioGroupName] = voiceNameSet

        configData.audioGroupNameToVoiceNameSetMap = audioGroupToVoicesMap

        configData.audioTrackList = \
            generateObjectListFromString(audioTrackList, AudioTrack())

        Logging.trace("<<")

#====================

class _LocalValidator:
    """Encapsulates routines for validation of the configuration
       file variables."""

    _map = {}

    #--------------------
    # LOCAL ROUTINES
    #--------------------

    @classmethod
    def _setMap (cls, name, defaultValue, kind, regExp=None):
        """Sets a single entry in internal validation map for configuration
           variable with <name>, having default <defaultValue> and with type
           <kind>; if <kind> is 'REGEXP', the additional parameter <regExp>
           gives the validation regexp"""

        st = ("--" if regExp is None else regExp.pattern)
        Logging.trace(">>: name = %s, default = %s, kind = %s, regExp = %s",
                      name, defaultValue, kind, st)

        cls._map[name] = { "defaultValue" : defaultValue,
                           "kind"         : kind,
                           "regExp"       : regExp }

        Logging.trace("<<")

    #--------------------
    # EXPORTED ROUTINES
    #--------------------

    @classmethod
    def initialize (cls):
        """Sets up internal map for all configuration variables"""

        # abbreviations for pattern functions
        makeCompactListPat = RegExpPattern.makeCompactListPattern
        makeListPat        = RegExpPattern.makeListPattern
        makeMapPat         = RegExpPattern.makeMapPattern
        makeRegExp         = RegExpPattern.makeRegExp

        # common element patterns
        noCommaPattern    = r"(?:'[^']*'|[^,'\s]+)"

        identifierPattern = RegExpPattern.identifierPattern
        integerPattern    = RegExpPattern.integerPattern
        floatPattern      = RegExpPattern.floatPattern

        # special element patterns
        beatPattern = r"(?:[1-8]|OTHER|SLACK|S)"
        clefPattern = makeCompactListPat(r"(?:bass_8|G_8|bass|G|'')")
        humanizationPattern = r"[BA]?\d+(\.\d+)?"
        parallelTrackPattern = (r"[^,\s]+(?:,\s*%s\s*(?:,\s*%s\s*))"
                                % (floatPattern, floatPattern))
        prephasePattern = r"(?:extract|midi|score|video)"
        staffListPattern = makeCompactListPat("(?:DrumStaff|PianoStaff"
                                              + "|Staff|TabStaff)")
        # simple map patterns
        idToTextMapPattern = makeMapPat(identifierPattern, noCommaPattern)

        # regular expressions for lists of standard elements
        floatListRegExp = makeRegExp(makeListPat(floatPattern, False))
        identifierListRegExp = makeRegExp(makeListPat(identifierPattern,
                                                      False))
        instrumentListRegExp = makeRegExp(makeListPat(r"\d+(:\d+)?", False))
        integerListRegExp = makeRegExp(makeListPat(integerPattern, False))

        # commands
        cls._setMap("aacCommandLine", "", "STRING")
        cls._setMap("ffmpegCommand", None, "EXECUTABLE")
        cls._setMap("fluidsynthCommand", None, "EXECUTABLE")
        cls._setMap("mp4boxCommand", "", "EXECUTABLE")
        cls._setMap("soxCommandLinePrefix", None, "STRING")

        # file paths
        cls._setMap("intermediateFileDirectoryPath", ".", "WDIRECTORY")
        cls._setMap("loggingFilePath", None, "WFILE")
        cls._setMap("targetDirectoryPath", None, "WDIRECTORY")
        cls._setMap("tempLilypondFilePath", "temp.ly", "WFILE")

        # song group properties
        cls._setMap("artistName", u"[ARTIST]", "STRING")
        cls._setMap("albumName", u"[ALBUM]", "STRING")

        # general song properties
        cls._setMap("title", None, "STRING")
        cls._setMap("fileNamePrefix", None, "STRING")
        cls._setMap("year", datetime.date.today().year, "NATURAL")
        cls._setMap("composerText", u"[COMPOSERTEXT]", "STRING")
        cls._setMap("trackNumber", 1, "NATURAL")
        cls._setMap("countInMeasureCount", 0, "NATURAL")
        cls._setMap("intermediateFilesAreKept", False, "BOOLEAN")
        cls._setMap("voiceNameList", None, "REGEXP", identifierListRegExp)

        cls._setMap("measureToTempoMap", None, "REGEXP",
                    makeRegExp(makeMapPat(floatPattern, integerPattern,
                                          False)))
        cls._setMap("phaseAndVoiceNameToClefMap", "{}", "REGEXP",
                    makeRegExp(makeMapPat(prephasePattern,
                                          makeMapPat(identifierPattern,
                                                     clefPattern))))
        cls._setMap("phaseAndVoiceNameToStaffListMap", "{}", "REGEXP",
                    makeRegExp(makeMapPat(prephasePattern,
                                          makeMapPat(identifierPattern,
                                                     staffListPattern))))

        # extract and score generation
        cls._setMap("extractVoiceNameSet", "", "REGEXP", identifierListRegExp)
        cls._setMap("lyricsVoiceMap", "{}", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          makeCompactListPat(r"[esv]\d*"))))

        cls._setMap("scoreVoiceNameList", "", "REGEXP", identifierListRegExp)
        cls._setMap("voiceNameToScoreNameMap", "", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          identifierPattern)))

        # midi generation
        cls._setMap("humanizedVoiceNameSet", "", "REGEXP",
                    identifierListRegExp)
        cls._setMap("humanizationStyle*", None, "REGEXP",
                    makeRegExp(makeMapPat(r"(?:timing|velocity)",
                                          "(?:"
                                          + makeMapPat(beatPattern,
                                                       humanizationPattern,
                                                       False)
                                          + ")", False)))
        cls._setMap("measureToHumanizationStyleNameMap", "{}", "REGEXP",
                    makeRegExp(makeMapPat(integerPattern,
                                          identifierPattern)))
        cls._setMap("midiChannelList", "", "REGEXP", integerListRegExp)
        cls._setMap("midiInstrumentList", "", "REGEXP", instrumentListRegExp)
        cls._setMap("midiPanList", "", "REGEXP",
                    makeRegExp(makeListPat(r"C|\d+(\.\d+)[RL]", False)))
        cls._setMap("midiVoiceNameList", "", "REGEXP", identifierListRegExp)
        cls._setMap("midiVolumeList", "", "REGEXP", integerListRegExp)
        cls._setMap("voiceNameToVariationFactorMap", "", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          floatPattern + "/" + floatPattern)))

        # audio file generation
        cls._setMap("attenuationLevel", 0.0, "FLOAT")
        cls._setMap("audioGroupToVoicesMap", "{}", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          makeCompactListPat(identifierPattern),
                                          False)))
        cls._setMap("audioLevelList", "", "REGEXP", floatListRegExp)
        cls._setMap("audioTargetDirectoryPath", None, "WDIRECTORY")
        cls._setMap("audioTrackList", "", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          AudioTrack.regexpPattern(),
                                          False)))
        cls._setMap("audioVoiceNameSet", "", "REGEXP", identifierListRegExp)
        cls._setMap("parallelTrack", "", "REGEXP",
                    makeRegExp(parallelTrackPattern))
        cls._setMap("reverbLevelList", "", "REGEXP", floatListRegExp)
        cls._setMap("soundFontDirectoryPath", None, "RDIRECTORY")
        cls._setMap("soundFontNames", None, "STRING")
        cls._setMap("soundStyle*", None, "STRING")
        cls._setMap("soundVariantList", "", "REGEXP", identifierListRegExp)
        cls._setMap("tempAudioDirectoryPath", None, "WDIRECTORY")
        cls._setMap("voiceNameToOverrideFileNameMap", "{}", "REGEXP",
                    makeRegExp(idToTextMapPattern))

        # video file generation
        cls._setMap("videoTargetMap", None, "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          VideoTarget.regexpPattern(),
                                          False)))
        cls._setMap("videoFileKindMap", None, "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          VideoFileKind.regexpPattern(),
                                          False)))

    #--------------------

    @classmethod
    def check (cls, parameterName, getValueProc, checkedName=None):
        """Checks whether value for <parameterName> gained by
           <getValueProc> is okay by looking up in internal map; if
           <checkedName> is set, the syntax of that name is used
           instead"""

        Logging.trace(">>: parameterName = %s, checkedName = %s",
                      parameterName, checkedName)
        effectiveName = iif(checkedName is None, parameterName, checkedName)

        if effectiveName not in cls._map:
            # no check found => fine
            Logging.trace("--: no check")
        else:
            entry = cls._map[effectiveName]
            kind         = entry["kind"]
            defaultValue = entry["defaultValue"]
            value = getValueProc(parameterName, defaultValue)

            if kind == "STRING":
                ValidityChecker.isString(value, parameterName)
            elif kind == "NATURAL":
                ValidityChecker.isNatural(value, parameterName)
            elif kind == "BOOLEAN":
                ValidityChecker.isBoolean(value, parameterName)
            elif kind == "FLOAT":
                ValidityChecker.isFloat(value, parameterName)
            elif kind == "REGEXP":
                regExp = entry["regExp"]
                Logging.trace("--: %s", regExp.pattern)
                errorMessage = "'%s' has a bad syntax" % parameterName
                ValidityChecker.isValid(regExp.match(value) is not None,
                                        errorMessage)
            elif value == "":
                pass
            elif kind in [ "RDIRECTORY", "WDIRECTORY" ]:
                ValidityChecker.isDirectory(value, parameterName)
            elif kind in [ "RFILE", "EXECUTABLE" ]:
                ValidityChecker.isReadableFile(value, parameterName)
            elif kind == "WFILE":
                ValidityChecker.isWritableFile(value, parameterName)
            else:
                Logging.trace("--: no check, unknown kind '%s'", kind)

    #--------------------

    @classmethod
    def get (cls, name, getValueProc):
        """Gets value for <name> gained by <getValueProc> providing
           default value from internal map (if any); assumes that
           correctness check has been done before"""

        Logging.trace(">>:%s", name)

        if name not in cls._map:
            result = getValueProc(name)
        else:
            entry = cls._map[name]
            defaultValue = entry["defaultValue"]
            result = getValueProc(name, defaultValue)

        Logging.trace("<<:%s", result)
        return result

#====================

class LTBVC_ConfigurationData:
    """This class encapsulates the settings read from a configuration
       file like e.g. the global commands for ffmpeg, sox, etc. as
       well as file name templates and specifically the song
       configuration data."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _checkStringLists (self, voiceNames, midiChannels, midiInstruments,
                           midiVolumes, panPositions, audioLevels,
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
        ValidityChecker.isString(audioLevels, "audioLevelList")
        ValidityChecker.isString(soundVariants, "soundVariantList")

        voiceCount = elementsInString(voiceNames)
        checkForRequiredLength(midiChannels, "midiChannelList", voiceCount)
        checkForRequiredLength(midiInstruments, "midiInstrumentList",
                               voiceCount)
        checkForRequiredLength(midiVolumes, "midiVolumeList", voiceCount)
        checkForRequiredLength(panPositions, "panPositionList", voiceCount)
        checkForRequiredLength(audioLevels, "audioLevelList", voiceCount)
        checkForRequiredLength(reverbLevels, "reverbLevelList", voiceCount)
        checkForRequiredLength(soundVariants, "soundVariantList", voiceCount)

        Logging.trace("<<")

    #--------------------

    def _checkValidity (self):
        """Checks whether all data read from configuration file is
           okay."""

        Logging.trace(">>")

        configurationFile = self._configurationFile
        _ConfigDataGlobal.checkValidity(configurationFile)
        _ConfigDataNotation.checkValidity(configurationFile)
        _ConfigDataMidiHumanization.checkValidity(configurationFile)
        _ConfigDataSong.checkValidity(configurationFile)
        _ConfigDataSongGroup.checkValidity(configurationFile)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        _LocalValidator.initialize()
        _ConfigDataGlobal.initialize(self)
        _ConfigDataMidiHumanization.initialize(self)
        _ConfigDataNotation.initialize(self)
        _ConfigDataSong.initialize(self)
        _ConfigDataSongGroup.initialize(self)

    #--------------------

    def __str__ (self):
        """Returns the string representation of <self>"""

        className = self.__class__.__name__
        st = (("%s(%s, %s, %s, %s, %s)")
              % (className,
                 _ConfigDataGlobal.toString(self),
                 _ConfigDataNotation.toString(self),
                 _ConfigDataMidiHumanization.toString(self),
                 _ConfigDataSong.toString(self),
                 _ConfigDataSongGroup.toString(self)))

        return st

    #--------------------

    def checkAndSetDerivedVariables (self, selectedVoiceNameSet):
        """Checks data from configuration file read into <self>;
           <selectedVoiceNameList> gives the set of voices selected
           for processing"""

        Logging.trace(">>")

        self._checkValidity()

        configurationFile = self._configurationFile
        _ConfigDataGlobal.read(self, configurationFile)
        _ConfigDataMidiHumanization.read(self, configurationFile)
        _ConfigDataNotation.read(self, configurationFile)
        _ConfigDataSong.read(self, configurationFile)
        _ConfigDataSongGroup.read(self, configurationFile)

        if len(self.extractVoiceNameSet) == 0:
            self.extractVoiceNameSet.update(self.voiceNameList)

        if len(self.midiVoiceNameList) == 0:
            self.midiVoiceNameList = list(self.voiceNameList)

        if len(self.scoreVoiceNameList) == 0:
            self.scoreVoiceNameList = list(self.voiceNameList)

        if len(self.audioVoiceNameSet) == 0:
            self.audioVoiceNameSet.update(self.midiVoiceNameList)

        for videoFileKindName, videoFileKind in self.videoFileKindMap.items():
            if len(videoFileKind.voiceNameList) == 0:
                videoFileKind.voiceNameList = list(self.voiceNameList)

        if len(selectedVoiceNameSet) == 0:
            # when no voices are selected so far, all voices will be
            # used
            selectedVoiceNameSet.update(self.voiceNameList)

        Logging.trace("<<: '%s'", self)

    #--------------------

    def get (self, parameterName):
        """Gets data from configuration file read into <self> at
           <parameterName>"""

        Logging.trace(">>: %s", parameterName)

        getValueProc = self._configurationFile.getValue
        result = _LocalValidator.get(parameterName, getValueProc)

        Logging.trace("<<: '%s'", result)
        return result

    #--------------------

    def readFile (self, configurationFilePath):
        """Reads data from configuration file with <configurationFilePath>
           into <self>"""

        Logging.trace(">>: '%s'", configurationFilePath)

        separator = OperatingSystem.pathSeparator
        scriptFilePath = OperatingSystem.scriptFilePath()
        scriptDirectoryPath = OperatingSystem.dirname(scriptFilePath)
        configSuffix = separator + "config"
        searchPathList = \
          [ OperatingSystem.homeDirectoryPath() + separator + ".ltbvc",
            scriptDirectoryPath + configSuffix,
            OperatingSystem.dirname(scriptDirectoryPath) + configSuffix ]
        ConfigurationFile.setSearchPaths(searchPathList)
        self._configurationFile = ConfigurationFile(configurationFilePath)

        Logging.trace("<<")
