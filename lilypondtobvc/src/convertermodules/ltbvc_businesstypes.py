# -*- coding: utf-8-unix -*-
# ltbvc_businesstypes -- services for several simple business types for the
#                        lilypond to band video converter that are used
#                        across modules:
#
#                          - AudioTrack
#                          - TempoTrack
#                          - TrackSettings
#                          - VideoFileKind
#                          - VideoTarget
#                          - VoiceDescriptor
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

from copy import deepcopy

from basemodules.regexppattern import RegExpPattern
from basemodules.simplelogging import Logging
from basemodules.ttbase import adaptToRange, convertStringToList, \
                               convertStringToMap, iif2
from basemodules.validitychecker import ValidityChecker

#====================

_noCommaPattern    = r"(?:'[^']*'|[^,'\s]+)"

#====================

def _checkForTypesAndCompleteness (objectName, objectKind,
                                   attributeNameToValueMap,
                                   attributeNameToKindMap):
    """Checks for object with <objectName> and kind <objectKind>
       whether elements in <attributeNameToValueMap> occur in
       <attributeNameToKindMap> and have correct types"""

    Logging.trace(">>: name = '%s', kind = '%s', attributeMap = %s"
                  + " referenceMap = %s",
                  objectName, objectKind,
                  attributeNameToValueMap, attributeNameToKindMap)

    for attributeName in attributeNameToKindMap.keys():
        ValidityChecker.isValid(\
            attributeNameToValueMap.get(attributeName) is not None,
            "no value for %s in %s %s"
                                % (attributeName, objectKind, objectName))
        kind  = attributeNameToKindMap[attributeName]
        value = attributeNameToValueMap[attributeName]
        errorMessage = ("bad kind for %s in %s %s: %s"
                        % (attributeName, objectKind, objectName, value))

        if kind in [ "I", "F" ]:
            isFloat = (kind == "F")
            ValidityChecker.isNumberString(value, errorMessage, isFloat)
        elif kind == "B":
            ValidityChecker.isValid(value.upper() in ["TRUE", "FALSE"],
                                    errorMessage)

    Logging.trace("<<")

#--------------------

def _setToDefault (currentMap, key, defaultValue):
    """sets entry <key> in <map> to <defaultValue> if undefined"""

    originalValue = currentMap.get(key, None)
    Logging.trace(">>: key = %s, originalValue = %s, default = %s",
                  key, originalValue, defaultValue)

    if key not in currentMap:
        currentMap[key] = defaultValue

    Logging.trace("<<")
    
#====================

def generateObjectListFromString (st, prototypeObject):
    """Generates list of objects as copies of <prototypeObject> from
       external representation <st> describing a mapping from
       object name to object value"""

    Logging.trace(">>: %s", st)

    result = []
    table = convertStringToMap(st)

    for name in table.keys():
        attributeNameToValueMap = table[name]
        attributeNameToValueMap["name"] = name
        Logging.trace("--: converting %s = %s",
                      name, attributeNameToValueMap)
        currentObject = deepcopy(prototypeObject)
        currentObject.checkAndSetFromMap(attributeNameToValueMap)
        result.append(currentObject)

    Logging.trace("<<: %s", result)
    return result

#--------------------

def generateObjectMapFromString (st, prototypeObject):
    """Generates map of objects as copies of <prototypeObject> from
       external representation <st> describing a mapping from
       object name to object value"""

    Logging.trace(">>: %s", st)

    result = {}
    table = convertStringToMap(st)

    for name, attributeNameToValueMap in table.items():
        attributeNameToValueMap["name"] = name
        Logging.trace("--: converting %s = %s",
                      name, attributeNameToValueMap)
        currentObject = deepcopy(prototypeObject)
        currentObject.checkAndSetFromMap(attributeNameToValueMap)
        result[name] = currentObject

    Logging.trace("<<: %s", result)
    return result

#--------------------

def humanReadableVoiceName (voiceName):
    """Returns human readable version of given <voiceName>"""

    result = iif2(voiceName.endswith("Simple"), voiceName[:-6],
                  voiceName.endswith("Extended"), voiceName[:-8],
                  voiceName)
    return result

#====================

