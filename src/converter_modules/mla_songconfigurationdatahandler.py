# -*- coding: utf-8-unix -*-
# mla_songconfigurationdata -- services for access to the song-specific
#                              configuration file of makeLilypondAll

#====================

import datetime
from configurationfile import ConfigurationFile
from simplelogging import Logging
from ttbase import convertStringToList, iif, isInRange
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

    def __repr__ (self):
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
        ValidityChecker.isString(self.targetFileNamePrefix,
                                 "targetFileNamePrefix")
        ValidityChecker.isDirectory(self.audioTargetDirectoryPath,
                                    "audioTargetDirectoryPath")
        ValidityChecker.isReadableFile(self.albumArtFilePath,
                                       "albumArtFilePath")
        ValidityChecker.isNatural(self.year, "year")
        ValidityChecker.isBoolean(self.useHardVideoSubtitles,
                                  "useHardVideoSubtitles")

        ValidityChecker.isString(self.title, "title")
        ValidityChecker.isReadableFile(self.includeFilePath,
                                       "includeFilePath")
        ValidityChecker.isNatural(self.trackNumber, "trackNumber")
        ValidityChecker.isString(self.fileNamePrefix, "fileNamePrefix")
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
        ValidityChecker.isFloat(self.parallelTrackVolume,
                                "parallelTrackVolume")
        ValidityChecker.isFloat(self.shiftOffset, "shiftOffset")
        ValidityChecker.isFloat(self.attenuationLevel, "attenuationLevel")

        if self.parallelTrackFilePath != "":
            ValidityChecker.isReadableFile(self.parallelTrackFilePath,
                                           "parallelTrackFilePath")

        # additional rules
        ValidityChecker.isValid(" " not in self.fileNamePrefix,
                   "'fileNamePrefix' must not contain blanks")
        ValidityChecker.isValid(isInRange(self.year, 1900, 2100),
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

    def _splitOverrideInfo (self, overrideFiles):
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

    def _splitParallelTrackInfo (self, parallelTrackInfo):
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
            
        self.parallelTrackFilePath = partList[0]
        self.parallelTrackVolume   = float(partList[1])
        self.shiftOffset           = float(partList[2])

        Logging.trace("<<: %s", partList)
        
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        # album related
        self.artistName               = None
        self.albumName                = None
        self.targetFileNamePrefix     = None
        self.albumArtFilePath         = None
        self.audioTargetDirectoryPath = None
        self.videoVoiceNameList       = None
        self.useHardVideoSubtitles    = None
        self.year                     = None

        # song related
        self.debuggingIsActive = False
        self.optionalVoiceNameToSuffixMap = {}
        self.title = "%title%"
        self.trackNumber = 0
        self.fileNamePrefix = "XXXX"
        self.includeFilePath = "%includeFilePath%"
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
        self.parallelTrackFilePath = ""
        self.parallelTrackVolume = 1.0
        self.shiftOffset    = None
        self.tempoTrackList = ""
        self.attenuationLevel = 0

    #--------------------

    def __repr__ (self):
        st = (("_SongConfigurationData("
               + "artistName = '%s', albumName = '%s', albumArtFilePath = '%s',"
               + " audioTargetDirectoryPath = '%s',"
               + " targetFileNamePrefix = %s, year = %d,"
               + " title = '%s', fileNamePrefix = %s, includeFilePath = '%s',"
               + " optionalVoiceNameToSuffixMap = %s,"
               + " trackNumber = %d, debuggingIsActive = %s,"
               + " lyricsCountVocals = %d, lyricsCountVocalsStandalone = %d,"
               + " lyricsCountBgVocals = %d,"
               + " lyricsCountBgVocalsStandalone = %d,"
               + " useSpecialLayoutForExtracts = %s,"
               + " styleHumanizationKind = %s, humanizedVoiceNameList = %s,"
               + " voiceNameList = %s, voiceNameToVoiceDataMap = %s,"
               + " voiceNameToOverrideFileMap = %s, videoVoiceNameList = %s,"
               + " tempoTrackList = %s, parallelTrackFilePath = '%s',"
               + " parallelTrackVolume = %4.3f, shiftOffset = %5.3f,"
               + " attenuationLevel = %5.3f, useHardVideoSubtitles = %s)")
              % (self.artistName, self.albumName, self.albumArtFilePath,
                 self.audioTargetDirectoryPath, self.targetFileNamePrefix,
                 self.year, self.title, self.fileNamePrefix,
                 self.includeFilePath, self.optionalVoiceNameToSuffixMap,
                 self.trackNumber, self.debuggingIsActive,
                 self.lyricsCountVocals, self.lyricsCountVocalsStandalone,
                 self.lyricsCountBgVocals, self.lyricsCountBgVocalsStandalone,
                 self.useSpecialLayoutForExtracts, self.styleHumanizationKind,
                 self.humanizedVoiceNameList, self.voiceNameList,
                 self.voiceNameToVoiceDataMap, self.voiceNameToOverrideFileMap,
                 self.videoVoiceNameList, self.tempoTrackList,
                 self.parallelTrackFilePath, self.parallelTrackVolume,
                 self.shiftOffset, self.attenuationLevel,
                 self.useHardVideoSubtitles))

        return st

    #--------------------

    def readFile (self, configurationFilePath, selectedVoiceNameList):
        """Reads data from configuration file with
           <configurationFilePath> into <self>."""

        Logging.trace(">>: '%s'", configurationFilePath)

        configurationFile = ConfigurationFile(configurationFilePath)
        getValueProc = configurationFile.getValue

        # read all values
        self.artistName = getValueProc("artistName", "")
        self.albumName = getValueProc("albumName", "")
        self.targetFileNamePrefix = getValueProc("targetFileNamePrefix", "")
        self.useHardVideoSubtitles = getValueProc("useHardVideoSubtitles",
                                                  True)
        self.title = getValueProc("title")
        self.trackNumber = getValueProc("trackNumber", 0)
        self.fileNamePrefix = getValueProc("fileNamePrefix")
        self.audioTargetDirectoryPath = \
                 getValueProc("audioTargetDirectoryPath", "")
        self.includeFilePath = self.fileNamePrefix + "-music.ly"
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
        self.attenuationLevel = getValueProc("attenuationLevel", 0.0)

        tempoTrack          = getValueProc("tempoTrack")

        videoVoiceNames     = getValueProc("videoVoices", "")
        humanizedVoiceNames = getValueProc("humanizedVoicesList", "")

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
        parallelTrackInfo   = getValueProc("parallelTrack", "")
        self._splitParallelTrackInfo(parallelTrackInfo)

        self._checkValidity()
        self._checkStringLists(voiceNames, midiChannels, midiInstruments,
                               midiVolumes, panPositions, audioVolumes,
                               reverbLevels, soundVariants)

        self.optionalVoiceNameToSuffixMap = \
                 self._splitOptionalVoiceInfo(optionalVoiceNames)
        self.voiceNameToOverrideFileMap = \
                 self._splitOverrideInfo(overrideFiles)
        self.tempoTrackList         = convertStringToList(tempoTrack, "|")
        self.humanizedVoiceNameList = convertStringToList(humanizedVoiceNames)
        self.videoVoiceNameList     = convertStringToList(videoVoiceNames)

        self._convertToVoiceMap(voiceNames, midiChannels, midiInstruments,
                                midiVolumes, panPositions, audioVolumes,
                                reverbLevels, soundVariants)

        if len(selectedVoiceNameList) == 0:
            # when no voices are selected so far, all voices will be
            # used
            selectedVoiceNameList.extend(self.voiceNameList)

        if len(self.videoVoiceNameList) == 0:
            self.videoVoiceNameList.extend(self.voiceNameList)

        Logging.trace("<<: self = %s, selectedVoiceNameList = %s",
                      str(self), str(selectedVoiceNameList))
