# mla_songconfigurationdata -- services for access to the song-specific
#                              configuration file of makeLilypondAll

#====================

from configurationfile import ConfigurationFile
from simplelogging import Logging
from ttbase import convertStringToList, iif
from validitychecker import ValidityChecker

#====================
# TYPE DEFINITIONS
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

class MLA_SongConfigurationData:
    """Handles the data within the song configuration file and checks
       it; sets object variables accordingly"""

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

    def _checkValidity (self):
        """Checks whether all data read from configuration file is
           okay."""

        Logging.trace(">>")

        # type checks
        ValidityChecker.isReadableFile(self.includeFileName,
                                       "includeFileName")
        ValidityChecker.isString(self.title, "title")
        ValidityChecker.isString(self.fileNamePrefix, "fileNamePrefix")
        ValidityChecker.isNatural(self.year, "year")
        ValidityChecker.isBoolean(self.debuggingIsActive, "debuggingIsActive")
        ValidityChecker.isNatural(self.lyricsCountVocals, "lyricsCountVocals")
        ValidityChecker.isNatural(self.lyricsCountVocalsStandalone,
                                  "lyricsCountVocalsStandalone")
        ValidityChecker.isNatural(self.lyricsCountBgVocals,
                                  "lyricsCountBgVocals")
        ValidityChecker.isNatural(self.lyricsCountBgVocalsStandalone,
                                  "lyricsCountBgVocalsStandalone")
        ValidityChecker.isBoolean(self.useSpecialLayoutForExtracts,
                                  "useSpecialLayoutForExtracts")
        ValidityChecker.isString(self.styleHumanizationKind,
                                 "styleHumanizationKind")
        ValidityChecker.isString(self.humanizedVoiceNameList,
                                 "humanizedVoiceNameList")
        ValidityChecker.isString(self.tempoTrackLineList,
                                 "tempoTrackLineList")
        ValidityChecker.isFloat(self.attenuationLevel, "attenuationLevel")

        # additional rules
        ValidityChecker.isValid(" " not in self.fileNamePrefix,
                   "'fileNamePrefix' must not contain blanks")
        ValidityChecker.isValid(self.year >= 2010,
                   "'year' must be in a reasonable range")

        Logging.trace("<<")

    #--------------------

    def _convertToVoiceMap (self, voiceNames, midiChannels, midiInstruments,
                            midiVolumes, panPositions, audioVolumes,
                            reverbLevels, soundVariants):
        """Converts strings read from configuration file to voice name
           list and map to voice descriptors"""

        Logging.trace(">>")

        self.voiceNameList = convertStringToList(voiceNames)

        midiChannelList    = convertStringToList(midiChannels, kind="I")
        midiInstrumentList = convertStringToList(midiInstruments, kind="I")
        midiVolumeList     = convertStringToList(midiVolumes, kind="I")
        panPositionList    = convertStringToList(panPositions)
        audioVolumeList    = convertStringToList(audioVolumes)
        reverbLevelList    = convertStringToList(reverbLevels, kind="F")
        soundVariantList   = convertStringToList(soundVariants)

        self.voiceNameToVoiceDataMap = {}

        for i in xrange(len(self.voiceNameList)):
            voiceDescriptor = _VoiceDescriptor()
            voiceName = self.voiceNameList[i]
            voiceDescriptor.voiceName      = voiceName
            voiceDescriptor.midiChannel    = midiChannelList[i]
            voiceDescriptor.midiInstrument = midiInstrumentList[i]
            voiceDescriptor.midiVolume     = midiVolumeList[i]
            voiceDescriptor.panPosition    = panPositionList[i]
            voiceDescriptor.audioVolume    = audioVolumeList[i]
            voiceDescriptor.reverbLevel    = reverbLevelList[i]
            voiceDescriptor.soundVariant   = soundVariantList[i]
            self.voiceNameToVoiceDataMap[voiceName] = voiceDescriptor

        Logging.trace("<<")

    #--------------------

    def _splitOverrideInfo (self, overrideFiles):
        """Converts string <overrideFiles> to mapping from voice name
           to override file name"""

        Logging.trace(">>: %s", overrideFiles)

        result = {}
        overridePartList = overrideFiles.split(",")

        for part in overridePartList:
            part = part.strip()

            if part > "":
                voiceName, overrideFileName = part.split(":")
                result[voiceName] = overrideFileName
                Logging.trace("--: %s -> %s", voiceName, overrideFileName)

        Logging.trace("<<: %s", str(result))
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        self.title = "%title%"
        self.fileNamePrefix = "XXXX"
        self.includeFileName = "%includeFileName%"
        self.year = 2017
        self.debuggingIsActive = False
        self.lyricsCountVocals = 0
        self.lyricsCountVocalsStandalone = 0
        self.lyricsCountBgVocals = 0
        self.lyricsCountBgVocalsStandalone = 0
        self.useSpecialLayoutForExtracts = False
        self.styleHumanizationKind = None
        self.humanizedVoiceNameList = None
        self.voiceNameList         = ""
        self.voiceNameToVoiceDataMap = ""
        self.voiceNameToOverrideFileMap = {}
        self.tempoTrackLineList = ""
        self.attenuationLevel = 0

    #--------------------

    def __str__ (self):
        st = (("_SongConfigurationData("
               + "title = '%s', fileNamePrefix = %s,"
               + " includeFileName = '%s', year = %d, debuggingIsActive = %s,"
               + " lyricsCountVocals = %d, lyricsCountVocalsStandalone = %d,"
               + " lyricsCountBgVocals = %d,"
               + " lyricsCountBgVocalsStandalone = %d,"
               + " useSpecialLayoutForExtracts = %s,"
               + " styleHumanizationKind = %s, humanizedVoiceNameList = %s,"
               + " voiceNameList = %s, voiceNameToVoiceDataMap = %s,"
               + " voiceNameToOverrideFileMap = %s, tempoTrackLineList = %s,"
               + " attenuationLevel = %5.3f)")
              % (self.title, self.fileNamePrefix, self.includeFileName,
                 self.year, self.debuggingIsActive,
                 self.lyricsCountVocals, self.lyricsCountVocalsStandalone,
                 self.lyricsCountBgVocals, self.lyricsCountBgVocalsStandalone,
                 self.useSpecialLayoutForExtracts, self.styleHumanizationKind,
                 self.humanizedVoiceNameList, self.voiceNameList,
                 self.voiceNameToVoiceDataMap, self.voiceNameToOverrideFileMap,
                 self.tempoTrackLineList, self.attenuationLevel))
        return st

    #--------------------

    def readFile (self, configurationFileName, selectedVoiceNameList):
        """Reads data from configuration file with
           <configurationFileName> into <self>."""

        Logging.trace(">>: '%s'", configurationFileName)

        configurationFile = ConfigurationFile(configurationFileName)
        getValueProc = configurationFile.getValue

        # read all values
        self.title = getValueProc("title", True)
        self.fileNamePrefix = getValueProc("fileNamePrefix", True)
        self.includeFileName = self.fileNamePrefix + "-music.ly"
        self.year = getValueProc("year", True)
        self.debuggingIsActive = getValueProc("debuggingIsActive")
        self.lyricsCountVocals = getValueProc("lyricsCountVocals", True)
        self.lyricsCountVocalsStandalone = \
            getValueProc("lyricsCountVocalsStandalone")
        self.lyricsCountBgVocals = getValueProc("lyricsCountBgVocals")
        self.lyricsCountBgVocalsStandalone = \
            getValueProc("lyricsCountBgVocalsStandalone")
        self.useSpecialLayoutForExtracts = \
            getValueProc("useSpecialLayoutForExtracts", True)
        self.styleHumanizationKind = \
            getValueProc("styleHumanizationKind", True)
        self.humanizedVoiceNameList = getValueProc("humanizedVoicesList",
                                                   True)
        self.tempoTrackLineList = getValueProc("tempoTrack", True)
        self.attenuationLevel = getValueProc("attenuationLevel", True)

        voiceNames      = getValueProc("voices", True)
        midiChannels    = getValueProc("midiChannel", True)
        midiInstruments = getValueProc("midiInstrument", True)
        midiVolumes     = getValueProc("midiVolume", True)
        panPositions    = getValueProc("panPosition", True)
        audioVolumes    = getValueProc("audioVolume", True)
        reverbLevels    = getValueProc("reverbLevel", True)
        soundVariants   = getValueProc("soundVariant", True)

        overrideFiles = getValueProc("overrideFiles", False)
        overrideFiles = iif(overrideFiles is None, "", overrideFiles)

        self._checkValidity()
        self._checkStringLists(voiceNames, midiChannels, midiInstruments,
                               midiVolumes, panPositions, audioVolumes,
                               reverbLevels, soundVariants)

        self.voiceNameToOverrideFileMap = \
                self._splitOverrideInfo(overrideFiles)
        self.tempoTrackLineList = \
           convertStringToList(self.tempoTrackLineList, "|")
        self.humanizedVoiceNameList = \
            convertStringToList(self.humanizedVoiceNameList)

        self._convertToVoiceMap(voiceNames, midiChannels, midiInstruments,
                                midiVolumes, panPositions, audioVolumes,
                                reverbLevels, soundVariants)

        if len(selectedVoiceNameList) == 0:
            # when no voices are selected so far, all voices will be
            # used
            selectedVoiceNameList.extend(self.voiceNameList)

        Logging.trace("<<: self = %s, selectedVoiceNameList = %s",
                      str(self), str(selectedVoiceNameList))
