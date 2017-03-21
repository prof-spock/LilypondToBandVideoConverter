# -*- coding: utf-8-unix -*-
# audiotrackmanager -- generates audio tracks from midi file and provides
#                      several transformations on it (e.g. instrument
#                      postprocessing and mixdown
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================

from configurationfile import ConfigurationFile
from miditransformer import MidiTransformer
from mp4tagmanager import MP4TagManager
from operatingsystem import OperatingSystem
from simplelogging import Logging
from ttbase import adaptToRange, iif, isInRange, MyRandom

#====================

processedAudioFileTemplate = "%s/%s-processed.wav"
tempAudioFileTemplate = "%s/%s-temp%s.wav"
soundNameSeparator = "|"

# the log level for ffmpeg rendering
ffmpegLogLevel = "error"

#====================

class AudioTrackManager:
    """This class encapsulates services for audio tracks generated
       from a midi file."""

    _aacCommand                = None
    _debuggingIsActive         = None
    _ffmpegCommand             = None
    _fluidsynthCommand         = None
    _soundFontDirectoryName    = None
    _soundFontNameList         = None
    _soundNameToCommandListMap = None
    _soxCommand                = None

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _compressAudio (self, audioFilePath, songTitle, targetFilePath):
        """Compresses audio file with <songTitle> at <audioFilePath>
           to AAC file at <targetFilePath>"""

        Logging.trace(">>: audioFile = '%s', title = '%s', targetFile = '%s'",
                      audioFilePath, songTitle, targetFilePath)

        cls = self.__class__

        if cls._aacCommand is None:
            command = ( cls._ffmpegCommand,
                        "-loglevel", ffmpegLogLevel,
                        "-i", audioFilePath,
                        "-y", targetFilePath )
        else:
            command = ( cls._aacCommand,
                        "-V100", "--no-optimize",
                        "-i", audioFilePath,
                        "-o", targetFilePath )

        OperatingSystem.showMessageOnConsole("== convert to AAC: " + songTitle)
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------

    def _convertMidiToAudio (self, voiceMidiFilePath, targetFilePath):
        """Converts voice data in midi file with <voiceMidiFilePath>
           to raw audio file with <targetFilePath>"""

        Logging.trace(">>: midiFile = '%s', targetFile = '%s'",
                      voiceMidiFilePath, targetFilePath)

        cls = self.__class__

        # prepare config file for fluidsynth
        fluidsynthSettingsFilePath = ("%s/%s"
                                      % (self._audioDirectoryPath,
                                         "fluidsynthsettings.txt"))
        fluidsynthSettingsFile = open(fluidsynthSettingsFilePath, "w")
        st = "rev_setlevel 0\nrev_setwidth 1.5\nrev_setroomsize 0.5"
        fluidsynthSettingsFile.write(st)
        fluidsynthSettingsFile.close()
        Logging.trace("--: settings file '%s' generated",
                      fluidsynthSettingsFilePath)

        concatDirectoryProc = (lambda x: "%s/%s"
                                         % (cls._soundFontDirectoryName, x))
        soundFonts = map(concatDirectoryProc, cls._soundFontNameList)

        # processing midi file via fluidsynth
        OperatingSystem.showMessageOnConsole("== fluidsynth "
                                             + targetFilePath)

        command = ([ cls._fluidsynthCommand,
                     "-n", "-i", "-g", "1",
                     "-f", fluidsynthSettingsFilePath,
                     "-F", targetFilePath ]
                   + soundFonts
                   + [ voiceMidiFilePath ])
        OperatingSystem.executeCommand(command, False,
                                       stdout=OperatingSystem.nullDevice)

        # cleanup
        OperatingSystem.removeFile(fluidsynthSettingsFilePath,
                                   cls._debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    def _makeFilteredMidiFile (self, voiceName, midiFilePath,
                               voiceMidiFilePath):
        """Filters tracks in midi file named <midiFilePath> belonging
           to voice with <voiceName> and writes them to
           <voiceMidiFilePath>"""

        Logging.trace(">>: voice = %s, midiFile = '%s', targetFile = '%s'",
                      voiceName, midiFilePath, voiceMidiFilePath)

        cls = self.__class__
        midiTransformer = MidiTransformer(midiFilePath,
                                          cls._debuggingIsActive)
        midiTransformer.filterByTrackNamePrefix(voiceName)
        midiTransformer.save(voiceMidiFilePath)

        Logging.trace("<<")

    #--------------------

    def _mixdownToWavFile (self, songTitle, voiceNameList,
                           voiceNameToVolumeMap, shiftOffset,
                           parallelTrackFilePath, attenuationLevel,
                           targetFilePath):
        """Constructs and executes a command for audio mixdown of song
           with <songTitle> to target file with <targetFilePath> from
           given <voiceNameList>, the mapping to volumes
           <voiceNameToVolumeMap> with loudness attenuation given by
           <attenuationLevel>; if <shiftOffset> is greater zero and
           <parallelTrackPath> is not empty, all audio is shifted and
           the parallel track is added"""

        Logging.trace(">>: voiceNames = %s, target = '%s'",
                      voiceNameList, targetFilePath)

        cls = self.__class__
        command = [ cls._soxCommand, "--combine", "mix" ]

        for voiceName in voiceNameList:
            audioFilePath = (processedAudioFileTemplate
                             % (self._audioDirectoryPath, voiceName))
            volume = voiceNameToVolumeMap.get(voiceName, 1)
            command += [ "-v", volume, audioFilePath ]

        if parallelTrackFilePath != "":
            volume = voiceNameToVolumeMap["parallel"]
            command += [ "-v", str(volume), parallelTrackFilePath ]
            
        command += [ targetFilePath, "norm", str(attenuationLevel) ]

        OperatingSystem.showMessageOnConsole("== make mix file: %s"
                                             % songTitle)
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _parseConfigurationFile(cls, configurationFilePath):
        """Fills mapping from sound name to associated command line
           list from configuration file in <configurationFilePath>"""
    
        Logging.trace(">>: %s", configurationFilePath)

        configurationFile = ConfigurationFile(configurationFilePath)
        getValueProc = configurationFile.getValue

        soundNameListAsString = getValueProc("soundNameList", "")
        soundNameList = soundNameListAsString.split(soundNameSeparator)
        cls._soundNameToCommandListMap = {}

        for soundName in soundNameList:
            soundName = soundName.strip()
            Logging.trace("--: looking for sound specification %s", soundName)
            soundSpecification = getValueProc(soundName, "")
            cls._soundNameToCommandListMap[soundName] = soundSpecification

        Logging.trace("--: soundNameToCommandsMap = %s",
                      cls._soundNameToCommandListMap)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _powerset (cls, currentList):
        """Calculates the power set of elements in <currentList>"""

        Logging.trace(">>: %s", currentList)

        elementCount = len(currentList)
        powersetCardinality = 2 ** elementCount
        result = []

        for i in xrange(powersetCardinality):
            currentSet = []
            bitmap = i

            for j in xrange(elementCount):
                bitmap, remainder = divmod(bitmap, 2)

                if remainder == 1:
                    currentSet.append(currentList[j])

            result.append(currentSet)

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def _shiftAudioFile (cls, audioFilePath, shiftedFilePath, shiftOffset):
        """Shifts audio file in <audioFilePath> to shifted audio in
           <shiftedFilePath> with silence prefix of length <shiftOffset>"""

        Logging.trace(">>: infile = '%s', outfile = '%s',"
                      + " shiftOffset = %7.3f",
                      audioFilePath, shiftedFilePath, shiftOffset)

        OperatingSystem.showMessageOnConsole("== shifting %s by %7.3fs"
                                             % (shiftedFilePath, shiftOffset))
        command = (cls._soxCommand, audioFilePath, shiftedFilePath,
                   "pad", ("%7.3f" % shiftOffset))
        OperatingSystem.executeCommand(command, False,
                                       stdout=OperatingSystem.nullDevice)
        
        Logging.trace("<<")
        
    #--------------------

    @classmethod
    def _splitParameterSequence (cls, parameterSequence):
        """Splits string <parameterSequence> into list of single words
           taking quoting into account"""

        Logging.trace(">>: %s", parameterSequence)

        blankChar       = " "
        singleQuoteChar = "'"
        doubleQuoteChar = "\""

        ParseState_inLimbo  = 1
        ParseState_inWord   = 2
        ParseState_inString = 3
        
        parseState = ParseState_inLimbo
        result = []

        for ch in parameterSequence:
            parameterIsDone = False

            if parseState == ParseState_inString:
                if ch != singleQuoteChar:
                    currentWord += ch
                else:
                    parameterIsDone = True
            elif parseState == ParseState_inWord:
                if ch == blankChar:
                    parameterIsDone = True
                else:
                    currentWord += ch
            elif parseState == ParseState_inLimbo:
                currentWord = ""

                if ch == singleQuoteChar:
                    parseState = ParseState_inString
                elif ch != blankChar:
                    currentWord = ch
                    parseState = ParseState_inWord

            if parameterIsDone:
                result.append(currentWord)
                parseState = ParseState_inLimbo

        currentWord += iif(parseState == ParseState_inString,
                           doubleQuoteChar, "")
            
        if parseState != ParseState_inLimbo:
            result.append(currentWord)

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def _tagAudio (self, audioFilePath, songData, songTitle, albumName):
        """Tags M4A audio file with <songTitle> at <audioFilePath>
           with tags specified by <songData>, <songTitle> and
           <albumName>"""

        Logging.trace(">>: audioFile = '%s', songData = %s,"
                      + " title = '%s', album = '%s'",
                      audioFilePath, songData, songTitle, albumName)

        artistName = songData.artistName

        tagToValueMap = {}
        tagToValueMap["album"]       = albumName
        tagToValueMap["albumArtist"] = artistName
        tagToValueMap["artist"]      = artistName
        tagToValueMap["cover"]       = songData.albumArtFilePath
        tagToValueMap["title"]       = songTitle
        tagToValueMap["track"]       = songData.trackNumber
        tagToValueMap["year"]        = songData.year

        OperatingSystem.showMessageOnConsole("== tagging AAC: " + songTitle)
        MP4TagManager.tagFile(audioFilePath, tagToValueMap)

        Logging.trace("<<")
        
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, configurationFileName,
                    aacCommand, ffmpegCommand, fluidsynthCommand,
                    soxCommand, soundFontDirectoryName, soundFontNameList,
                    debuggingIsActive):
        """Sets some global processing data like e.g. the command
           paths."""

        Logging.trace(">>: configurationFileName = '%s',"
                      + " aac = '%s', ffmpeg = '%s', fluidsynth = '%s',"
                      + " sox = '%s', sfDirectory = '%s', sfList = %s,"
                      + " debugging = %s",
                      configurationFileName, aacCommand, ffmpegCommand,
                      fluidsynthCommand, soxCommand, soundFontDirectoryName,
                      soundFontNameList, debuggingIsActive)

        cls._aacCommand                = aacCommand
        cls._debuggingIsActive         = debuggingIsActive
        cls._ffmpegCommand             = ffmpegCommand
        cls._fluidsynthCommand         = fluidsynthCommand
        cls._soundFontDirectoryName    = soundFontDirectoryName
        cls._soundFontNameList         = soundFontNameList
        cls._soundNameToCommandListMap = {}
        cls._soxCommand                = soxCommand

        scriptFilePath = OperatingSystem.scriptFilePath()
        scriptFileDirectoryPath = OperatingSystem.dirname(scriptFilePath)
        configurationFilePath = ("%s/%s"
                                 % (scriptFileDirectoryPath,
                                    configurationFileName))

        if not OperatingSystem.hasFile(configurationFilePath):
            Logging.trace("--: ERROR configuration file not found %s",
                          configurationFilePath)
        else:
            cls._parseConfigurationFile(configurationFilePath)

        Logging.trace("<<")

    #--------------------

    def __init__ (self, audioDirectoryPath):
        """Initializes generator with target directory of all audio
           files to be stored in <audioDirectoryPath>"""

        Logging.trace(">>: audioDirectoryPath = '%s'", audioDirectoryPath)

        self._audioDirectoryPath = audioDirectoryPath

        Logging.trace("<<")

    # --------------------

    @classmethod
    def constructSettingsForOptionalVoices (cls, songData):
        """Constructs a list of quadruples from mapping
           <songData.optionalVoiceNameToSuffixMap> of optional voices
           and given <songData.voiceNameList>, where each tuple
           represents a target audio file with the voice name list
           used, its album name, its song title and its target file
           path"""

        Logging.trace(">>")

        result = []
        optionalVoiceMap = songData.optionalVoiceNameToSuffixMap

        # calculate power set as list
        optionalVoiceList = optionalVoiceMap.keys()
        voiceNameSubsetList = cls._powerset(optionalVoiceList)
        voiceNameSubsetCount = len(voiceNameSubsetList)

        for i in xrange(voiceNameSubsetCount):
            j = -(i+1)
            voiceNameSubset      = voiceNameSubsetList[i]
            currentVoiceNameList = list(set(songData.voiceNameList)
                                        - set(voiceNameSubset))
            albumNameSuffix = "_".join([optionalVoiceMap[name][0]
                                        for name in voiceNameSubset])
            songTitleSuffix = ("-" +
                               "".join([optionalVoiceMap[name][1]
                                        for name in voiceNameSubset]))
            songTitleSuffix = iif(songTitleSuffix == "-",
                                  "ALL", songTitleSuffix)
            fileSuffix = iif(songTitleSuffix == "ALL",
                             "", songTitleSuffix.lower())

            albumName = iif(albumNameSuffix == "", songData.albumName,
                            "%s - %s" % (songData.albumName, albumNameSuffix))
            songTitle = "%s [%s]" % (songData.title, songTitleSuffix)
            targetFilePath = ("%s/%s%s%s.m4a"
                              % (songData.audioTargetDirectoryPath,
                                 songData.targetFileNamePrefix,
                                 songData.fileNamePrefix, fileSuffix))

            newEntry = (currentVoiceNameList,
                        albumName, songTitle, targetFilePath)
            Logging.trace("--: appending %s for subset %s",
                          newEntry, voiceNameSubset)
            result.append(newEntry)

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def copyOverrideFile (self, filePath, voiceName, shiftOffset):
        """Sets refined file from <filePath> for voice with
           <voiceName> and applies <shiftOffset>"""

        Logging.trace(">>: file = '%s', voice = %s, offset = %7.3f",
                      filePath, voiceName, shiftOffset)

        cls = self.__class__
        message = "== overriding %s from file" % voiceName
        OperatingSystem.showMessageOnConsole(message)

        targetFilePath = (processedAudioFileTemplate
                          % (self._audioDirectoryPath, voiceName))
        command = (cls._soxCommand,
                   filePath, targetFilePath, "pad", "%7.3f" % shiftOffset)
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------

    def generateRawAudio (self, midiFilePath, voiceName, shiftOffset):
        """Generates audio wave file for <voiceName> from midi file
           with <midiFilePath> in target directory; if several midi
           tracks match voice name, the resulting audio files are
           mixed; output is dry (no chorus, reverb and delay) and
           contains leading and trailing silent passages; if
           <shiftOffset> is greater that zero, the target file is
           shifted by that amount"""

        Logging.trace(">>: voice = %s, midiFile = '%s', shiftOffset = %7.3f",
                      voiceName, midiFilePath, shiftOffset)

        cls = self.__class__
        tempMidiFilePath = "tempRender.mid"
        isShifted = (shiftOffset > 0)
        defaultTemplate = "%s/%s.wav"
        filePathTemplate = iif(isShifted, "%s/%s-raw.wav", defaultTemplate)
        audioFilePath = filePathTemplate % (self._audioDirectoryPath,
                                            voiceName)

        self._makeFilteredMidiFile(voiceName, midiFilePath, tempMidiFilePath)
        self._convertMidiToAudio(tempMidiFilePath, audioFilePath)

        if isShifted:
            targetFilePath = defaultTemplate % (self._audioDirectoryPath,
                                                voiceName)
            cls._shiftAudioFile(audioFilePath, targetFilePath, shiftOffset)
            OperatingSystem.removeFile(audioFilePath, cls._debuggingIsActive)
            
        OperatingSystem.removeFile(tempMidiFilePath, cls._debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    def generateRefinedAudio (self, voiceName, soundVariant, reverbLevel):
        """Generates refined audio wave file for <voiceName> from raw
           audio file in target directory; <soundVariant> gives the
           kind of postprocessing ('COPY', 'STD', 'EXTREME', ...) and
           <reverbLevel> the percentage of reverb to be used for that
           voice"""

        Logging.trace(">>: voice = %s, variant = %s, reverb = %4.3f",
                      voiceName, soundVariant, reverbLevel)

        cls = self.__class__
        extendedSoundVariant = soundVariant.upper()
        uppercasedVoiceName = voiceName.upper()
        isSimpleKeyboard = (uppercasedVoiceName == "KEYBOARDSIMPLE")

        if extendedSoundVariant != "COPY":
            uppercasedVoiceName = iif(isSimpleKeyboard, "KEYBOARD",
                                      uppercasedVoiceName)
            extendedSoundVariant = "%s_%s" % (uppercasedVoiceName,
                                              extendedSoundVariant)

        message = "== processing %s (%s)" % (voiceName, soundVariant)
        OperatingSystem.showMessageOnConsole(message)

        # prepare list of sox argument lists for processing
        reverbCommands = "norm -3 reverb %4.3f" % reverbLevel

        if extendedSoundVariant in cls._soundNameToCommandListMap:
            params = cls._soundNameToCommandListMap[extendedSoundVariant]
        else:
            params = ""
            Logging.trace("--: unknown variant %s replaced by empty default",
                          extendedSoundVariant)
        
        params += " " + reverbCommands
        parameterSequenceList = params.split("tee ")

        if not cls._debuggingIsActive:
            # when not debugging, there is no need to have intermediate
            # audio files => use only one single command line
            parameterSequenceList = [ " ".join(parameterSequenceList) ]

        Logging.trace("--: parameterSeqList = %s", parameterSequenceList)
        commandCount = len(parameterSequenceList)
        sourceFilePath = "%s/%s.wav" % (self._audioDirectoryPath, voiceName)
        targetFilePath = (processedAudioFileTemplate %
                          (self._audioDirectoryPath, voiceName))
        currentSource = sourceFilePath

        for i, parameterSequence in enumerate(parameterSequenceList):
            tempFilePath = (tempAudioFileTemplate
                            % (self._audioDirectoryPath, voiceName,
                               hex(i + 1).upper()))
            currentTarget = iif(i < commandCount - 1, tempFilePath,
                                targetFilePath)
            parameterList = cls._splitParameterSequence(parameterSequence)
            command = ([cls._soxCommand, currentSource, currentTarget ]
                       + parameterList)
            OperatingSystem.executeCommand(command, False)
            currentSource = currentTarget
                       
        Logging.trace("<<")

    #--------------------

    def mixdown (self, songData, voiceNameToVolumeMap):
        """Combines the processed audio files for all voices in
           <songData.voiceNameList> into several combination files and
           converts them to aac format; <songData> defines the voice
           volumes, the relative normalization level, the optional
           voices as well as the tags and suffices for the final
           files"""

        Logging.trace(">>: songData = %s, voiceNameToVolumeMap = %s",
                      songData, voiceNameToVolumeMap)

        cls = self.__class__

        if songData.parallelTrackFilePath != "":
            voiceNameToVolumeMap["parallel"] = songData.parallelTrackVolume

        waveIntermediateFilePath = self._audioDirectoryPath + "/result.wav"
        voiceProcessingList = \
            cls.constructSettingsForOptionalVoices(songData)

        attenuationLevel = songData.attenuationLevel
        # the attenuation level should be adapted from -18dbFS to
        # -8dbFS, so 10dB are added
        attenuationLevel += 10

        for v in voiceProcessingList:
            currentVoiceNameList, albumName, songTitle, targetFilePath = v
            self._mixdownToWavFile(songTitle, currentVoiceNameList,
                                   voiceNameToVolumeMap,
                                   songData.shiftOffset,
                                   songData.parallelTrackFilePath,
                                   attenuationLevel,
                                   waveIntermediateFilePath)
            self._compressAudio(waveIntermediateFilePath, songTitle,
                                targetFilePath)
            self._tagAudio(targetFilePath, songData, songTitle, albumName)

            OperatingSystem.removeFile(waveIntermediateFilePath,
                                       cls._debuggingIsActive)

        Logging.trace("<<")
