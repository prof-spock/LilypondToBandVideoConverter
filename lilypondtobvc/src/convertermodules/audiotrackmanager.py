# -*- coding: utf-8-unix -*-
# audiotrackmanager -- generates audio tracks from midi file and provides
#                      several transformations on it (e.g. instrument
#                      postprocessing and mixdown
#
# author: Dr. Thomas Tensi, 2006 - 2018

#====================
# IMPORTS
#====================

from basemodules.configurationfile import ConfigurationFile
from basemodules.operatingsystem import OperatingSystem
from basemodules.simplelogging import Logging
from basemodules.ttbase import adaptToRange, iif, isInRange, MyRandom
from basemodules.utf8file import UTF8File 

from .ltbvc_businesstypes import humanReadableVoiceName
from .miditransformer import MidiTransformer
from .mp4tagmanager import MP4TagManager

#====================

_processedAudioFileTemplate = "%s/%s-processed.wav"
_tempAudioFileTemplate = "%s/%s-temp%s.wav"

# the log level for ffmpeg rendering
_ffmpegLogLevel = "error"

#====================

class AudioTrackManager:
    """This class encapsulates services for audio tracks generated
       from a midi file."""

    _aacCommandLine              = None
    _intermediateFilesAreKept    = None
    _ffmpegCommand               = None
    _fluidsynthCommand           = None
    _soundFontDirectoryName      = None
    _soundFontNameList           = None
    _soundStyleNameToCommandsMap = None
    _soxCommandLinePrefixList    = None

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _compressAudio (self, audioFilePath, songTitle, targetFilePath):
        """Compresses audio file with <songTitle> in path with
          <audioFilePath> to AAC file at <targetFilePath>"""

        Logging.trace(">>: audioFile = '%s', title = '%s', targetFile = '%s'",
                      audioFilePath, songTitle, targetFilePath)

        cls = self.__class__

        if cls._aacCommandLine == "":
            command = ( cls._ffmpegCommand,
                        "-loglevel", _ffmpegLogLevel,
                        "-aac_tns", "0",                        
                        "-i", audioFilePath,
                        "-y", targetFilePath )
        else:
            commandLine = (cls._aacCommandLine
                           .replace("$1", audioFilePath)
                           .replace("$2", targetFilePath))
            command = commandLine.split()

        OperatingSystem.showMessageOnConsole("== convert to AAC: "
                                             + songTitle)
        OperatingSystem.executeCommand(command, True)

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

        st = "rev_setlevel 0\nrev_setwidth 1.5\nrev_setroomsize 0.5"

        fluidsynthSettingsFile = UTF8File(fluidsynthSettingsFilePath, "wt")
        fluidsynthSettingsFile.write(st)
        fluidsynthSettingsFile.close()

        Logging.trace("--: settings file '%s' generated",
                      fluidsynthSettingsFilePath)

        concatDirectoryProc = (lambda x: "%s/%s"
                               % (cls._soundFontDirectoryName, x))
        soundFonts = list(map(concatDirectoryProc, cls._soundFontNameList))

        # processing midi file via fluidsynth
        OperatingSystem.showMessageOnConsole("== fluidsynth "
                                             + targetFilePath)

        command = ([ cls._fluidsynthCommand,
                     "-n", "-i", "-g", "1",
                     "-f", fluidsynthSettingsFilePath,
                     "-F", targetFilePath ]
                   + soundFonts
                   + [ voiceMidiFilePath ])
        OperatingSystem.executeCommand(command, True,
                                       stdout=OperatingSystem.nullDevice)

        # cleanup
        OperatingSystem.removeFile(fluidsynthSettingsFilePath,
                                   cls._intermediateFilesAreKept)

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
                                          cls._intermediateFilesAreKept)
        midiTransformer.filterByTrackNamePrefix(voiceName)
        midiTransformer.removeVolumeChanges()
        midiTransformer.save(voiceMidiFilePath)

        Logging.trace("<<")

    #--------------------

    def _mixdownToWavFile (self, songTitle, voiceNameList,
                           voiceNameToVolumeMap, parallelTrackFilePath,
                           attenuationLevel, targetFilePath):
        """Constructs and executes a command for audio mixdown of song with
           <songTitle> to target file with <targetFilePath> from given
           <voiceNameList>, the mapping to volumes <voiceNameToVolumeMap> with
           loudness attenuation given by <attenuationLevel>; if
           <parallelTrackPath> is not empty, the parallel track is added"""

        Logging.trace(">>: voiceNames = %s, target = '%s'",
                      voiceNameList, targetFilePath)

        cls = self.__class__
        command = (cls._soxCommandLinePrefixList
                   + [ "--combine", "mix" ])

        for voiceName in voiceNameList:
            audioFilePath = (_processedAudioFileTemplate
                             % (self._audioDirectoryPath, voiceName))
            volume = voiceNameToVolumeMap.get(voiceName, 1)
            command += [ "-v", str(volume), audioFilePath ]

        if parallelTrackFilePath != "":
            volume = voiceNameToVolumeMap["parallel"]
            command += [ "-v", str(volume), parallelTrackFilePath ]
            
        command += [ targetFilePath, "norm", str(attenuationLevel) ]

        OperatingSystem.showMessageOnConsole("== make mix file: %s"
                                             % songTitle)
        OperatingSystem.executeCommand(command, True)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _powerset (cls, currentList):
        """Calculates the power set of elements in <currentList>"""

        Logging.trace(">>: %s", currentList)

        elementCount = len(currentList)
        powersetCardinality = 2 ** elementCount
        result = []

        for i in range(powersetCardinality):
            currentSet = []
            bitmap = i

            for j in range(elementCount):
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
        command = (cls._soxCommandLinePrefixList
                   + [ audioFilePath, shiftedFilePath,
                       "pad", ("%7.3f" % shiftOffset) ])
        OperatingSystem.executeCommand(command, True,
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

    def _tagAudio (self, audioFilePath, configData, songTitle, albumName):
        """Tags M4A audio file with <songTitle> at <audioFilePath>
           with tags specified by <configData>, <songTitle> and
           <albumName>"""

        Logging.trace(">>: audioFile = '%s', configData = %s,"
                      + " title = '%s', album = '%s'",
                      audioFilePath, configData, songTitle, albumName)

        artistName = configData.artistName

        tagToValueMap = {}
        tagToValueMap["album"]       = albumName
        tagToValueMap["albumArtist"] = artistName
        tagToValueMap["artist"]      = artistName
        tagToValueMap["cover"]       = configData.albumArtFilePath
        tagToValueMap["title"]       = songTitle
        tagToValueMap["track"]       = configData.trackNumber
        tagToValueMap["year"]        = configData.songYear

        OperatingSystem.showMessageOnConsole("== tagging AAC: " + songTitle)
        MP4TagManager.tagFile(audioFilePath, tagToValueMap)

        Logging.trace("<<")
        
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls,
                    aacCommandLine, ffmpegCommand, fluidsynthCommand,
                    soxCommandLinePrefix, soundFontDirectoryName,
                    soundFontNameList, soundStyleNameToCommandsMap,
                    intermediateFilesAreKept):
        """Sets some global processing data like e.g. the command
           paths."""

        Logging.trace(">>: aac = '%s', ffmpeg = '%s', fluidsynth = '%s',"
                      + " sox = '%s', sfDirectory = '%s',"
                      + " sfList = %s, soundStyleNameToCommandsMap = %s,"
                      + " debugging = %s",
                      aacCommandLine, ffmpegCommand, fluidsynthCommand,
                      soxCommandLinePrefix, soundFontDirectoryName,
                      soundFontNameList, soundStyleNameToCommandsMap,
                      intermediateFilesAreKept)

        cls._aacCommandLine              = aacCommandLine
        cls._intermediateFilesAreKept    = intermediateFilesAreKept
        cls._ffmpegCommand               = ffmpegCommand
        cls._fluidsynthCommand           = fluidsynthCommand
        cls._soundFontDirectoryName      = soundFontDirectoryName
        cls._soundFontNameList           = soundFontNameList
        cls._soundStyleNameToCommandsMap = soundStyleNameToCommandsMap
        cls._soxCommandLinePrefixList    = soxCommandLinePrefix.split()

        Logging.trace("<<")

    #--------------------

    def __init__ (self, audioDirectoryPath):
        """Initializes generator with target directory of all audio
           files to be stored in <audioDirectoryPath>"""

        Logging.trace(">>: audioDirectoryPath = '%s'", audioDirectoryPath)

        self._audioDirectoryPath = audioDirectoryPath

        Logging.trace("<<")

    #--------------------

    @classmethod
    def constructSettingsForAudioTracks (cls, configData):
        """Constructs a list of tuples each representing a target
           audio file from mapping
           <audioGroupNameToVoiceNameListMap> and
           <audioTrackNameToListMap> and given <voiceNameList> in
           <configData>; each tuple contains the set of voice
           names used, its album name, its song title and its
           target file path"""

        Logging.trace(">>")

        result = []
        groupToVoiceSetMap = configData.audioGroupNameToVoiceNameSetMap
        audioTrackList     = configData.audioTrackList

        Logging.trace("--: groupToVoiceSetMap = %s, trackList = %s",
                      groupToVoiceSetMap, audioTrackList)
        
        # traverse all audio track objects
        for audioTrack in audioTrackList:
            # expand the set of audio groups into a set of voice names
            voiceNameSubset = set()

            for groupName in audioTrack.audioGroupList:
                if groupName not in groupToVoiceSetMap:
                    Logging.trace("--: skipped unknown group %s",
                                  groupName)
                else:
                    voiceNameSubset.update(groupToVoiceSetMap[groupName])

            voiceNameSubset &= set(configData.voiceNameList)
            albumName = audioTrack.albumName
            albumName = albumName.replace("$", configData.albumName)
            st = audioTrack.songNameTemplate
            songTitle = st.replace("$", configData.title)
            st = audioTrack.audioFileTemplate
            st = st.replace("$", configData.fileNamePrefix)
            targetFilePath = \
                ("%s/%s.m4a" % (configData.audioTargetDirectoryPath, st))

            newEntry = (voiceNameSubset, albumName, songTitle,
                        targetFilePath, audioTrack.description,
                        audioTrack.languageCode)
            Logging.trace("--: appending %s for track name %s",
                          newEntry, audioTrack.name)
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

        targetFilePath = (_processedAudioFileTemplate
                          % (self._audioDirectoryPath, voiceName))
        command = (cls._soxCommandLinePrefixList
                   + [ filePath, targetFilePath,
                       "pad", ("%7.3f" % shiftOffset) ])
        OperatingSystem.executeCommand(command, True)

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
            OperatingSystem.removeFile(audioFilePath, cls._intermediateFilesAreKept)
            
        OperatingSystem.removeFile(tempMidiFilePath, cls._intermediateFilesAreKept)

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
        extendedSoundVariant = soundVariant.capitalize()
        isCopyVariant = (extendedSoundVariant == "Copy")

        if isCopyVariant:
            soundStyleName = "COPY"
        else:
            simpleVoiceName = humanReadableVoiceName(voiceName)
            capitalizedVoiceName = simpleVoiceName.capitalize()
            isSimpleKeyboard = (capitalizedVoiceName == "Keyboardsimple")
            capitalizedVoiceName = iif(isSimpleKeyboard, "Keyboard",
                                       capitalizedVoiceName)
            soundStyleName = \
                "soundStyle%s%s" % (capitalizedVoiceName,
                                    extendedSoundVariant)

        message = "== processing %s (%s)" % (voiceName, soundVariant)
        OperatingSystem.showMessageOnConsole(message)

        # prepare list of sox argument lists for processing
        reverbLevel = adaptToRange(int(reverbLevel * 100.0), 0, 100)
        reverbCommands = iif(reverbLevel > 0, " reverb %d" % reverbLevel, "")

        if isCopyVariant:
            params = ""
        elif soundStyleName in cls._soundStyleNameToCommandsMap:
            params = cls._soundStyleNameToCommandsMap[soundStyleName]
        else:
            params = ""
            message = ("--: unknown variant %s replaced by copy default"
                       % soundVariant)
            Logging.trace(message)
            OperatingSystem.showMessageOnConsole(message)
        
        params += " norm -3" + reverbCommands
        parameterSequenceList = params.split("tee ")

        if not cls._intermediateFilesAreKept:
            # when not debugging, there is no need to have intermediate
            # audio files => use only one single command line
            parameterSequenceList = [ " ".join(parameterSequenceList) ]

        Logging.trace("--: parameterSeqList = %s", parameterSequenceList)
        commandCount = len(parameterSequenceList)
        sourceFilePath = "%s/%s.wav" % (self._audioDirectoryPath, voiceName)
        targetFilePath = (_processedAudioFileTemplate %
                          (self._audioDirectoryPath, voiceName))
        currentSource = sourceFilePath

        for i, parameterSequence in enumerate(parameterSequenceList):
            tempFilePath = (_tempAudioFileTemplate
                            % (self._audioDirectoryPath, voiceName,
                               hex(i + 1).upper()))
            currentTarget = iif(i < commandCount - 1, tempFilePath,
                                targetFilePath)
            parameterList = cls._splitParameterSequence(parameterSequence)
            command = (cls._soxCommandLinePrefixList
                       + [ currentSource, currentTarget ]
                       + parameterList)
            OperatingSystem.executeCommand(command, True)
            currentSource = currentTarget
                       
        Logging.trace("<<")

    #--------------------

    def mixdown (self, configData, voiceNameToVolumeMap):
        """Combines the processed audio files for all voices in
           <configData.voiceNameList> into several combination files and
           converts them to aac format; <configData> defines the voice
           volumes, the relative normalization level, the optional
           voices as well as the tags and suffices for the final
           files"""

        Logging.trace(">>: configData = %s, voiceNameToVolumeMap = %s",
                      configData, voiceNameToVolumeMap)

        cls = self.__class__

        if configData.parallelTrackFilePath != "":
            voiceNameToVolumeMap["parallel"] = configData.parallelTrackVolume

        waveIntermediateFilePath = self._audioDirectoryPath + "/result.wav"
        voiceProcessingList = \
            cls.constructSettingsForAudioTracks(configData)

        attenuationLevel = configData.attenuationLevel

        for v in voiceProcessingList:
            currentVoiceNameList, albumName, songTitle, \
              targetFilePath, _, _ = v
            self._mixdownToWavFile(songTitle, currentVoiceNameList,
                                   voiceNameToVolumeMap,
                                   configData.parallelTrackFilePath,
                                   attenuationLevel,
                                   waveIntermediateFilePath)
            self._compressAudio(waveIntermediateFilePath, songTitle,
                                targetFilePath)
            self._tagAudio(targetFilePath, configData, songTitle, albumName)

            OperatingSystem.removeFile(waveIntermediateFilePath,
                                       cls._intermediateFilesAreKept)

        Logging.trace("<<")
