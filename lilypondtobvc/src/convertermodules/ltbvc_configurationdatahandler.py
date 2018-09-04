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

from basemodules.configurationfile import ConfigurationFile
from basemodules.operatingsystem import OperatingSystem
from basemodules.regexppattern import RegExpPattern
from basemodules.simplelogging import Logging
from basemodules.ttbase import adaptToKind, convertStringToList, \
                               convertStringToMap, iif, isInRange
from basemodules.validitychecker import ValidityChecker

from .ltbvc_businesstypes import generateObjectListFromString, \
                                 generateObjectMapFromString, \
                                 AudioTrack, TempoTrack, \
                                 VideoFileKind, VideoTarget, VoiceDescriptor

#====================

def _checkVariableList (variableNameList, configurationFile):
    """Checks all variables in <variableNameList> to be read from
       <configurationFile>"""

    for variableName in variableNameList:
        _LocalValidator.checkVariable(variableName,
                                      configurationFile.getValue)

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

#--------------------

def _readAttributesFromConfigFile (object, attributeNameList,
                                   configurationFile):
    """Traverses <attributeNameList> and sets attribute in <object> to
       value read from <configurationFile>."""

    for attributeName in attributeNameList:
        value = _LocalValidator.get(attributeName,
                                    configurationFile.getValue)
        setattr(object, attributeName, value)

#====================
# TYPE DEFINITIONS
#====================

