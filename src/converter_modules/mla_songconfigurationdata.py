# mla_songconfigurationdata -- services for access to the song-specific
#                              configuration file of makeLilypondAll

#====================

import datetime
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
        ValidityChecker.isString(self.artistName, "artistName")
        ValidityChecker.isString(self.albumName, "albumName")
        ValidityChecker.isString(self.audioTargetFileNamePrefix,
                                 "audioTargetFileNamePrefix")
        ValidityChecker.isDirectory(self.audioTargetDirectoryPath,
                                    "audioTargetDirectoryPath")
        ValidityChecker.isReadableFile(self.albumArtFilePath,
                                       "albumArtFilePath")
        ValidityChecker.isReadableFile(self.includeFileName,
                                       "includeFileName")
        ValidityChecker.isString(self.title, "title")
        ValidityChecker.isNatural(self.trackNumber, "trackNumber")
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

    def _splitOptionalVoiceInfo (self, optionalVoiceNames):
        """Converts string <optionalVoiceNames> to mapping from voice
           name to suffices for album name and song name"""

        Logging.trace(">>: %s", optionalVoiceNames)

        result = {}
        optionalVoicePartList = optionalVoiceNames.split(",")

        for part in optionalVoicePartList:
            part = part.strip()

            if part > "":
                voiceName, suffices = part.split(":")
                songNameSuffix, albumNameSuffix = suffices.strip().split("|")
                value = (albumNameSuffix, songNameSuffix)
                result[voiceName] = value
                Logging.trace("--: %s -> %s", voiceName, str(value))

        Logging.trace("<<: %s", str(result))
        return result

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
        self.artistName = "%artistName%"
        self.albumName = "%albumName%"
        self.optionalVoiceNameToSuffixMap = {}
        self.title = "%title%"
        self.trackNumber = 0
        self.audioTargetFileNamePrefix = ""
        self.fileNamePrefix = "XXXX"
        self.includeFileName = "%includeFileName%"
        self.albumArtFilePath = "%albumArtFilePath%"
        self.audioTargetDirectoryPath = "YYYY"
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
               + "artistName = '%s', albumName = '%s', title = '%s',"
               + " audioTargetFileNamePrefix = %s, fileNamePrefix = %s,"
               + " optionalVoiceNameToSuffixMap = %s,"
               + " audioTargetDirectoryPath = '%s',"
               + " includeFileName = '%s', albumArtFilePath = '%s',"
               + " year = %d, trackNumber = %d, debuggingIsActive = %s,"
               + " lyricsCountVocals = %d, lyricsCountVocalsStandalone = %d,"
               + " lyricsCountBgVocals = %d,"
               + " lyricsCountBgVocalsStandalone = %d,"
               + " useSpecialLayoutForExtracts = %s,"
               + " styleHumanizationKind = %s, humanizedVoiceNameList = %s,"
               + " voiceNameList = %s, voiceNameToVoiceDataMap = %s,"
               + " voiceNameToOverrideFileMap = %s, tempoTrackLineList = %s,"
               + " attenuationLevel = %5.3f)")
              % (self.artistName, self.albumName, self.title,
                 self.audioTargetFileNamePrefix, self.fileNamePrefix,
                 self.optionalVoiceNameToSuffixMap,
                 self.audioTargetDirectoryPath, self.includeFileName,
                 self.albumArtFilePath,
                 self.year, self.trackNumber, self.debuggingIsActive,
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
        self.artistName = getValueProc("artistName", "")
        self.albumName = getValueProc("albumName", "")
        self.title = getValueProc("title")
        self.trackNumber = getValueProc("trackNumber", 0)
        self.audioTargetFileNamePrefix = \
                 getValueProc("audioTargetFileNamePrefix", "")
        self.fileNamePrefix = getValueProc("fileNamePrefix")
        self.audioTargetDirectoryPath = \
                 getValueProc("audioTargetDirectoryPath", "")
        self.includeFileName = self.fileNamePrefix + "-music.ly"
        self.albumArtFilePath = getValueProc("albumArtFilePath", "")
        self.year = getValueProc("year", datetime.date.today().year)
        self.debuggingIsActive = getValueProc("debuggingIsActive", False)
        self.lyricsCountVocals = getValueProc("lyricsCountVocals")
        self.lyricsCountVocalsStandalone = \
                 getValueProc("lyricsCountVocalsStandalone")
        self.lyricsCountBgVocals = getValueProc("lyricsCountBgVocals")
        self.lyricsCountBgVocalsStandalone = \
                 getValueProc("lyricsCountBgVocalsStandalone")
        self.useSpecialLayoutForExtracts = \
                 getValueProc("useSpecialLayoutForExtracts", False)
        self.styleHumanizationKind = getValueProc("styleHumanizationKind")
        self.humanizedVoiceNameList = getValueProc("humanizedVoicesList", [])
        self.tempoTrackLineList = getValueProc("tempoTrack")
        self.attenuationLevel = getValueProc("attenuationLevel", 0)

        voiceNames      = getValueProc("voices")
        midiChannels    = getValueProc("midiChannel")
        midiInstruments = getValueProc("midiInstrument")
        midiVolumes     = getValueProc("midiVolume")
        panPositions    = getValueProc("panPosition")
        audioVolumes    = getValueProc("audioVolume")
        reverbLevels    = getValueProc("reverbLevel")
        soundVariants   = getValueProc("soundVariant")

        overrideFiles = getValueProc("overrideFiles", "")
        optionalVoiceNames = getValueProc("optionalVoices", "")

        self._checkValidity()
        self._checkStringLists(voiceNames, midiChannels, midiInstruments,
                               midiVolumes, panPositions, audioVolumes,
                               reverbLevels, soundVariants)

        self.optionalVoiceNameToSuffixMap = \
                 self._splitOptionalVoiceInfo(optionalVoiceNames)
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