class AudioTrack:
    """Represents information about the audio tracks
       combining audio groups together with all their
       properties."""

    _attributeNameToTypeMap = {
        "name"                     : "S",
        "audioGroupList"           : "S",
        "audioFileTemplate"        : "S",
        "songNameTemplate"         : "S",
        "albumName"                : "S",
        "description"              : "S",
        "languageCode"             : "S"
    }

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        self.name              = "XXX"
        self.audioGroupList    = []
        self.audioFileTemplate = "%"
        self.songNameTemplate  = "%"
        self.albumName         = "[ALBUM NAME]"
        self.description       = "XXX"
        self.languageCode      = "eng"

    #--------------------

    def __repr__ (self):
        return str(self)

    #--------------------

    def __str__ (self):
        clsName = self.__class__.__name__
        st = (("%s(name = %s, groupList = %s,"
               + " audioFileTemplate = '%s', songNameTemplate = '%s',"
               + " albumName = '%s', description = '%s', language = %s")
               % (clsName,
                  self.name, self.audioGroupList,
                  self.audioFileTemplate, self.songNameTemplate,
                  self.albumName, self.description, self.languageCode))
        return st

    #--------------------

    def checkAndSetFromMap (self, attributeNameToValueMap):
        """Checks validity of variables in
           <attributeNameToValueMap> and assigns them to current
           audio track descriptor"""

        cls = self.__class__

        # set optional attributes to default values
        _setToDefault(attributeNameToValueMap, "description", "")

        # check and set object values
        name = attributeNameToValueMap["name"]
        _checkForTypesAndCompleteness(name, "audio track",
                                      attributeNameToValueMap,
                                      cls._attributeNameToTypeMap)

        self.name              = name
        st                     = attributeNameToValueMap["audioGroupList"]
        self.audioGroupList    = convertStringToList(st, "/")
        self.audioFileTemplate = attributeNameToValueMap["audioFileTemplate"]
        self.songNameTemplate  = attributeNameToValueMap["songNameTemplate"]
        self.albumName         = attributeNameToValueMap["albumName"]
        self.description       = attributeNameToValueMap["description"]
        self.languageCode      = attributeNameToValueMap["languageCode"]

    #--------------------

    @classmethod
    def regexpPattern (cls):
        """Returns regexp pattern for checking an audio track string"""

        attributeNamePattern = \
            "(?:%s)" % ("|".join(cls._attributeNameToTypeMap.keys()))
        result = RegExpPattern.makeMapPattern(attributeNamePattern,
                                              _noCommaPattern, False)
        return result

#====================

class AudioGroup:
    """Represents information about the audio groups
       combining voices."""

    pass

#====================

class TempoTrack:
    """Represents tempo track with mappings from measure number to
       tempo (in beats per minute) and measure length (in
       quarters)."""

    _defaultMeasureLength = 4 # quarters

    #--------------------

    @classmethod
    def measureToTempoMap (cls, tempoMap):
        """Scans <tempoMap> for mappings from measure number to tempo
           and measure length indications and returns those in a map.
           Note that intermediate measures just maintain the previous
           tempo and length indication (as expected)."""

        Logging.trace(">>: %s", tempoMap)

        result = {}
        separator = "/"
        measureLength = cls._defaultMeasureLength

        for measure, measureLengthAndTempo in tempoMap.items():
            measure = int(measure)
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

class TrackSettings:
    """Represents the settings of a MIDI track"""

    def __init__ (self, voiceName, midiChannel, midiInstrumentBank,
                  midiInstrument, midiVolume, panPosition, reverbLevel):
        """Initializes object with all standard parameters"""

        self.voiceName = voiceName

        # adjust to MIDI parameter ranges
        self.midiChannel        = adaptToRange(midiChannel, 0, 15)
        self.midiInstrumentBank = adaptToRange(midiInstrumentBank, 0, 127)
        self.midiInstrument     = adaptToRange(midiInstrument, 0, 127)
        self.midiVolume         = adaptToRange(midiVolume, 0, 127)
        self.panPosition        = adaptToRange(panPosition, 0, 127)
        self.reverbLevel        = adaptToRange(reverbLevel, 0, 127)

#====================

class VideoFileKind:
    """This class encapsulates the settings for a video file kind used
       for video generation."""

    _attributeNameToTypeMap = {
        "name"           : "S",
        "target"         : "S",
        "fileNameSuffix" : "S",
        "directoryPath"  : "S",
        "voiceNameList"  : "S"
    }

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        self.name           = None
        self.target         = None
        self.fileNameSuffix = None
        self.directoryPath  = None
        self.voiceNameList  = None

    #--------------------

    def __repr__ (self):
        return str(self)

    #--------------------

    def __str__ (self):
        clsName = self.__class__.__name__
        st = (("%s(name = %s, target = %s, fileNameSuffix = %s,"
               + " directory = %s, voiceNameList = %s")
               % (clsName,
                  self.name, self.target, self.fileNameSuffix,
                  self.directoryPath, self.voiceNameList))
        return st

    #--------------------

    def checkAndSetFromMap (self, attributeNameToValueMap):
        """Checks validity of variables in
           <attributeNameToValueMap> and assigns them to
           current video target"""

        cls = self.__class__

        # check and set object values
        targetName = attributeNameToValueMap["name"]
        _checkForTypesAndCompleteness(targetName, "video file kind",
                                      attributeNameToValueMap,
                                      cls._attributeNameToTypeMap)

        self.name             = targetName
        self.target           = attributeNameToValueMap["target"]
        self.fileNameSuffix   = attributeNameToValueMap["fileNameSuffix"]
        self.directoryPath    = attributeNameToValueMap["directoryPath"]
        self.voiceNameList    = \
            convertStringToList(attributeNameToValueMap["voiceNameList"])

    #--------------------

    @classmethod
    def regexpPattern (cls):
        """Returns regexp pattern for checking a video file kind string"""

        attributeNamePattern = \
            "(?:%s)" % ("|".join(cls._attributeNameToTypeMap.keys()))
        result = RegExpPattern.makeMapPattern(attributeNamePattern,
                                              _noCommaPattern, False)
        return result

