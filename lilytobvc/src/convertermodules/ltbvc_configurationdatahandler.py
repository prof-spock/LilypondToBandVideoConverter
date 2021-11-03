# ltbvc_configurationdatahandler -- services for access to the global
#                                   configuration file of ltbvc
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

import dataclasses
from dataclasses import dataclass
import datetime

from basemodules.attributemanager import AttributeManager
from basemodules.configurationfile import ConfigurationFile
from basemodules.datatypesupport import AbstractDataType, \
                                        DataTypeSupport, specialField, \
                                        SETATTR
from basemodules.operatingsystem import OperatingSystem
from basemodules.regexppattern import RegExpPattern
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, Callable, ClassVar, \
                                    Dictionary, Map, \
                                    Natural, Object, ObjectList, Real, \
                                    String, StringList, StringMap, \
                                    StringSet, Tuple
from basemodules.stringutil import adaptToKind, convertStringToList, \
                                   convertStringToMap
from basemodules.ttbase import iif, isInRange
from basemodules.validitychecker import ValidityChecker

from .ltbvc_businesstypes import AudioTrack, VideoFileKind, \
                                 VideoTarget, VoiceDescriptor

# renamings
generateObjectListFromString= DataTypeSupport.generateObjectListFromString
generateObjectMapFromString = DataTypeSupport.generateObjectMapFromString

#====================

#--------------------------------------
# helper variables for default settings
#--------------------------------------

# the path of the directory where media files should be stored
_defaultMediaTargetDirectoryPath = "./mediafiles"

# set of voices with chord symbols
_melodicVoiceNameSet : StringSet = set(("bass", "keyboard", "guitar"))

# mapping from voice names to the lilypond clefs
_voiceNameToClefMapString : String = \
    ("{ bass : bass_8, drums : '', guitar : G_8,"
     + " keyboardBottom : bass, percussion : '' }")

# mapping from voice name to involved staffs for this voice
_voiceNameToStaffListMapString : String = \
    "{ drums : DrumStaff, percussion : DrumStaff }"

#====================

def _filterByKeyList (nameToValueMap : StringMap,
                      keyList : StringList) -> StringMap:
    """Returns <nameToValueMap> projected to keys from <keyList>"""

    Logging.trace(">>: keyList = %r, map = %r",
                  keyList, nameToValueMap)

    result = { key : value
               for key, value in nameToValueMap.items()
               if key in keyList }

    Logging.trace("<<: %r", result)
    return result

#--------------------

def _getStylesWithNamePrefix (prefix : String,
                              parameterNameToValueMap : StringMap) \
                              -> StringList:
    """Returns list of names of styles having <prefix> in
       keys of <parameterNameToValueMap>"""

    Logging.trace(">>")

    result = [ x for x in parameterNameToValueMap.keys()
               if x.startswith(prefix) ]

    Logging.trace("<<: %r", result)
    return result

#--------------------

def _readStylesWithPrefix (prefix : String,
                           parameterNameToValueMap : StringMap) \
                           -> StringMap:
    """Reads all styles with name <prefix> from <keySet> and associates
       them with their value from <parameterNameToValueMap> and returns
       them as map"""

    Logging.trace(">>")

    styleNameList = _getStylesWithNamePrefix(prefix, parameterNameToValueMap)
    result = { styleName : parameterNameToValueMap[styleName]
               for styleName in styleNameList }

    Logging.trace("<<: %r", result)
    return result

#--------------------

def _readAttributesFromMapping (currentObject : Object,
                                attributeNameList : StringList,
                                attributeNameToValueMap : StringMap):
    """Traverses <attributeNameList> and sets attribute in <currentObject>
       to value read via <attributeNameToValueMap>"""

    for attributeName in attributeNameList:
        value = _LocalValidator.get(attributeName,
                                    attributeNameToValueMap)
        setattr(currentObject, attributeName, value)

#====================