class _ConfigDataGlobal:
    """Represents all configuration data that is global e.g. the
       command paths for generation. Note that this categorization is
       just for systematics, any configuration variable can be set per
       song."""

    _soundStyleNamePrefix = "soundStyle"

    # list of attribute names with external representation in config file
    _attributeNameList = \
        [ "aacCommandLine", "ffmpegCommand", "fluidsynthCommand",
          "intermediateFileDirectoryPath", "lilypondCommand",
          "loggingFilePath", "mp4boxCommand",
          "soundFontDirectoryPath", "soxCommandLinePrefix",
          "targetDirectoryPath", "tempAudioDirectoryPath",
          "tempLilypondFilePath", "videoTargetMap",
          "videoFileKindMap" ]

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
        configData.intermediateFilesAreKept      = False
        configData.lilypondCommand               = "lilypond"
        configData.loggingFilePath               = ("/tmp/logs"
                                                   + "/makeLilypondAll.log")
        configData.mp4boxCommand                 = "mp4box"
        configData.soundFontDirectoryPath        = "/tmp/soundfonts"
        configData.soundFontNameList             = ""
        configData.soundStyleNameToTextMap       = ""
        configData.soxCommandLinePrefix          = "sox"
        configData.targetDirectoryPath           = "generated"
        configData.tempAudioDirectoryPath        = "/tmp"
        configData.tempLilypondFilePath          = "."
        configData.videoTargetMap                = ""
        configData.videoFileKindMap              = ""

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
               + " intermediateFilesAreKept = %s,"
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
                 configData.intermediateFilesAreKept,
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

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        attributeNameList = (cls._attributeNameList
                             + [ "keepIntermediateFiles",
                                 "soundFontNames" ])
        _checkVariableList(attributeNameList, configurationFile)

        # validate sound style definitions
        styleNamePrefix = cls._soundStyleNamePrefix
        soundStyleNameList = _getStylesWithNamePrefix(styleNamePrefix,
                                                      configurationFile)

        for styleName in soundStyleNameList:
            _LocalValidator.checkVariable(styleName,
                                          configurationFile.getValue,
                                          styleNamePrefix + "*")

        # additional checks
        for variableName in ["aacCommandLine", "soxCommandLinePrefix"]:
            commandLine = getValueProc(variableName)
            command = commandLine.split()[0]
            ValidityChecker.isReadableFile(command, variableName)

        configVariableName = "soundFontNames"
        nameList = convertStringToList(getValueProc(configVariableName))
        soundFontDirectoryPath = getValueProc("soundFontDirectoryPath")
        separator = OperatingSystem.pathSeparator

        for name in nameList:
            fullPath = soundFontDirectoryPath + separator + name
            ValidityChecker.isReadableFile(fullPath, configVariableName)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserializeObjects (cls, configData):
        """Adapts strings in <configData> into final list or map form."""

        Logging.trace(">>")
        cstl = convertStringToList
        
        configData.soundFontNameList = cstl(configData.soundFontNameList)
        configData.videoFileKindMap = \
            generateObjectMapFromString(configData.videoFileKindMap,
                                        VideoFileKind())
        configData.videoTargetMap = \
            generateObjectMapFromString(configData.videoTargetMap,
                                        VideoTarget())
        
        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads global configuration data from <configurationFile> into
           <configData> without any string interpretation for object
           serializations."""

        Logging.trace(">>")

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        _readAttributesFromConfigFile(configData, cls._attributeNameList,
                                      configurationFile)

        configData.intermediateFilesAreKept = \
            getValueProc("keepIntermediateFiles")
        configData.soundFontNameList = getValueProc("soundFontNames")
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

    # list of attribute names with external representation in config file
    _attributeNameList = \
        [ "humanizedVoiceNameSet", "voiceNameToVariationFactorMap" ]

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes midi humanization attributes of <configData>"""

        configData.humanizationStyleNameToTextMap = ""
        configData.humanizedVoiceNameSet          = ""
        configData.voiceNameToVariationFactorMap  = ""

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

        _checkVariableList(cls._attributeNameList, configurationFile)

        styleNamePrefix = cls._humanizationStyleNamePrefix
        humanizationStyleNameList = \
            _getStylesWithNamePrefix(styleNamePrefix, configurationFile)

        for styleName in humanizationStyleNameList:
            _LocalValidator.checkVariable(styleName,
                                          configurationFile.getValue,
                                          styleNamePrefix + "*")

        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserializeObjects (cls, configData):
        """Adapts strings in <configData> into final list or map form."""

        Logging.trace(">>")
        
        vntvfMap = {}
        tempMap = convertStringToMap(configData.voiceNameToVariationFactorMap)

        for voiceName, factors in tempMap.items():
            scalingFactors = list(map(lambda x: float(x), factors.split("/")))
            vntvfMap[voiceName] = scalingFactors

        configData.voiceNameToVariationFactorMap = vntvfMap
        
        configData.humanizedVoiceNameSet = \
            set(convertStringToList(configData.humanizedVoiceNameSet))

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads midi humanization configuration data from
           <configurationFile> into <configData>."""

        Logging.trace(">>")

        _readAttributesFromConfigFile(configData, cls._attributeNameList,
                                      configurationFile)
        configData.humanizationStyleNameToTextMap = \
            _readStylesWithPrefix(cls._humanizationStyleNamePrefix,
                                  configurationFile)

        Logging.trace("<<")

#====================

class _ConfigDataNotation:
    """Represents all configuration data that refers to the notation:
       this is the map from phase and voice name to the staff kind and
       the map from phase and voice name to the clef."""

    # list of attribute names with external representation in config file
    _attributeNameList = \
        [ "phaseAndVoiceNameToClefMap", "phaseAndVoiceNameToStaffListMap",
          "voiceNameToScoreNameMap" ]

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes notation attributes of <configData>"""

        configData.phaseAndVoiceNameToClefMap      = ""
        configData.phaseAndVoiceNameToStaffListMap = ""
        configData.voiceNameToScoreNameMap         = ""

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the notation
           attributes of <configData>"""

        className = cls.__name__
        st = (("%s("
               + "phaseAndVoiceNameToClefMap = %s,"
               + " phaseAndVoiceNameToStaffListMap = %s,"
               + " voiceNameToScoreNameMap = %s)")
              % (className,
                 configData.phaseAndVoiceNameToClefMap,
                 configData.phaseAndVoiceNameToStaffListMap,
                 configData.voiceNameToScoreNameMap))
        return st

    #--------------------

    @classmethod
    def checkValidity (cls, configurationFile):
        """Checks the validity of data to be read from
           <configurationFile> for the notation attributes"""

        Logging.trace(">>")

        _checkVariableList(cls._attributeNameList, configurationFile)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserializeObjects (cls, configData):
        """Adapts strings in <configData> into final list or map form."""

        Logging.trace(">>")
        
        pAVnToStaffListMap = \
            convertStringToMap(configData.phaseAndVoiceNameToStaffListMap)

        for phase, voiceNameToStaffListMap in pAVnToStaffListMap.items():
            updatedMap = {}

            for voiceName, staffListString in voiceNameToStaffListMap.items():
                staffList = convertStringToList(staffListString, "/")
                updatedMap[voiceName] = staffList

            pAVnToStaffListMap[phase] = updatedMap
                
        configData.phaseAndVoiceNameToClefMap = \
            convertStringToMap(configData.phaseAndVoiceNameToClefMap)
        configData.phaseAndVoiceNameToStaffListMap = pAVnToStaffListMap
        configData.voiceNameToScoreNameMap = \
            convertStringToMap(configData.voiceNameToScoreNameMap)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads notation configuration data from <configurationFile>
           into <configData>."""

        Logging.trace(">>")

        _readAttributesFromConfigFile(configData, cls._attributeNameList,
                                      configurationFile)

        Logging.trace("<<")

