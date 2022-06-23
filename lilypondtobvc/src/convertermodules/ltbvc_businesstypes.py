# ltbvc_businesstypes -- services for several simple business types for the
#                        lilypond to band video converter that are used
#                        across modules:
#
#                          - AudioTrack
#                          - MidiTrackSettings
#                          - TempoTrack
#                          - VideoFileKind
#                          - VideoTarget
#                          - VoiceDescriptor
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

from dataclasses import dataclass

from basemodules.datatypesupport import AbstractDataType, \
                                        DataTypeSupport, specialField, \
                                        SETATTR
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, Integer, \
                                    Map, Object, Real, RealList, \
                                    String, StringList, StringMap
from basemodules.stringutil import deserializeToList, deserializeToMap, \
                                   tokenize
from basemodules.ttbase import adaptToRange, iif, iif2
from basemodules.validitychecker import ValidityChecker

#====================
# PRIVATE FEATURES
#====================

def _adaptMixSettingsMap (inputMap : StringMap) -> StringMap:
    """Adapts map <inputMap> containing mix settings into a map from voice
       name to pairs of volume and pan settings"""

    Logging.trace(">>: %s", inputMap)

    separator = "/"
    result = {}

    for voiceName, mixSettings in inputMap.items():
        if separator not in mixSettings:
            volume      = float(mixSettings)
            panPosition = None
        else:
            firstPart, lastPart = mixSettings.split(separator)
            volume = float(firstPart)
            panPosition = panPositionStringToReal(lastPart)

        result[voiceName] = (volume, panPosition)
    
    Logging.trace("<<: %s", result)
    return result

#====================
# PUBLIC FEATURES
#====================

def humanReadableVoiceName (voiceName : String) -> String:
    """Returns human readable version of given <voiceName>"""

    result = iif2(voiceName.endswith("Simple"), voiceName[:-6],
                  voiceName.endswith("Extended"), voiceName[:-8],
                  voiceName)
    return result

#--------------------

def panPositionStringToReal (st : String) -> Real:
    """Converts <st> to pan position between -1 and 1 assuming string is
       correctly formatted"""

    Logging.trace(">>: %r", st)

    st = st.upper()

    if st == "C":
        result = 0
    else:
        suffix = st[-1]
        value = float(st[0:-1])
        result = iif(suffix == "L", -value, value)
    
    Logging.trace("<<: %r", result)
    return result

#====================

@dataclass(frozen=True)
class AudioTrack (AbstractDataType):
    """Represents information about the audio tracks combining audio
       groups together with all their properties."""

    name                     : String     = ""
    audioGroupList           : StringList = \
                                   specialField((),
                                                (lambda st:
                                                 deserializeToList(st,
                                                                   "/")))
    audioFileTemplate        : String     = "$"
    songNameTemplate         : String     = "$"
    albumName                : String     = "[ALBUM NAME]"
    description              : String     = ""
    languageCode             : String     = "eng"
    voiceNameToMixSettingMap : StringMap  = \
                                   specialField(None,
                                                _adaptMixSettingsMap)
    masteringEffectList      : StringList = specialField((), tokenize)
    amplificationLevel       : Real       = 0.0
    
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

        Logging.trace(">>: %r", tempoMap)

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
                                               realIsAllowed=True,
                                               rangeKind=">0")
                measureLength = float(measureLength)

            ValidityChecker.isNumberString(tempo, "tempo track tempo",
                                           realIsAllowed=True,
                                           rangeKind=">0")
            tempo = float(tempo)

            Logging.trace("--: tempo - %d -> %f/%f",
                          measure, measureLength, tempo)
            result[measure] = (tempo, measureLength)

        Logging.trace("<<: %r", result)
        return result

#====================

@dataclass(frozen=True)
class MidiTrackSettings (AbstractDataType):
    """Represents the settings of a MIDI track"""

    voiceName          : String
    midiChannel        : Integer
    midiInstrumentBank : Integer
    midiInstrument     : Integer
    midiVolume         : Integer
    midiPanPosition    : Integer
    midiReverbLevel    : Integer
    
    #--------------------    

    def __post_init__ (self):
        """Adapts attributes to MIDI ranges"""

        rangeAdjustProc = (lambda attributeName, maximumValue:
                           SETATTR(self, attributeName,
                                   adaptToRange(getattr(self, attributeName),
                                                0, maximumValue)))

        rangeAdjustProc("midiChannel", 15)
        rangeAdjustProc("midiInstrumentBank", 127)
        rangeAdjustProc("midiInstrument", 127)
        rangeAdjustProc("midiVolume", 127)
        rangeAdjustProc("midiPanPosition", 127)
        rangeAdjustProc("midiReverbLevel", 127)

#====================

@dataclass(frozen=True)
class VideoFileKind (AbstractDataType):
    """This class encapsulates the settings for a video file kind used
       for video generation."""

    name           : String     = ""
    target         : String     = ""
    fileNameSuffix : String     = ""
    directoryPath  : String     = ""
    voiceNameList  : StringList = specialField((),
                                               deserializeToList)

#====================

@dataclass(frozen=True)
class VideoTarget (AbstractDataType):
    """This class encapsulates the settings for a video target used
       for video generation."""

    name                  : String  = ""
    resolution            : Integer = 0
    height                : Integer = 0
    width                 : Integer = 0
    topBottomMargin       : Real    = 0.0
    leftRightMargin       : Real    = 0.0
    systemSize            : Real    = 20.0
    scalingFactor         : Integer = 1
    mediaType             : String  = "Normal"
    frameRate             : Real    = 1.0
    ffmpegPresetName      : String  = ""
    subtitleColor         : Integer = 0
    subtitleFontSize      : Real    = 1
    subtitlesAreHardcoded : Boolean = True

#====================

@dataclass(frozen=False)
class VoiceDescriptor (AbstractDataType):
    """Type representing all data for generation of a single voice"""

    voiceName      : String  = ""
    midiChannel    : Integer = 0
    midiInstrument : Integer = 0
    midiVolume     : Integer = 0
    panPosition    : Real    = 0  # in range -1 to +1
    reverbLevel    : Real    = 0  # in range 0 to 1
    soundVariant   : String  = ""