class _DefaultValueHandler:
    """Encapsulates default string values of configuration file
       variables."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    #.........................
    # complex parameter values
    #.........................
    
    # default value for refinement audio processor
    _audioProcessorDefaultString : String = \
        ("{"
         + "amplificationEffect: 'gain ${amplificationLevel}',"
         + "mixingCommandLine: 'sox -m [-v ${factor} ${infile} ] ${outfile}',"
         + "paddingCommandLine: 'sox ${infile} ${outfile} pad ${duration}',"
         + "refinementCommandLine: 'sox ${infile} ${outfile} ${effects}'"
         + "}")

    # default value for mapping from output kinds to the lilypond
    # clefs used for the different voice names
    _phaseAndVoiceNameToClefMapDefaultString = \
        ("{"
         + ", ".join([targetKind + " : " +
                      _voiceNameToClefMapString
                      for targetKind in ["extract", "midi", "score", "video"]])
         + "}")

    # default value for mapping from output kinds to staff mappings
    # used
    _phaseAndVoiceNameToStaffListMapDefaultString : String = \
        ("{ "
         + ", ".join([targetKind + " : " + _voiceNameToStaffListMapString
                      for targetKind in ["extract", "midi", "score", "video"]])
         + " }")

    # default value for mapping from voice names to chords shown in
    # extract, score or video
    _voiceNameToChordsMapDefaultString : String = \
        ("{ "
         + "vocals : s/v, "
         + ", ".join([voiceName + " : e"
                      for voiceName in _melodicVoiceNameSet])
         + " }")

    # default value for the mapping from file kind to video target for
    # a single target with the all voices
    _videoFileKindMapDefaultString = \
        ("{ " \
         "tabletVocGtr: { target:         tablet,"
         +              " fileNameSuffix: '-tblt',"
         +             (" directoryPath:  '%s' ,"
                        % _defaultMediaTargetDirectoryPath)
         +              " voiceNameList:  '' }"
         + " }")

    # default value for the mapping of the video target: a single
    # target with a 640x480 resolution
    _videoTargetMapDefaultString : String = \
        ("{ "
         + "tablet: { resolution: 64,"
         +          " height: 480,"
         +          " width: 640," \
         +          " topBottomMargin: 5," \
         +          " leftRightMargin: 10," \
         +          " scalingFactor: 4," \
         +          " frameRate: 10.0," \
         +          " mediaType: 'Music Video'," \
         +          " systemSize: 25," \
         +          " subtitleColor: 2281766911," \
         +          " subtitleFontSize: 20," \
         +          " subtitlesAreHardcoded: true }"
         + " }")

    #......................................................
    # overall mapping from parameter name to default values
    #......................................................

    _parameterNameToDataMap : StringMap = {
        # commands
        "aacCommandLine"                    : "",
        "audioProcessor"                    : _audioProcessorDefaultString,
        "ffmpegCommand"                     : "ffmpeg",
        "lilypondCommand"                   : "lilypond",
        "lilypondVersion"                   : "2.18.22",
        "midiToWavRenderingCommandLine"     : "",
        "mp4boxCommand"                     : "",

        # global settings
        "intermediateFilesAreKept"          : False,

        # file paths
        "intermediateFileDirectoryPath"     : ".",
        "loggingFilePath"                   : "./ltbvc.log",
        "targetDirectoryPath"               : "./generated",
        "tempLilypondFilePath"              : "./temp.ly",

        # song group properties
        "artistName"                        : "UNKNOWN ARTIST",
        "albumName"                         : "UNKNOWN ALBUM",

        # general song properties
        "composerText"                      : "",
        "countInMeasureCount"               : 0,
        "fileNamePrefix"                    : None,
        "includeFilePath"                   : "",
        "title"                             : None,
        "trackNumber"                       : 0,
        "voiceNameList"                     : "[]",
        "year"                              : datetime.date.today().year,
        "measureToTempoMap"                 : "{}",
        "phaseAndVoiceNameToClefMap"        : \
            _phaseAndVoiceNameToClefMapDefaultString,
        "phaseAndVoiceNameToStaffListMap"   : \
            _phaseAndVoiceNameToStaffListMapDefaultString,

        # extract and score generation
        "extractVoiceNameSet"               : "",
        "scoreVoiceNameList"                : "",
        "voiceNameToChordsMap"              : \
            _voiceNameToChordsMapDefaultString,
        "voiceNameToLyricsMap"              : "",
        "voiceNameToScoreNameMap"           : "",

        # midi generation
        "humanizedVoiceNameSet"             : "",
        "measureToHumanizationStyleNameMap" : "{}",
        "midiChannelList"                   : "",
        "midiInstrumentList"                : "",
        "midiVoiceNameList"                 : "",
        "midiVolumeList"                    : "",
        "panPositionList"                   : "",
        "voiceNameToVariationFactorMap"     : "{}",

        # audio file generation
        "audioGroupToVoicesMap"             : "{}",
        "audioTargetDirectoryPath"          : \
            _defaultMediaTargetDirectoryPath,
        "audioTrackList"                    : "{}",
        "audioVoiceNameSet"                 : "",
        "parallelTrack"                     : ",0,0",
        "reverbLevelList"                   : "",
        "soundVariantList"                  : "",
        "tempAudioDirectoryPath"            : ".",
        "voiceNameToOverrideFileNameMap"    : "{}",

        # video file generation
        "videoTargetMap"                    : _videoTargetMapDefaultString,
        "videoFileKindMap"                  : _videoFileKindMapDefaultString
    }
    
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def parameterNameList (cls) -> StringList:
        """Returns the list of parameter names with defaults"""

        return cls._parameterNameToDataMap.keys()

    #--------------------

    @classmethod
    def value (cls,
               parameterName : String) -> String:
        """Returns the default value string for parameter given by
           <parameterName> (if any)"""

        return cls._parameterNameToDataMap.get(parameterName)

#====================

class _LocalValidator:
    """Encapsulates routines for validation of the configuration
       file variables."""

    _validationMap = {}

    #--------------------
    # LOCAL ROUTINES
    #--------------------

    @classmethod
    def _setMap (cls,
                 name : String,
                 kind : String,
                 regExp : Object = None):
        """Sets a single entry in internal validation map for configuration
           variable with <name>, having type <kind>; if <kind> is
           'REGEXP', the additional parameter <regExp> gives the
           validation regexp"""

        st = ("--" if regExp is None else regExp.pattern)
        Logging.trace(">>: name = %r, kind = %r, regExp = %r",
                      name, kind, st)

        cls._validationMap[name] = { "kind"   : kind,
                                     "regExp" : regExp }

        Logging.trace("<<")

    #--------------------
    # EXPORTED ROUTINES
    #--------------------

    @classmethod
    def initialize (cls):
        """Sets up internal map for all configuration variables"""

        Logging.trace(">>")

        # abbreviations for pattern functions
        makeCompactListPat = RegExpPattern.makeCompactListPattern
        makeListPat        = RegExpPattern.makeListPattern
        makeMapPat         = RegExpPattern.makeMapPattern
        makeRegExp         = RegExpPattern.makeRegExp

        # common element patterns
        noCommaPattern    = r"(?:'[^']*'|\{[^\}]*\}|[^,'\s]+)"

        identifierPattern = RegExpPattern.identifierPattern
        integerPattern    = RegExpPattern.integerPattern
        floatPattern      = RegExpPattern.floatPattern

        # special element patterns
        audioProcessorKeyPattern = \
                      (r"(?:(?:mixing|padding|refinement)CommandLine"
                       + r"|amplificationEffect|chainSeparator|redirector)")
        beatPattern = r"(?:(?:%s)|OTHER)" % floatPattern
        clefPattern = makeCompactListPat(r"(?:bass_8|G_8|bass|G|'')")
        humanizationKeyPattern = r"(?:%s|RASTER|SLACK)" % beatPattern
        humanizationValuePattern = (r"%s(?:/[BA]?%s)?"
                                    % (floatPattern, floatPattern))
        parallelTrackPattern = (r"\s*|[^,\s]+(?:,\s*%s\s*(?:,\s*%s\s*))"
                                % (floatPattern, floatPattern))
        prephasePattern = r"(?:extract|midi|score|video)"
        staffListPattern = makeCompactListPat("(?:DrumStaff|PianoStaff"
                                              + "|Staff|TabStaff)")
        tempoValuePattern = (r"%s(?:\|%s/%s)?"
                             % (floatPattern, integerPattern, integerPattern))
        versionPattern = r"\d+(\.\d+)*"

        # simple map patterns
        idToTextMapPattern = makeMapPat(identifierPattern, noCommaPattern)

        # regular expressions for lists of standard elements
        emptyFloatListRegExp = makeRegExp(makeListPat(floatPattern, True))
        identifierListRegExp = makeRegExp(makeListPat(identifierPattern,
                                                      False))
        emptyIdentifierListRegExp = makeRegExp(makeListPat(identifierPattern,
                                                           True))
        instrumentListRegExp = makeRegExp(makeListPat(r"\d+(:\d+)?", False))
        integerListRegExp = makeRegExp(makeListPat(integerPattern, False))

        # commands
        cls._setMap("aacCommandLine", "STRING")
        cls._setMap("audioProcessor", "REGEXP",
                    makeRegExp(makeMapPat(audioProcessorKeyPattern,
                                          noCommaPattern, False)))
        cls._setMap("ffmpegCommand", "EXECUTABLE")
        cls._setMap("lilypondCommand", "EXECUTABLE")
        cls._setMap("lilypondVersion", "REGEXP",
                    makeRegExp(versionPattern))
        cls._setMap("midiToWavRenderingCommandLine", "STRING")
        cls._setMap("mp4boxCommand", "EXECUTABLE")

        # global settings
        cls._setMap("intermediateFilesAreKept", "BOOLEAN")

        # file paths
        cls._setMap("intermediateFileDirectoryPath", "WDIRECTORY")
        cls._setMap("loggingFilePath", "WFILE")
        cls._setMap("targetDirectoryPath", "WDIRECTORY")
        cls._setMap("tempLilypondFilePath", "WFILE")

        # song group properties
        cls._setMap("artistName", "STRING")
        cls._setMap("albumName", "STRING")

        # general song properties
        cls._setMap("composerText", "STRING")
        cls._setMap("countInMeasureCount", "NATURAL")
        cls._setMap("fileNamePrefix", "STRING")
        cls._setMap("includeFilePath", "STRING")
        cls._setMap("title", "STRING")
        cls._setMap("trackNumber", "NATURAL")
        cls._setMap("voiceNameList", "REGEXP", identifierListRegExp)
        cls._setMap("year", "NATURAL")

        cls._setMap("measureToTempoMap", "REGEXP",
                    makeRegExp(makeMapPat(floatPattern, tempoValuePattern,
                                          False)))
        cls._setMap("phaseAndVoiceNameToClefMap", "REGEXP",
                    makeRegExp(makeMapPat(prephasePattern,
                                          makeMapPat(identifierPattern,
                                                     clefPattern))))
        cls._setMap("phaseAndVoiceNameToStaffListMap", "REGEXP",
                    makeRegExp(makeMapPat(prephasePattern,
                                          makeMapPat(identifierPattern,
                                                     staffListPattern))))

        # extract and score generation
        cls._setMap("extractVoiceNameSet", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("scoreVoiceNameList", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("voiceNameToChordsMap", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          makeCompactListPat(r"[esv]"))))
        cls._setMap("voiceNameToLyricsMap", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          makeCompactListPat(r"[esv]\d*"))))
        cls._setMap("voiceNameToScoreNameMap", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          identifierPattern)))

        # midi generation
        cls._setMap("humanizedVoiceNameSet", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("humanizationStyle*", "REGEXP",
                    makeRegExp(makeMapPat(humanizationKeyPattern,
                                          humanizationValuePattern,
                                          False)))
        cls._setMap("measureToHumanizationStyleNameMap", "REGEXP",
                    makeRegExp(makeMapPat(integerPattern,
                                          identifierPattern)))
        cls._setMap("midiChannelList", "REGEXP", integerListRegExp)
        cls._setMap("midiInstrumentList", "REGEXP",
                    instrumentListRegExp)
        cls._setMap("midiVoiceNameList", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("midiVolumeList", "REGEXP", integerListRegExp)
        cls._setMap("panPositionList", "REGEXP",
                    makeRegExp(makeListPat(r"C|\d+(\.\d+)[RL]", False)))
        cls._setMap("voiceNameToVariationFactorMap", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          floatPattern + "/" + floatPattern)))

        # audio file generation
        cls._setMap("audioGroupToVoicesMap", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          makeCompactListPat(identifierPattern),
                                          False)))
        cls._setMap("audioTargetDirectoryPath", "WDIRECTORY")
        cls._setMap("audioTrackList", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          AudioTrack.regexpPattern(),
                                          False)))
        cls._setMap("audioVoiceNameSet", "REGEXP",
                    emptyIdentifierListRegExp)
        cls._setMap("parallelTrack", "REGEXP",
                    makeRegExp(parallelTrackPattern))
        cls._setMap("reverbLevelList", "REGEXP", emptyFloatListRegExp)
        cls._setMap("soundStyle*", "STRING")
        cls._setMap("soundVariantList", "REGEXP", identifierListRegExp)
        cls._setMap("tempAudioDirectoryPath", "WDIRECTORY")
        cls._setMap("voiceNameToOverrideFileNameMap", "REGEXP",
                    makeRegExp(idToTextMapPattern))

        # video file generation
        cls._setMap("videoTargetMap", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          VideoTarget.regexpPattern())))
        cls._setMap("videoFileKindMap", "REGEXP",
                    makeRegExp(makeMapPat(identifierPattern,
                                          VideoFileKind.regexpPattern())))

        Logging.trace("<<")

    #--------------------

    @classmethod
    def checkVariable (cls,
                       parameterName : String,
                       parameterNameToValueMap : StringMap,
                       checkedName : String = None):
        """Checks whether value for <parameterName> gained from
           <parameterNameToValueMap> is okay by looking up in internal
           map; if <checkedName> is set, the syntax of that name is
           used instead"""

        Logging.trace(">>: parameterName = %r, checkedName = %r",
                      parameterName, checkedName)
        effectiveName = iif(checkedName is None, parameterName, checkedName)

        if effectiveName not in cls._validationMap:
            # no check found => fine
            Logging.trace("--: no check necessary")
        else:
            entry = cls._validationMap[effectiveName]
            kind         = entry["kind"]
            defaultValue = _DefaultValueHandler.value(effectiveName)
            value = parameterNameToValueMap.get(parameterName, defaultValue)
            Logging.trace("--: parameterName = %s, value = %r",
                          parameterName, value)

            if value is None:
                errorMessage = "%r is not set" % parameterName
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
                Logging.trace("--: regexp = %r", regExp.pattern)
                errorMessage = "%s has a bad syntax" % parameterName
                ValidityChecker.isValid(regExp.match(value) is not None,
                                        errorMessage)
            elif value == "":
                pass
            elif kind in [ "RDIRECTORY", "WDIRECTORY" ]:
                ValidityChecker.isDirectory(value, parameterName)
            elif kind == "RFILE":
                ValidityChecker.isReadableFile(value, parameterName)
            elif kind == "EXECUTABLE":
                ValidityChecker.isExecutableCommand(value, parameterName)
            elif kind == "WFILE":
                ValidityChecker.isWritableFile(value, parameterName)
            else:
                Logging.trace("--: no check, unknown kind %r", kind)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def checkVariableList (cls,
                           parameterNameList : StringList,
                           parameterNameToValueMap : StringMap):
        """Checks all values of variables in <parameterNameList> via
           <parameterNameToValueMap>"""

        Logging.trace(">>: list = %r", parameterNameList)
        
        for parameterName in parameterNameList:
            cls.checkVariable(parameterName, parameterNameToValueMap)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def get (cls,
             name : String,
             parameterNameToValueMap : StringMap) -> Object:
        """Gets value for <name> gained by <parameterNameToValueMap>
           providing default value from internal map (if any); assumes
           that correctness check has been done before"""

        Logging.trace(">>: %r", name)

        defaultValue = _DefaultValueHandler.value(name)
        result = parameterNameToValueMap.get(name, defaultValue)

        Logging.trace("<<: %r", result)
        return result

#====================
# TYPE DEFINITIONS
#====================

@dataclass(frozen=True)
class _ConfigDataGlobal (AbstractDataType):
    """Represents all configuration data that is global e.g. the
       command paths for generation. Note that this categorization is
       just for systematics, any configuration variable can be set per
       song."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _audioProcessorMapAliasName : ClassVar = "audioProcessor"

    _attributeNameList : ClassVar = \
        [ "aacCommandLine", "ffmpegCommand", "intermediateFileDirectoryPath",
          "lilypondCommand", "lilypondVersion", "loggingFilePath",
          "midiToWavRenderingCommandLine", "mp4boxCommand",
          "targetDirectoryPath", "tempAudioDirectoryPath",
          "tempLilypondFilePath", "videoTargetMap", "videoFileKindMap" ]

    _derivedAttributeNameList : ClassVar = [ "audioProcessorMap" ]

    _externalAttributeNameList : ClassVar = [ _audioProcessorMapAliasName ]

    _soundStyleNamePrefix : ClassVar = "soundStyle"

    _defaultAudioProcessorMap : ClassVar = \
        { "chainSeparator": ";", "mixingCommandLine" : "",
          "amplificationEffect" : "", "refinementCommandLine" : "",
          "paddingCommandLine": "", "redirector": "->" }

    #--------------------

    @classmethod
    def _makeAudioProcessorMap (cls,
                                st : String) -> StringMap:
        """Converts string <st> into audio processor map using defaults
           from <_defaultAudioProcessorMap>"""

        Logging.trace(">>: %s", st)

        result = {}
        externalMap = convertStringToMap(st)

        for key, value in cls._defaultAudioProcessorMap.items():
            result[key] = externalMap.get(key, value)

        Logging.trace("<<: %r", result)
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    aacCommandLine                : String    = ""
    audioProcessorMap             : StringMap = \
        specialField(None,
                     lambda st: _ConfigDataGlobal._makeAudioProcessorMap(st),
                     _audioProcessorMapAliasName)
    ffmpegCommand                 : String    = "ffmpeg"
    intermediateFileDirectoryPath : String    = "."
    lilypondCommand               : String    = "lilypond"
    lilypondVersion               : String    = "2.18"
    loggingFilePath               : String    = \
                                        ("/tmp/logs"
                                         + "/makeLilypondAll.log")
    midiToWavRenderingCommandLine : String    = "fluidsynth"
    mp4boxCommand                 : String    = ""
    soundStyleNameToTextMap       : StringMap = ""
    targetDirectoryPath           : String    = "."
    tempAudioDirectoryPath        : String    = "/tmp"
    tempLilypondFilePath          : String    = "./temp.ly"
    videoTargetMap                : StringMap = \
        specialField(None,
                     (lambda st :
                      generateObjectMapFromString(st,
                                                  VideoTarget())))
    videoFileKindMap              : StringMap = \
        specialField(None,
                     (lambda st :
                      generateObjectMapFromString(st,
                                                  VideoFileKind())))

    #--------------------
    #--------------------

    @classmethod
    def checkValidity (cls,
                       parameterNameToValueMap : StringMap):
        """Checks the validity of data to be read from
           <parameterNameToValueMap> for the global attributes in the
           ltbvc configuration"""

        Logging.trace(">>")

        relevantAttributeNameList = (cls._attributeNameList
                                     + cls._externalAttributeNameList)
        _LocalValidator.checkVariableList(relevantAttributeNameList,
                                          parameterNameToValueMap)

        # validate sound style definitions
        styleNamePrefix = cls._soundStyleNamePrefix
        soundStyleNameList = \
            _getStylesWithNamePrefix(styleNamePrefix,
                                     parameterNameToValueMap)

        for styleName in soundStyleNameList:
            _LocalValidator.checkVariable(styleName,
                                          parameterNameToValueMap,
                                          styleNamePrefix + "*")

        # validate audio processor map
        parameterName = cls._audioProcessorMapAliasName
        audioProcessorMapAsString = \
            parameterNameToValueMap.get(cls._audioProcessorMapAliasName)
        audioProcessorMap = convertStringToMap(audioProcessorMapAsString)
        apmGet = audioProcessorMap.get

        chainSeparator        = apmGet("chainSeparator", ";")
        mixingCommandLine     = apmGet("mixingCommandLine", "")
        amplificationEffect   = apmGet("amplificationEffect", "")
        paddingCommandLine    = apmGet("paddingCommandLine", "")
        redirector            = apmGet("redirector", "->")
        refinementCommandLine = apmGet("refinementCommandLine", "")

        Logging.trace("--: chainSep = %r, mixCmd = %r,"
                      + " amplifEffect = %r, padCmd = %r,"
                      + " redirector = %r, refCmd = %r",
                      chainSeparator, mixingCommandLine,
                      amplificationEffect, paddingCommandLine,
                      redirector, refinementCommandLine)

        ValidityChecker.isValid(chainSeparator > "",
            "'audioProcessor.chainSeparator' must be non-empty")
        ValidityChecker.isValid(amplificationEffect > "",
            "'audioProcessor.amplificationEffect' must be non-empty")
        ValidityChecker.isValid(redirector > "",
            "'audioProcessor.redirector' must be non-empty")
        ValidityChecker.isValid(refinementCommandLine > "",
            "'audioProcessor.refinementCommandLine' must be defined")

        # additional checks
        parameterName = "aacCommandLine"
        aacCommandLine = parameterNameToValueMap.get(parameterName)
        commandNameMap = { parameterName : aacCommandLine }

        for key, commandLine in audioProcessorMap.items():
            if key not in ["chainSeparator", "amplificationEffect",
                           "redirector"]:
                commandNameMap["audioProcessor." + key] = commandLine

        for parameterName, commandLine in commandNameMap.items():
            command, _, _ = commandLine.partition(" ")

            if command > "":
                ValidityChecker.isExecutableCommand(command, parameterName)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserialize (cls,
                     currentObject : Object,
                     parameterNameToValueMap : StringMap):
        """Deserializes global configuration data from strings in
           <parameterNameToValueMap> updating <currentObject>"""

        Logging.trace(">>")

        relevantAttributeNameList = (cls._attributeNameList
                                     + cls._externalAttributeNameList)
        localNameToValueMap = \
            _filterByKeyList(parameterNameToValueMap,
                             relevantAttributeNameList)
        DataTypeSupport.checkAndSetFromMap(currentObject,
                                           localNameToValueMap)
        SETATTR(currentObject, "soundStyleNameToTextMap",
                _readStylesWithPrefix(cls._soundStyleNamePrefix,
                                      parameterNameToValueMap))

        Logging.trace("<<")