#====================

class _ConfigDataSong:
    """Represents all configuration data for a song like e.g. the voice names
       or the song title. Note that this categorization is just for
       systematics, any configuration variable can be set per song."""

    _attributeNameList = \
      [ "attenuationLevel", "audioVoiceNameSet",
        "countInMeasureCount", "extractVoiceNameSet", "fileNamePrefix",
        "includeFilePath", "intermediateFilesAreKept",
        "measureToHumanizationStyleNameMap", "measureToTempoMap",
        "midiVoiceNameList", "scoreVoiceNameList", "title",
        "trackNumber", "voiceNameToChordsMap", "voiceNameToLyricsMap",
        "voiceNameToOverrideFileNameMap" ]

    _voiceAttributeNameList = [
        "audioLevelList", "midiChannelList", "midiInstrumentList",
        "midiVolumeList", "panPositionList", "reverbLevelList",
        "soundVariantList", "voiceNameList"]

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _adaptMap (cls, map, keyKind='S', valueKind='S'):
        """Changes in place the keys and values of <map>; <keyKind> tells the
           target kind of the keys, <valueKind> those of the values"""

        Logging.trace(">>: map = %s, keyKind = %s, valueKind = %s",
                      map, keyKind, valueKind)

        otherMap = dict(map)
        map.clear()

        for key, value in otherMap.items():
            newKey   = adaptToKind(key,   keyKind)
            newValue = adaptToKind(value, valueKind)
            map[newKey] = newValue

        Logging.trace("<<: %s", map)

    #--------------------

    @classmethod
    def _checkStringLists (cls, voiceNames, midiChannels, midiInstruments,
                           midiVolumes, panPositions, audioLevels,
                           reverbLevels, soundVariants):
        """Checks whether data for voice list and voice data read from
           configuration file is okay."""

        Logging.trace(">>: voiceNames = '%s', midiChannels = '%s',"
                      + " midiInstruments = '%s', midiVolumes = '%s',"
                      + " panPositions = '%s', audioLevels ='%s',"
                      + " reverbLevels = '%s', soundVariants = '%s'",
                      voiceNames, midiChannels, midiInstruments,
                      midiVolumes, panPositions, audioLevels,
                      reverbLevels, soundVariants)

        elementsInString = lambda st: len(st.strip().split(","))

        checkForRequiredLength = (lambda st, valueName, elementCount:
            ValidityChecker.isValid(elementsInString(st) == elementCount,
                                    ("'%s' must contain %d elements"
                                     + " to match 'voiceNameList'")
                                    % (valueName, elementCount)))

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

    @classmethod
    def _convertToVoiceMap (cls, configData,
                            voiceNames, midiChannels, midiInstruments,
                            midiVolumes, panPositions, audioLevels,
                            reverbLevels, soundVariants):
        """Converts strings read from configuration file to voice name
           list and map to voice descriptors"""

        Logging.trace(">>: voiceNames = '%s', midiChannels = '%s',"
                      + " midiInstruments = '%s', midiVolumes = '%s',"
                      + " panPositions = '%s', audioLevels ='%s',"
                      + " reverbLevels = '%s', soundVariants = '%s'",
                      voiceNames, midiChannels, midiInstruments,
                      midiVolumes, panPositions, audioLevels,
                      reverbLevels, soundVariants)

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
        map = convertStringToMap(mapAsString)

        if map is None:
            result = None
        else:
            result = {}
            
            for voiceName, value in map.items():
                entry = iif(isLyricsMap, {}, set())
                targetList = value.split("/")
                Logging.trace("--: targetList(%s) = %s",
                              voiceName, targetList)

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

        if parallelTrackInfo == "" or parallelTrackInfo is None:
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

        configData.attenuationLevel                  = 0
        configData.audioVoiceNameSet                 = set()
        configData.countInMeasureCount               = 0
        configData.extractVoiceNameSet               = set()
        configData.fileNamePrefix                    = "XXXX"
        configData.includeFilePath                   = "%includeFilePath%"
        configData.intermediateFilesAreKept          = False
        configData.measureToHumanizationStyleNameMap = None
        configData.measureToTempoMap                 = None
        configData.midiVoiceNameList                 = ""
        configData.parallelTrackFilePath             = ""
        configData.parallelTrackVolume               = 1.0
        configData.scoreVoiceNameList                = ""
        configData.shiftOffset                       = 0.0
        configData.songComposerText                  = None
        configData.songYear                          = None
        configData.title                             = "%title%"
        configData.trackNumber                       = 0
        configData.voiceNameList                     = ""
        configData.voiceNameToChordsMap              = {}
        configData.voiceNameToLyricsMap              = {}
        configData.voiceNameToOverrideFileNameMap    = {}
        configData.voiceNameToVoiceDataMap           = {}

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the song related
           attributes of <configData>"""

        st = (("%s("
               + "attenuationLevel = %5.3f,  audioVoiceNameSet = %s,"
               + " countInMeasureCount = %d,"
               + " extractVoiceNameSet = %s, fileNamePrefix = %s,"
               + " includeFilePath = '%s', intermediateFilesAreKept = %s,"
               + " measureToHumanizationStyleNameMap = %s,"
               + " measureToTempoMap = %s,  midiVoiceNameList = %s,"
               + " parallelTrackFilePath = '%s', parallelTrackVolume = %4.3f,"
               + " scoreVoiceNameList = %s, shiftOffset = %5.3f,"
	       + " songComposerText = '%s', songYear = %d,"
               + " title = '%s', trackNumber = %d,"
               + " voiceNameList = %s, voiceNameToChordsMap = %s,"
               + " voiceNameToLyricsMap = %s,"
               + " voiceNameToOverrideFileNameMap = %s,"
               + " voiceNameToVoiceDataMap = %s"
               + ")")
               % (cls.__name__,
                  configData.attenuationLevel, configData.audioVoiceNameSet,
                  configData.countInMeasureCount,
                  configData.extractVoiceNameSet, configData.fileNamePrefix,
                  configData.includeFilePath,
                  configData.intermediateFilesAreKept,
                  configData.measureToHumanizationStyleNameMap,
                  configData.measureToTempoMap, configData.midiVoiceNameList,
                  configData.parallelTrackFilePath,
                  configData.parallelTrackVolume,
                  configData.scoreVoiceNameList, configData.shiftOffset,
                  configData.songComposerText, configData.songYear,
                  configData.title, configData.trackNumber,
                  configData.voiceNameList, configData.voiceNameToChordsMap,
                  configData.voiceNameToLyricsMap,
                  configData.voiceNameToOverrideFileNameMap,
                  configData.voiceNameToVoiceDataMap))

        return st

    #--------------------

    @classmethod
    def checkValidity (cls, configurationFile):
        """Checks the validity of data to be read from
           <configurationFile> for the song attributes"""

        Logging.trace(">>")

        _checkVariableList(cls._attributeNameList, configurationFile)
        _checkVariableList(cls._voiceAttributeNameList, configurationFile)
        
        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        # additional rules
        fileNamePrefix = getValueProc("fileNamePrefix")
        ValidityChecker.isValid(" " not in fileNamePrefix,
                                "'fileNamePrefix' must not contain blanks")

        includeFilePath = getValueProc("includeFilePath")
        includeFilePath  = iif(includeFilePath != "", includeFilePath,
                               fileNamePrefix + "-music.ly")
        ValidityChecker.isReadableFile(includeFilePath, "includeFilePath")

        year = getValueProc("year")
        ValidityChecker.isValid(isInRange(year, 1900, 2100),
                                "'year' must be in a reasonable range")

        # consistency of the lists
        cls._checkStringLists(getValueProc("voiceNameList"),
                              getValueProc("midiChannelList"),
                              getValueProc("midiInstrumentList"),
                              getValueProc("midiVolumeList"),
                              getValueProc("panPositionList"),
                              getValueProc("audioLevelList"),
                              getValueProc("reverbLevelList"),
                              getValueProc("soundVariantList"))

        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserializeObjects (cls, configData):
        """Adapts strings in <configData> into final list or map form."""

        Logging.trace(">>")
        cstl = convertStringToList
        
        configData.audioVoiceNameSet = \
          set(cstl(configData.audioVoiceNameSet))
        configData.extractVoiceNameSet = \
          set(cstl(configData.extractVoiceNameSet))
        configData.measureToHumanizationStyleNameMap = \
            convertStringToMap(configData.measureToHumanizationStyleNameMap)
        cls._adaptMap(configData.measureToHumanizationStyleNameMap, 'F')
        configData.midiVoiceNameList  = cstl(configData.midiVoiceNameList)
        configData.scoreVoiceNameList = cstl(configData.scoreVoiceNameList)
        configData.voiceNameToChordsMap = \
            cls._convertTargetMapping(configData.voiceNameToChordsMap, False)
        configData.voiceNameToLyricsMap = \
            cls._convertTargetMapping(configData.voiceNameToLyricsMap, True)
        configData.voiceNameToOverrideFileNameMap = \
            convertStringToMap(configData.voiceNameToOverrideFileNameMap)

        # the string representation for the parallel track is stored
        # in <parallelTrackInfo>
        cls._splitParallelTrackInfo(configData,
                                    configData.parallelTrackInfo)
        
        # the tempo map maps the measure into a pair of tempo and
        # measure length in quarters
        tempoMap = convertStringToMap(configData.measureToTempoMap)
        cls._adaptMap(tempoMap, 'F')

        for key, value in tempoMap.items():
            if "/" not in value:
                tempo = float(value)
                measureLength = 4.0
            else:
                slashPosition = value.find("/")
                tempo = float(value[:slashPosition])
                measureLength = float(value[slashPosition+1:])

            tempoMap[key] = (tempo, measureLength)

        configData.measureToTempoMap = tempoMap

        # the voice data map is synthesized from several lists
        c = configData.voiceNameToVoiceDataMap
        cls._convertToVoiceMap(configData,
                               c["voiceNameList"], c["midiChannelList"],
                               c["midiInstrumentList"], c["midiVolumeList"],
                               c["panPositionList"], c["audioLevelList"],
                               c["reverbLevelList"], c["soundVariantList"])

        # adapt the different lists (when empty)
        if len(configData.extractVoiceNameSet) == 0:
            configData.extractVoiceNameSet.update(configData.voiceNameList)

        if len(configData.midiVoiceNameList) == 0:
            configData.midiVoiceNameList = list(configData.voiceNameList)

        if len(configData.scoreVoiceNameList) == 0:
            configData.scoreVoiceNameList = list(configData.voiceNameList)

        if len(configData.audioVoiceNameSet) == 0:
            configData.audioVoiceNameSet.update(configData.midiVoiceNameList)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads song configuration data from <configurationFile> into
           <configData>."""

        Logging.trace(">>")

        _readAttributesFromConfigFile(configData, cls._attributeNameList,
                                      configurationFile)
        
        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)

        if configData.includeFilePath == "":
            configData.includeFilePath = (configData.fileNamePrefix
                                          + "-music.ly")

        configData.parallelTrackInfo = getValueProc("parallelTrack")
        configData.songComposerText = getValueProc("composerText")
        configData.songYear = getValueProc("year")

        configData.voiceNameToVoiceDataMap = {}

        for voiceAttributeName in cls._voiceAttributeNameList:
            configData.voiceNameToVoiceDataMap[voiceAttributeName] = \
                getValueProc(voiceAttributeName)

        # set to float values for correct output
        configData.parallelTrackVolume = 0.0
        configData.shiftOffset         = 0.0

        Logging.trace("<<: configData = %s", configData)