#====================

class VideoTarget:
    """This class encapsulates the settings for a video target used
       for video generation."""

    _attributeNameToTypeMap = {
        "name"                     : "S",
        "resolution"               : "I",
        "height"                   : "I",
        "width"                    : "I",
        "topBottomMargin"          : "F",
        "leftRightMargin"          : "F",
        "systemSize"               : "F",
        "mediaType"                : "S",
        "subtitleColor"            : "I",
        "subtitleFontSize"         : "F",
        "scalingFactor"            : "I",
        "frameRate"                : "F",
        "subtitlesAreHardcoded"    : "B"
    }

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        self.name                     = None
        self.resolution               = None
        self.height                   = None
        self.width                    = None
        self.topBottomMargin          = None
        self.leftRightMargin          = None
        self.scalingFactor            = None
        self.frameRate                = None
        self.systemSize               = None
        self.mediaType                = None
        self.subtitleColor            = None
        self.subtitleFontSize         = None
        self.subtitlesAreHardcoded    = None

    #--------------------

    def __repr__ (self):
        return str(self)

    #--------------------

    def __str__ (self):
        clsName = self.__class__.__name__
        st = (("%s(name = %s,"
               + " resolution = %s, height = %s, width = %s,"
               + " topBottomMargin = %s, leftRightMargin = %s,"
               + " systemSize = %s, scalingFactor = %s,"
               + " mediaType = '%s', frameRate = %s,"
               + " subtitleColor = %s, subtitleFontSize = %s,"
               + " subtitlesAreHardcoded = %s")
               % (clsName,
                  self.name,
                  self.resolution, self.height, self.width,
                  self.topBottomMargin, self.leftRightMargin,
                  self.systemSize, self.scalingFactor,
                  self.mediaType, self.frameRate,
                  self.subtitleColor, self.subtitleFontSize,
                  self.subtitlesAreHardcoded))
        return st

    #--------------------

    def checkAndSetFromMap (self, attributeNameToValueMap):
        """Checks validity of variables in
           <attributeNameToValueMap> and assigns them to
           current video target"""

        cls = self.__class__

        # set optional attributes to default values
        _setToDefault(attributeNameToValueMap, "systemSize", 20)
        _setToDefault(attributeNameToValueMap, "scalingFactor", 1)
        _setToDefault(attributeNameToValueMap, "mediaType", "Normal")
        _setToDefault(attributeNameToValueMap, "subtitlesAreHardcoded",
                      "true")

        # check and set object values
        targetName = attributeNameToValueMap["name"]
        _checkForTypesAndCompleteness(targetName, "video target",
                                      attributeNameToValueMap,
                                      cls._attributeNameToTypeMap)

        self.name             = targetName
        self.resolution       = int(attributeNameToValueMap["resolution"])
        self.height           = int(attributeNameToValueMap["height"])
        self.width            = int(attributeNameToValueMap["width"])
        self.topBottomMargin  = int(attributeNameToValueMap["topBottomMargin"])
        self.leftRightMargin  = int(attributeNameToValueMap["leftRightMargin"])
        self.systemSize       = int(attributeNameToValueMap["systemSize"])
        self.scalingFactor    = int(attributeNameToValueMap["scalingFactor"])
        self.frameRate        = float(attributeNameToValueMap["frameRate"])
        self.mediaType        = attributeNameToValueMap["mediaType"]
        self.subtitleColor    = int(attributeNameToValueMap["subtitleColor"])
        self.subtitleFontSize = int(attributeNameToValueMap["subtitleFontSize"])
        self.subtitlesAreHardcoded = \
            attributeNameToValueMap["subtitlesAreHardcoded"].upper() == "TRUE"

    #--------------------

    @classmethod
    def regexpPattern (cls):
        """Returns regexp pattern for checking a video target string"""

        attributeNamePattern = \
            "(?:%s)" % ("|".join(cls._attributeNameToTypeMap.keys()))
        result = RegExpPattern.makeMapPattern(attributeNamePattern,
                                              _noCommaPattern, False)
        return result

#====================

class VoiceDescriptor:
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

    def __repr__ (self):
        return str(self)

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