#====================

@dataclass(frozen=True)
class _ConfigDataMidiHumanization (AbstractDataType):
    """Represents all configuration data that covers the MIDI
       humanization; single variable is a mapping from humanization
       style name to humanization style text"""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _attributeNameList : ClassVar = \
        [ "humanizationStyleNameToTextMap", "humanizedVoiceNameSet",
          "voiceNameToVariationFactorMap" ]

    _humanizationStyleNamePrefix : ClassVar = "humanizationStyle"

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    # -- attributes
    humanizationStyleNameToTextMap : StringMap = None
    humanizedVoiceNameSet          : StringMap = \
        specialField(frozenset(), lambda st : set(convertStringToList(st)))
    voiceNameToVariationFactorMap  : StringMap = \
        specialField(None,
                     (lambda st :
                      { voiceName : list(map(float, factors.split("/")))
                        for voiceName, factors
                            in convertStringToMap(st).items()}))

    #--------------------

    @classmethod
    def checkValidity (cls,
                       parameterNameToValueMap : StringMap):
        """Checks the validity of data to be read from
           <parameterNameToValueMap> for the midi humanization
           attributes"""

        Logging.trace(">>")

        relevantAttributeNameList = cls._attributeNameList
        _LocalValidator.checkVariableList(relevantAttributeNameList,
                                          parameterNameToValueMap)

        styleNamePrefix = cls._humanizationStyleNamePrefix
        humanizationStyleNameList = \
            _getStylesWithNamePrefix(styleNamePrefix,
                                     parameterNameToValueMap)

        for styleName in humanizationStyleNameList:
            _LocalValidator.checkVariable(styleName,
                                          parameterNameToValueMap,
                                          styleNamePrefix + "*")

        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserialize (cls,
                     currentObject : Object,
                     parameterNameToValueMap : StringMap):
        """Deserializes midi humanization configuration data from strings
           in <parameterNameToValueMap> updating <currentObject>"""

        Logging.trace(">>")

        relevantAttributeNameList = cls._attributeNameList
        localNameToValueMap = \
            _filterByKeyList(parameterNameToValueMap,
                             relevantAttributeNameList)
        DataTypeSupport.checkAndSetFromMap(currentObject,
                                           localNameToValueMap)
        SETATTR(currentObject, "humanizationStyleNameToTextMap",
                _readStylesWithPrefix(cls._humanizationStyleNamePrefix,
                                      parameterNameToValueMap))

        Logging.trace("<<")