#====================

class _ConfigDataSongGroup:
    """Represents all configuration data that is considered to be
       related to group of songs like e.g. the name of an album or the
       artist for generation. Note that this categorization is
       just for systematics, any configuration variable can be set per
       song."""

    # list of attribute names with external representation in config file
    _attributeNameList = \
      [ "albumArtFilePath", "albumName", "artistName",
        "audioTargetDirectoryPath",
        "audioTrackList", "targetFileNamePrefix" ]

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configData):
        """Initializes song group related attributes of
           <configData>"""

        configData.albumArtFilePath                = ""
        configData.albumName                       = ""
        configData.artistName                      = ""
        configData.audioGroupNameToVoiceNameSetMap = ""
        configData.audioTargetDirectoryPath        = ""
        configData.audioTrackList                  = ""
        configData.targetFileNamePrefix            = ""

    #--------------------

    @classmethod
    def toString (cls, configData):
        """Returns the string representation of the song
           group related attributes of <configData>"""

        st = (("%s("
               + "albumArtFilePath = '%s', albumName = '%s',"
               + " artistName = '%s', audioGroupNameToVoiceNameSetMap = %s,"
               + " audioTargetDirectoryPath = '%s', audioTrackList = %s,"
               + " targetFileNamePrefix = %s)")
              % (cls.__name__,
                 configData.albumArtFilePath, configData.albumName,
                 configData.artistName,
                 configData.audioGroupNameToVoiceNameSetMap,
                 configData.audioTargetDirectoryPath,
                 configData.audioTrackList,
                 configData.targetFileNamePrefix))

        return st

    #--------------------

    @classmethod
    def checkValidity (cls, configurationFile):
        """Checks the validity of data to be read from
           <configurationFile> for the song group attributes"""

        Logging.trace(">>")

        attributeNameList = (cls._attributeNameList
                             + [ "audioGroupToVoicesMap" ])
        _checkVariableList(attributeNameList, configurationFile)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserializeObjects (cls, configData):
        """Adapts strings in <configData> into final list or map form."""

        Logging.trace(">>")

        audioGroupToVoicesMap = \
            convertStringToMap(configData.audioGroupNameToVoiceNameSetMap)

        for audioGroupName in audioGroupToVoicesMap.keys():
            st = audioGroupToVoicesMap[audioGroupName]
            voiceNameSet = set(convertStringToList(st, "/"))
            audioGroupToVoicesMap[audioGroupName] = voiceNameSet

        configData.audioGroupNameToVoiceNameSetMap = audioGroupToVoicesMap

        configData.audioTrackList = \
            generateObjectListFromString(configData.audioTrackList,
                                         AudioTrack())

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls, configData, configurationFile):
        """Reads song group configuration data from <configurationFile>
           into <configData>."""

        Logging.trace(">>")

        _readAttributesFromConfigFile(configData, cls._attributeNameList,
                                      configurationFile)

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              configurationFile.getValue)
        configData.audioGroupNameToVoiceNameSetMap = \
            getValueProc("audioGroupToVoicesMap")

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
        Logging.trace(">>: name = %s, default = '%s', kind = %s,"
                      + " regExp = '%s'",
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

        fileNamePattern   = r"[/\w\-_\.]+"
        identifierPattern = RegExpPattern.identifierPattern
        integerPattern    = RegExpPattern.integerPattern
        floatPattern      = RegExpPattern.floatPattern

        # special element patterns
        beatPattern = r"(?:[1-8]|OTHER|SLACK|S)"
        clefPattern = makeCompactListPat(r"(?:bass_8|G_8|bass|G|'')")
        fileNameListPattern = makeListPat(fileNamePattern, False)
        humanizationPattern = r"[BA]?\d+(\.\d+)?"
        parallelTrackPattern = (r"[^,\s]+(?:,\s*%s\s*(?:,\s*%s\s*))"
                                % (floatPattern, floatPattern))
        prephasePattern = r"(?:extract|midi|score|video)"
        staffListPattern = makeCompactListPat("(?:DrumStaff|PianoStaff"
                                              + "|Staff|TabStaff)")
        tempoValuePattern = r"%s(?:/%s)?" % (floatPattern, floatPattern)

        # simple map patterns
        idToTextMapPattern = makeMapPat(identifierPattern, noCommaPattern)

        # regular expressions for lists of standard elements
        floatListRegExp = makeRegExp(makeListPat(floatPattern, False))
        identifierListRegExp = makeRegExp(makeListPat(identifierPattern,
                                                      False))
        emptyIdentifierListRegExp = makeRegExp(makeListPat(identifierPattern,
                                                           True))
        instrumentListRegExp = makeRegExp(makeListPat(r"\d+(:\d+)?", False))
        integerListRegExp = makeRegExp(makeListPat(integerPattern, False))

        # commands
        cls._setMap("aacCommandLine", "", "STRING")
        cls._setMap("ffmpegCommand", None, "EXECUTABLE")
        cls._setMap("fluidsynthCommand", None, "EXECUTABLE")
        cls._setMap("lilypondCommand", None, "EXECUTABLE")
        cls._setMap("mp4boxCommand", "", "EXECUTABLE")
        cls._setMap("soxCommandLinePrefix", None, "STRING")

        # global settings
        cls._setMap("keepIntermediateFiles", False, "BOOLEAN")

        # file paths
        cls._setMap("intermediateFileDirectoryPath", ".", "WDIRECTORY")
        cls._setMap("loggingFilePath", None, "WFILE")
        cls._setMap("targetDirectoryPath", ".", "WDIRECTORY")
        cls._setMap("tempLilypondFilePath", "./temp.ly", "WFILE")

        # song group properties
        cls._setMap("artistName", u"[ARTIST]", "STRING")
        cls._setMap("albumName", u"[ALBUM]", "STRING")

        # general song properties
        cls._setMap("composerText", "", "STRING")
        cls._setMap("countInMeasureCount", 0, "NATURAL")
        cls._setMap("fileNamePrefix", None, "STRING")
        cls._setMap("includeFilePath", "", "STRING")
        cls._setMap("title", None, "STRING")
        cls._setMap("trackNumber", 0, "NATURAL")
        cls._setMap("voiceNameList", None, "REGEXP", identifierListRegExp)
        cls._setMap("year", datetime.date.today().year, "NATURAL")

        cls._setMap("measureToTempoMap", None, "REGEXP",
                    makeRegExp(makeMapPat(floatPattern, tempoValuePattern,
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
        cls._setMap("extractVoiceNameSet", "", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("scoreVoiceNameList", "", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("voiceNameToChordsMap", "{}", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          makeCompactListPat(r"[esv]"))))
        cls._setMap("voiceNameToLyricsMap", "{}", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          makeCompactListPat(r"[esv]\d*"))))
        cls._setMap("voiceNameToScoreNameMap", "{}", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          identifierPattern)))

        # midi generation
        cls._setMap("humanizedVoiceNameSet", "", "REGEXP",
                    emptyIdentifierListRegExp)
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
        cls._setMap("midiChannelList", None, "REGEXP", integerListRegExp)
        cls._setMap("midiInstrumentList", None, "REGEXP",
                    instrumentListRegExp)
        cls._setMap("midiPanList", None, "REGEXP",
                    makeRegExp(makeListPat(r"C|\d+(\.\d+)[RL]", False)))
        cls._setMap("midiVoiceNameList", "", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("midiVolumeList", None, "REGEXP", integerListRegExp)
        cls._setMap("voiceNameToVariationFactorMap", "", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          floatPattern + "/" + floatPattern)))

        # audio file generation
        cls._setMap("attenuationLevel", 0.0, "FLOAT")
        cls._setMap("audioGroupToVoicesMap", None, "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          makeCompactListPat(identifierPattern),
                                          False)))
        cls._setMap("audioLevelList", None, "REGEXP", floatListRegExp)
        cls._setMap("audioTargetDirectoryPath", ".", "WDIRECTORY")
        cls._setMap("audioTrackList", None, "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          AudioTrack.regexpPattern(),
                                          False)))
        cls._setMap("audioVoiceNameSet", "", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("parallelTrack", "", "REGEXP",
                    makeRegExp(parallelTrackPattern))
        cls._setMap("reverbLevelList", None, "REGEXP", floatListRegExp)
        cls._setMap("soundFontDirectoryPath", None, "RDIRECTORY")
        cls._setMap("soundFontNames", None, "REGEXP",
                    makeRegExp(fileNameListPattern))
        cls._setMap("soundStyle*", None, "STRING")
        cls._setMap("soundVariantList", None, "REGEXP",
                    identifierListRegExp)
        cls._setMap("tempAudioDirectoryPath", ".", "WDIRECTORY")
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
    def checkVariable (cls, parameterName, getValueProc, checkedName=None):
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

            if value is None:
                errorMessage = "'%s' is not set" % parameterName
                ValidityChecker.isValid(False, errorMessage)
            elif kind == "STRING":
                ValidityChecker.isString(value, parameterName)
            elif kind == "NATURAL":
                ValidityChecker.isNatural(value, parameterName)
            elif kind == "BOOLEAN":
                ValidityChecker.isBoolean(value, parameterName)
            elif kind == "FLOAT":
                ValidityChecker.isFloat(value, parameterName)
            elif kind == "REGEXP":
                regExp = entry["regExp"]
                Logging.trace("--: regexp = '%s'", regExp.pattern)
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

        Logging.trace("<<")

    #--------------------

    @classmethod
    def get (cls, name, getValueProc):
        """Gets value for <name> gained by <getValueProc> providing
           default value from internal map (if any); assumes that
           correctness check has been done before"""

        Logging.trace(">>: %s", name)

        if name not in cls._map:
            result = getValueProc(name)
        else:
            entry = cls._map[name]
            defaultValue = entry["defaultValue"]
            result = getValueProc(name, defaultValue)

        Logging.trace("<<: %s", result)
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

    _homeDirectoryPath   = OperatingSystem.homeDirectoryPath()
    _scriptFilePath      = OperatingSystem.scriptFilePath()
    _scriptDirectoryPath = OperatingSystem.dirname(_scriptFilePath)

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

    def _deserializeObjects (self):
        """Deserializes all embedded objects represented as strings."""

        Logging.trace(">>")

        _ConfigDataGlobal.deserializeObjects(self)
        _ConfigDataNotation.deserializeObjects(self)
        _ConfigDataMidiHumanization.deserializeObjects(self)
        _ConfigDataSong.deserializeObjects(self)
        _ConfigDataSongGroup.deserializeObjects(self)

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

        self._deserializeObjects()

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

        cls = self.__class__

        separator = OperatingSystem.pathSeparator
        configSuffix = separator + "config"

        Logging.trace("--: scriptFilePath = '%s', scriptDirectory = '%s',"
                      + " homeDirectory = '%s'",
                      cls._scriptFilePath, cls._scriptDirectoryPath,
                      cls._homeDirectoryPath)

        searchPathList = \
          [ cls._homeDirectoryPath + separator + ".ltbvc" + configSuffix,
            cls._scriptDirectoryPath + "/../.." + configSuffix ]
        ConfigurationFile.setSearchPaths(searchPathList)
        file = ConfigurationFile(configurationFilePath)
        self._configurationFile = file

        Logging.trace("<<")
        return file