#====================

@dataclass(frozen=True)
class _ConfigDataNotation (AbstractDataType):
    """Represents all configuration data that refers to the notation:
       this is the map from phase and voice name to the staff kind and
       the map from phase and voice name to the clef."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _attributeNameList : ClassVar = \
        [ "phaseAndVoiceNameToClefMap", "phaseAndVoiceNameToStaffListMap",
          "voiceNameToScoreNameMap" ]

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    phaseAndVoiceNameToClefMap      : StringMap = \
        specialField(None, lambda st : convertStringToMap(st))
    phaseAndVoiceNameToStaffListMap : StringMap = \
        specialField(None,
                     lambda st:
                     { phase : { voiceName :
                                 convertStringToList(staffListString, "/")
                                 for voiceName, staffListString
                                 in voiceNameToStaffListMap.items() }
                       for phase, voiceNameToStaffListMap
                       in convertStringToMap(st).items() })
    voiceNameToScoreNameMap         : StringMap = \
        specialField(None, lambda st : convertStringToMap(st))

    #--------------------

    @classmethod
    def checkValidity (cls,
                       parameterNameToValueMap : StringMap):
        """Checks the validity of data to be read from
           <parameterNameToValueMap> for the notation attributes"""

        Logging.trace(">>")
        relevantAttributeNameList = cls._attributeNameList
        _LocalValidator.checkVariableList(relevantAttributeNameList,
                                          parameterNameToValueMap)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserialize (cls,
                     currentObject : Object,
                     parameterNameToValueMap : StringMap):
        """Deserializes notation configuration data from strings
           in <parameterNameToValueMap> updating <currentObject>"""

        Logging.trace(">>")
        relevantAttributeNameList = cls._attributeNameList
        localNameToValueMap = \
            _filterByKeyList(parameterNameToValueMap,
                             relevantAttributeNameList)
        DataTypeSupport.checkAndSetFromMap(currentObject,
                                           localNameToValueMap)
        Logging.trace("<<")

#====================

@dataclass(frozen=True)
class _ConfigDataSong (AbstractDataType):
    """Represents all configuration data for a song like e.g. the voice names
       or the song title. Note that this categorization is just for
       systematics, any configuration variable can be set per song."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _attributeNameList : ClassVar = [
        "audioVoiceNameSet", "countInMeasureCount",
        "extractVoiceNameSet", "fileNamePrefix", "includeFilePath",
        "intermediateFilesAreKept", "measureToHumanizationStyleNameMap",
        "measureToTempoMap", "midiVoiceNameList", "scoreVoiceNameList",
        "title", "trackNumber", "voiceNameList","voiceNameToChordsMap",
        "voiceNameToLyricsMap", "voiceNameToOverrideFileNameMap",
        "voiceNameToVoiceDataMap"
    ]

    _derivedAttributeNameList : ClassVar = [
        "parallelTrackFilePath", "parallelTrackVolume", "shiftOffset",
        "songComposerText", "songYear"
    ]
    
    _externalAttributeNameList : ClassVar = [
        "parallelTrack", "composerText", "year"
    ]


    _defaultTempoSetting = (120, 4)  # 120 bpm, 4/4

    #--------------------

    @classmethod
    def _adjustVoiceAttributeList (cls,
                                   voiceAttributeNameToDataMap : Dictionary,
                                   attributeListName : String,
                                   value : String = None):
        """Sets data in attribute list named <attributeListName> within map
           <voiceAttributeNameToDataMap> to <value>; if value is not set,
           this is the midi channel list and it is set to appropriate
           heuristic values"""

        Logging.trace(">>: attributeList = %s, value = %r",
                      attributeListName, value)

        voiceNames = voiceAttributeNameToDataMap["voiceNameList"]
        voiceCount = cls._elementCountInString(voiceNames)

        if attributeListName not in voiceAttributeNameToDataMap:
            adjustmentIsNecessary = True
        else:
            attributeDataAsString = \
                voiceAttributeNameToDataMap[attributeListName]

            # if there are some elements, leave them as is and
            # possibly complain later about a wrong count
            adjustmentIsNecessary = (attributeDataAsString.strip() == "")

        if adjustmentIsNecessary:
            if value is not None:
                correctValue = (value + ", ")  * (voiceCount - 1) + value
            else:
                voiceNameList = convertStringToList(voiceNames)
                correctValue = ""

                if attributeListName == "midiChannelList":
                    midiChannelList = [  1,  2,  3,  4,  5,  6, 7, 8, 9,
                                        11, 12, 13, 14, 15, 16]
                    j = 0

                    for voiceName in voiceNameList:
                        isDrumVoice = (voiceName in ("drums", "percussion"))
                        correctValue += (iif(j > 0, ", ", "")
                                         + iif(isDrumVoice, "10",
                                               str(midiChannelList[j])))
                        j += iif(j == 14 or isDrumVoice, 0, 1)
                else:
                    voiceToInstrumentMap = {
                        "bass" : "34", "brass" : "56", "guitar" : "26",
                        "organ" : "18", "reed" : "64", "strings" : "48",
                        "synthesizer" : "80", "vocals" : "54" }

                    for voiceName in voiceNameList:
                        correctValue += (iif(i > 0, ", ", "")
                                         + voiceToInstrumentMap.get(voiceName,
                                                                    "0"))

            # set associated data to correct value
            voiceAttributeNameToDataMap[attributeListName] = correctValue
            Logging.trace("--: correct value = %r", correctValue)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _checkStringLists (cls,
                           voiceNames : String,
                           midiChannels : String,
                           midiInstruments : String,
                           midiVolumes : String,
                           panPositions : String,
                           reverbLevels : String,
                           soundVariants : String):
        """Checks whether data for voice list and voice data read from
           configuration file is okay."""

        Logging.trace(">>: voiceNames = %r, midiChannels = %r,"
                      + " midiInstruments = %r, midiVolumes = %r,"
                      + " panPositions = %r, reverbLevels = %r,"
                      + " soundVariants = %r",
                      voiceNames, midiChannels, midiInstruments,
                      midiVolumes, panPositions, reverbLevels,
                      soundVariants)

        checkForRequiredLength = (lambda st, valueName, elementCount:
            ValidityChecker.isValid(cls._elementCountInString(st)
                                    in (1, elementCount),
                                    ("%r must contain %d elements"
                                     + " to match 'voiceNameList'")
                                    % (valueName, elementCount)))

        voiceCount = cls._elementCountInString(voiceNames)
        checkForRequiredLength(midiChannels, "midiChannelList", voiceCount)
        checkForRequiredLength(midiInstruments, "midiInstrumentList",
                               voiceCount)
        checkForRequiredLength(midiVolumes, "midiVolumeList", voiceCount)
        checkForRequiredLength(panPositions, "panPositionList", voiceCount)
        checkForRequiredLength(soundVariants, "soundVariantList", voiceCount)
        checkForRequiredLength(reverbLevels, "reverbLevelList", voiceCount)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _convertStringToRealMap (cls,
                                 st : String) -> Map:
        """Reads map from <st> and changes its keys of to real"""

        Logging.trace(">>: st = %r", st)
        currentMap = convertStringToMap(st)
        result = { adaptToKind(key, "R") : value
                   for (key, value) in currentMap.items() }
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def _convertToVoiceMap (self,
                            voiceNames : String,
                            midiChannels : String,
                            midiInstruments : String,
                            midiVolumes : String,
                            panPositions : String,
                            reverbLevels : String,
                            soundVariants : String) -> Tuple:
        """Converts strings read from configuration file to voice name
           list and a map from voice names to voice descriptors"""

        Logging.trace(">>: voiceNames = %r, midiChannels = %r,"
                      + " midiInstruments = %r, midiVolumes = %r,"
                      + " panPositions = %r, reverbLevels = %r,"
                      + " soundVariants = %r",
                      voiceNames, midiChannels, midiInstruments,
                      midiVolumes, panPositions, reverbLevels,
                      soundVariants)

        voiceNameList = convertStringToList(voiceNames)

        midiChannelList    = convertStringToList(midiChannels, kind="I")
        midiInstrumentList = convertStringToList(midiInstruments)
        midiVolumeList     = convertStringToList(midiVolumes, kind="I")
        panPositionList    = convertStringToList(panPositions)
        reverbLevelList    = convertStringToList(reverbLevels, kind="R")
        soundVariantList   = convertStringToList(soundVariants)

        voiceNameToVoiceDataMap = {}

        for i, voiceName in enumerate(voiceNameList):
            voiceDescriptor = VoiceDescriptor()
            voiceDescriptor.voiceName      = voiceName
            voiceDescriptor.midiChannel    = midiChannelList[i]
            voiceDescriptor.midiInstrument = midiInstrumentList[i]
            voiceDescriptor.midiVolume     = midiVolumeList[i]
            voiceDescriptor.panPosition    = panPositionList[i]
            voiceDescriptor.reverbLevel    = reverbLevelList[i]
            voiceDescriptor.soundVariant   = soundVariantList[i]
            voiceNameToVoiceDataMap[voiceName] = voiceDescriptor

        result = (voiceNameList, voiceNameToVoiceDataMap)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _convertTargetMapping (cls,
                               mapAsString : String,
                               isLyricsMap : Boolean) -> StringMap:
        """Prepares a map from voice name to lyrics or chord data
           (depending on <isLyricsMap>) based on data in
           <mapAsString>; voice names for lyrics map to a mapping from
           target to lyrics line count, voice names for chords map to
           sets of targets"""

        Logging.trace(">>: map = %r, isLyrics = %r",
                      mapAsString, isLyricsMap)

        targetAbbrevToNameMap = { "e": "extract", "m": "midi",
                                  "s": "score",   "v": "video" }
        currentMap = convertStringToMap(mapAsString)

        if currentMap is None:
            result = None
        else:
            result = {}

            for voiceName, value in currentMap.items():
                entry = iif(isLyricsMap, {}, set())
                targetList = value.split("/")
                Logging.trace("--: targetList(%r) = %r",
                              voiceName, targetList)

                for targetSpec in targetList:
                    targetSpec = targetSpec.strip()

                    if len(targetSpec) > 0:
                        target, rest = targetSpec[0], targetSpec[1:]
                        Logging.trace("--: target = %r", target)

                        if target in "emsv":
                            target = targetAbbrevToNameMap[target]

                            if not isLyricsMap:
                                entry.update([ target ])
                            else:
                                if rest == "":
                                    rest = "1"

                                entry[target] = int(rest)

                result[voiceName] = entry

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _elementCountInString (cls,
                               st : String) -> Natural:
        """Returns count of comma-separated elements in <st>"""

        return len(st.strip().split(","))

    #--------------------

    @classmethod
    def _splitParallelTrackInfo (cls,
                                 parallelTrackInfo : String) -> Tuple:
        """Splits string <parallelTrackInfo> given for parallel track
           into file path, track volume and shift offset"""

        Logging.trace(">>: %r", parallelTrackInfo)

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

        parallelTrackFilePath = partList[0].strip()
        parallelTrackVolume   = float(partList[1])
        shiftOffset           = float(partList[2])
        result = (parallelTrackFilePath, parallelTrackVolume, shiftOffset)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _stringToTempoMap (cls,
                           st : String) -> Map:
        """Returns a tempo map constructed from <st> which maps the measure
           into a pair of tempo and measure length in quarters"""

        Logging.trace(">>: %s", st)

        tempoMap = { adaptToKind(key, "R") : value
                     for key, value in convertStringToMap(st).items() }

        for key, value in tempoMap.items():
            if "|" not in value:
                tempo, fractionString = value, "4/4"
            else:
                tempo, fractionString = value.split("|")

            tempo = float(tempo)
            numerator, denominator = fractionString.split("/")
            signatureFraction = float(numerator) / float(denominator)
            measureLengthInQuarters = round(4.0 * signatureFraction, 5)
            tempoMap[key] = (tempo, measureLengthInQuarters)

        Logging.trace("<<: %r", tempoMap)
        return tempoMap

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    audioVoiceNameSet                 : StringSet = \
        specialField(frozenset(), lambda st : set(convertStringToList(st)))
    countInMeasureCount               : Natural = 0
    extractVoiceNameSet               : StringSet = \
        specialField(frozenset(), lambda st : set(convertStringToList(st)))
    fileNamePrefix                    : String = "XXXX"
    includeFilePath                   : String = ""
    intermediateFilesAreKept          : Boolean = False
    measureToHumanizationStyleNameMap : StringMap = \
        specialField(None,
                     lambda st: _ConfigDataSong._convertStringToRealMap(st))
    measureToTempoMap                 : Map = \
        specialField(None, lambda st: _ConfigDataSong._stringToTempoMap(st))
    midiVoiceNameList                 : StringList = \
        specialField((), convertStringToList)
    parallelTrackFilePath             : String = \
        specialField("",
                     lambda st: _ConfigDataSong._splitParallelTrackInfo(st)[0],
                     "parallelTrack",
                     lambda st: st.split(",")[0].strip())
    parallelTrackVolume               : Real = \
        specialField(0.0,
                     lambda st: _ConfigDataSong._splitParallelTrackInfo(st)[1],
                     "parallelTrack",
                     lambda st: st.split(",")[1].strip())
    scoreVoiceNameList                : StringList = \
        specialField((), convertStringToList)
    shiftOffset                       : Real =  \
        specialField(0.0,
                     lambda st: _ConfigDataSong._splitParallelTrackInfo(st)[2],
                     "parallelTrack",
                     lambda st: st.split(",")[2].strip())
    songComposerText                  : String = specialField("", None,
                                                              "composerText")
    songYear                          : Natural = specialField(0, None,
                                                               "year")
    title                             : String = "%title%"
    trackNumber                       : Natural = 0
    voiceNameList                     : StringList = \
        specialField((), convertStringToList)
    voiceNameToChordsMap              : StringMap = \
        specialField(None,
                     lambda st: _ConfigDataSong._convertTargetMapping(st,
                                                                      False))
    voiceNameToLyricsMap              : StringMap = \
        specialField(None,
                     lambda st: _ConfigDataSong._convertTargetMapping(st,
                                                                      True))
    voiceNameToOverrideFileNameMap    : StringMap = \
        specialField(None, convertStringToMap)
    voiceNameToVoiceDataMap           : StringMap = None

    #--------------------

    @classmethod
    def checkValidity (cls,
                       parameterNameToValueMap : StringMap):
        """Checks the validity of data to be read from
           <parameterNameToValueMap> for the song attributes"""

        Logging.trace(">>")

        relevantAttributeNameList = (cls._attributeNameList
                                     + cls._externalAttributeNameList)
        _LocalValidator.checkVariableList(relevantAttributeNameList,
                                          parameterNameToValueMap)

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              parameterNameToValueMap)

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
                              getValueProc("reverbLevelList"),
                              getValueProc("soundVariantList"))

        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserialize (cls,
                     currentObject : Object,
                     parameterNameToValueMap : StringMap):
        """Deserializes notation configuration data from strings in
           <parameterNameToValueMap> updating <currentObject>"""

        Logging.trace(">>")

        relevantAttributeNameList = (cls._attributeNameList
                                     + cls._externalAttributeNameList)
        localNameToValueMap = \
            _filterByKeyList(parameterNameToValueMap,
                             relevantAttributeNameList)
        DataTypeSupport.checkAndSetFromMap(currentObject,
                                           localNameToValueMap)

        getValueProc = \
            lambda name : _LocalValidator.get(name,
                                              parameterNameToValueMap)

        if currentObject.includeFilePath == "":
            SETATTR(currentObject, "includeFilePath",
                    currentObject.fileNamePrefix + "-music.ly")

        if currentObject.measureToTempoMap is None:
            SETATTR(currentObject, "measureToTempoMap", {})

        if 1 not in currentObject.measureToTempoMap:
            currentObject.measureToTempoMap[1] = cls._defaultTempoSetting
            
        # the string representation for the parallel track is stored
        # in <parallelTrackInfo>
        parallelTrackInfo = getValueProc("parallelTrack")
        parallelTrackFilePath, parallelTrackVolume, shiftOffset = \
            cls._splitParallelTrackInfo(parallelTrackInfo)
        SETATTR(currentObject, "parallelTrackFilePath", parallelTrackFilePath)
        SETATTR(currentObject, "parallelTrackVolume",   parallelTrackVolume)
        SETATTR(currentObject, "shiftOffset",           shiftOffset)

        c = dict(parameterNameToValueMap)

        # if the different sublists are not defined, they will be set to
        # defaults with the same count as the voice names
        voiceCount = cls._elementCountInString(c["voiceNameList"])
        cls._adjustVoiceAttributeList(c, "midiChannelList")
        cls._adjustVoiceAttributeList(c, "midiInstrumentList", "0")
        cls._adjustVoiceAttributeList(c, "midiVolumeList", "80")
        cls._adjustVoiceAttributeList(c, "panPositionList", "C")
        cls._adjustVoiceAttributeList(c, "reverbLevelList", "0")
        cls._adjustVoiceAttributeList(c, "soundVariantList", "COPY")

        # the voice data map is synthesized from several lists
        voiceNameList, vnToDataMap = \
            currentObject._convertToVoiceMap(c["voiceNameList"],
                                             c["midiChannelList"],
                                             c["midiInstrumentList"],
                                             c["midiVolumeList"],
                                             c["panPositionList"],
                                             c["reverbLevelList"],
                                             c["soundVariantList"])

        SETATTR(currentObject, "voiceNameList", voiceNameList)
        SETATTR(currentObject, "voiceNameToVoiceDataMap", vnToDataMap)

        # adapt the different lists (when empty)
        def updateListProc (attributeName, otherList):
            value = getattr(currentObject, attributeName)
            if value is not None and len(value) == 0:
                SETATTR(currentObject, attributeName, otherList)

        updateListProc("extractVoiceNameSet", set(voiceNameList))
        updateListProc("midiVoiceNameList", list(voiceNameList))
        updateListProc("scoreVoiceNameList", list(voiceNameList))
        updateListProc("audioVoiceNameSet",
                       set(currentObject.midiVoiceNameList))

        Logging.trace("<<: %r", currentObject)

#====================

@dataclass(frozen=True)
class _ConfigDataSongGroup (AbstractDataType):
    """Represents all configuration data that is considered to be
       related to group of songs like e.g. the name of an album or the
       artist for generation. Note that this categorization is
       just for systematics, any configuration variable can be set per
       song."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _attributeNameList : ClassVar = [
        "albumArtFilePath", "albumName", "artistName",
        "audioTargetDirectoryPath", "audioTrackList",
        "targetFileNamePrefix"
    ]

    _derivedAttributeNameList : ClassVar = [
        "audioGroupNameToVoiceNameSetMap"
    ]

    _externalAttributeNameList : ClassVar = [
        "audioGroupToVoicesMap"
    ]
    
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    albumArtFilePath                : String = ""
    albumName                       : String = ""
    artistName                      : String = ""
    audioGroupNameToVoiceNameSetMap : StringMap = \
        specialField(None,
                     (lambda st:
                      { audioGroupName :
                            set(convertStringToList(voiceNames, "/"))
                        for audioGroupName, voiceNames
                        in convertStringToMap(st).items() }),
                     "audioGroupToVoicesMap")
    audioTargetDirectoryPath        : String = "."
    audioTrackList                  : ObjectList = \
        specialField((),
                     lambda st: generateObjectListFromString(st,
                                                             AudioTrack()))
    targetFileNamePrefix            : String = ""

    #--------------------
    #--------------------

    @classmethod
    def checkValidity (cls,
                       parameterNameToValueMap : StringMap):
        """Checks the validity of data to be read from
           <parameterNameToValueMap> for the song group attributes"""

        Logging.trace(">>")
        relevantAttributeNameList = (cls._attributeNameList
                                     + cls._externalAttributeNameList)
        _LocalValidator.checkVariableList(relevantAttributeNameList,
                                          parameterNameToValueMap)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def deserialize (cls,
                     currentObject : Object,
                     parameterNameToValueMap : StringMap):
        """Deserializes song group configuration data from strings in
           <parameterNameToValueMap> updating <currentObject>"""

        Logging.trace(">>")
        relevantAttributeNameList = (cls._attributeNameList
                                     + cls._externalAttributeNameList)
        localNameToValueMap = \
            _filterByKeyList(parameterNameToValueMap,
                             relevantAttributeNameList)
        DataTypeSupport.checkAndSetFromMap(currentObject,
                                           localNameToValueMap)
        Logging.trace("<<")

#====================

@dataclass(frozen=True)
class LTBVC_ConfigurationData (_ConfigDataGlobal,
                               _ConfigDataNotation,
                               _ConfigDataMidiHumanization,
                               _ConfigDataSong,
                               _ConfigDataSongGroup):
    """This class encapsulates the settings read from a configuration
       file like e.g. the global commands for ffmpeg, sox, etc. as
       well as file name templates and specifically the song
       configuration data."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _configurationFile : ConfigurationFile = \
        dataclasses.field(default=None, repr = False)

    #--------------------

    _homeDirectoryPath   : ClassVar[String] = \
        OperatingSystem.homeDirectoryPath()
    _scriptFilePath      : ClassVar[String] = \
        OperatingSystem.scriptFilePath()
    _scriptDirectoryPath : ClassVar[String] = \
        OperatingSystem.dirname(_scriptFilePath)

    #--------------------

    def _addMissingSettingsFromDefaults \
        (self,
         parameterNameToValueMap : StringMap) -> StringMap:
        """Adds defaults values for parameters not in
           <parameterNameToValueMap> and returns resulting map"""

        Logging.trace(">>: %r", parameterNameToValueMap)

        defaultKeyList = _DefaultValueHandler.parameterNameList()
        unsetKeyList = defaultKeyList - parameterNameToValueMap.keys()
        result = parameterNameToValueMap.copy()

        for key in unsetKeyList:
            result[key] = _DefaultValueHandler.value(key)
        
        Logging.trace("<<: %r", result)
        return result
    
    #--------------------

    def _checkValidity (self,
                        parameterNameToValueMap : StringMap):
        """Checks whether all data in <parameterNameToValueMap> is okay"""

        Logging.trace(">>")

        _ConfigDataGlobal.checkValidity(parameterNameToValueMap)
        _ConfigDataNotation.checkValidity(parameterNameToValueMap)
        _ConfigDataMidiHumanization.checkValidity(parameterNameToValueMap)
        _ConfigDataSong.checkValidity(parameterNameToValueMap)
        _ConfigDataSongGroup.checkValidity(parameterNameToValueMap)

        Logging.trace("<<")

    #--------------------

    def _constructAdvancedDefaults (self):
        """Constructs additional defaults  updating <self>"""

        Logging.trace(">>")

        # workaround for missing frozenmap
        criticalAttributeNameList = [
            "audioGroupNameToVoiceNameSetMap", "audioProcessorMap",
            "measureToHumanizationStyleNameMap", "measureToTempoMap",
            "phaseAndVoiceNameToClefMap", "phaseAndVoiceNameToStaffListMap",
            "videoFileKindMap", "videoTargetMap", "voiceNameToChordsMap",
            "voiceNameToLyricsMap", "voiceNameToOverrideFileNameMap",
            "voiceNameToScoreNameMap", "voiceNameToVariationFactorMap" ]

        for attributeName in criticalAttributeNameList:
            if getattr(self, attributeName) is None:
                Logging.trace("--: setting %s to empty", attributeName)
                SETATTR(self, attributeName, {})

        # adapt several parameters when unset
        voiceNameList = self.voiceNameList

        # adapt video file kind
        for kindName, videoFileKind in self.videoFileKindMap.items():
            if len(videoFileKind.voiceNameList) == 0:
                Logging.trace("--: setting voice list for %s to all voices",
                              kindName)
                SETATTR(videoFileKind, "voiceNameList", list(voiceNameList))

        # when there is no audio group defined, provide a single group
        # "all" with all voices
        if len(self.audioGroupNameToVoiceNameSetMap) == 0:
            Logging.trace("--: adding an artificial 'all' audio group")
            self.audioGroupNameToVoiceNameSetMap["all"] = \
                set(voiceNameList)

        # when there is no audio track defined, take the first entry
        # in audioGroupNameToVoiceNameSetMap and make a track for that
        if len(self.audioTrackList) == 0:
            Logging.trace("--: ")
            audioGroupName = \
                list(self.audioGroupNameToVoiceNameSetMap.keys())[0]
            audioLevelMap = { voiceName : 1.0
                              for voiceName in voiceNameList }
            audioTrack = \
                AudioTrack(audioGroupList=[audioGroupName],
                           albumName=self.albumName,
                           voiceNameToAudioLevelMap=audioLevelMap)
            SETATTR(self, "audioTrackList", [ audioTrack ])

        Logging.trace("<<")

    #--------------------

    def _deserialize (self,
                      parameterNameToValueMap : StringMap,
                      selectedVoiceNameSet : StringSet):
        """Deserializes all configuration data from strings in
           <parameterNameToValueMap> updating <self>"""

        Logging.trace(">>")

        _ConfigDataGlobal.deserialize(self, parameterNameToValueMap)
        _ConfigDataMidiHumanization.deserialize(self,
                                                parameterNameToValueMap)
        _ConfigDataNotation.deserialize(self, parameterNameToValueMap)
        _ConfigDataSong.deserialize(self, parameterNameToValueMap)
        _ConfigDataSongGroup.deserialize(self, parameterNameToValueMap)
        self._constructAdvancedDefaults()

        if len(selectedVoiceNameSet) == 0:
            # when no voices are selected so far, all voices will be
            # used
            selectedVoiceNameSet.update(self.voiceNameList)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        Logging.trace(">>")
        _LocalValidator.initialize()
        SETATTR(self, "_configurationFile", None)
        Logging.trace("<<: %r", self)

    #--------------------

    def __repr__ (self) -> String:
        """Returns the string representation of <self>"""

        return DataTypeSupport.convertToString(self)

    #--------------------

    def checkAndSetDerivedVariables (self,
                                     selectedVoiceNameSet : StringSet):
        """Checks data from configuration file read into <self>;
           <selectedVoiceNameSet> gives the set of voices selected
           for processing"""

        Logging.trace(">>")

        parameterNameToValueMap = self._configurationFile.asStringMap()
        parameterNameToValueMap = \
            self._addMissingSettingsFromDefaults(parameterNameToValueMap)

        self._checkValidity(parameterNameToValueMap)
        self._deserialize(parameterNameToValueMap, selectedVoiceNameSet)

        Logging.trace("<<: %r", self)

    #--------------------

    def get (self,
             parameterName : String) -> String:
        """Gets data from configuration file read into <self> at
           <parameterName>"""

        Logging.trace(">>: %r", parameterName)

        parameterNameToValueMap = self._configurationFile.asDictionary()
        result = _LocalValidator.get(parameterName,
                                     parameterNameToValueMap)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def readFile (self,
                  configurationFilePath : String):
        """Reads data from configuration file with
           <configurationFilePath> into <self>"""

        Logging.trace(">>: %r", configurationFilePath)

        cls = self.__class__

        separator = OperatingSystem.pathSeparator
        configSuffix = separator + "config"

        Logging.trace("--: scriptFilePath = %r, scriptDirectory = %r,"
                      + " homeDirectory = %r",
                      cls._scriptFilePath, cls._scriptDirectoryPath,
                      cls._homeDirectoryPath)

        searchPathList = \
          [ cls._homeDirectoryPath + separator + ".ltbvc" + configSuffix,
            cls._scriptDirectoryPath + "/../.." + configSuffix ]
        ConfigurationFile.setSearchPaths(searchPathList)
        file = ConfigurationFile(configurationFilePath)
        SETATTR(self, "_configurationFile", file)

        Logging.trace("<<")
        return file
