#!/bin/python
# audiotrackmanager -- generates audio tracks from midi file and provides
#                      several transformations on it (e.g. instrument
#                      postprocessing and mixdown
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================

from miditransformer import MidiTransformer
from operatingsystem import OperatingSystem
from simplelogging import Logging
from ttbase import adaptToRange, iif, iif2, iif4, isInRange, MyRandom

#====================

# external commands
aacCommand        = None
ffmpegCommand     = None
fluidsynthCommand = None
soxCommand        = None

# soundfont data
soundFontDirectoryName = None
soundFontNameList      = None

debuggingIsActive = None

processedAudioFileTemplate = "%s/%s-processed.wav"

#====================

class AudioTrackManager:
    """This class encapsulates services for audio tracks generated
       from a midi file."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _compressAudio (self, audioFilePath, songData, songTitle, albumName,
                        targetFilePath):
        """Compresses audio file at <audioFilePath> to AAC file at
           <targetFilePath> using <songData>, <songTitle> and
           <albumName> for tagging"""

        Logging.trace(">>: audioFile = '%s', songData = %s,"
                      + " title = '%s', album = '%s', targetFile = '%s'",
                      audioFilePath, songData, songTitle, albumName,
                      targetFilePath)

        command = ( aacCommand,
                    "-V100", "--no-optimize",
                    "--title", songTitle,
                    "--artist", songData.artistName,
                    "--band", songData.artistName,
                    "--album", albumName,
                    "--track", str(songData.trackNumber),
                    "--date", str(songData.year),
                    "--artwork", songData.albumArtFilePath,
                    "-i", audioFilePath,
                    "-o", targetFilePath )

        OperatingSystem.showMessageOnConsole("== convert to AAC: " + songTitle)
        OperatingSystem.executeCommand(command, False)
        Logging.trace("<<")

    #--------------------

    def _convertMidiToAudio (self, voiceMidiFilePath, voiceName):
        """Converts voice data in midi file with <voiceMidiFilePath>
           to raw audio file in audio directory with <voiceName>"""

        Logging.trace(">>: voice = %s, midiFile = '%s'",
                      voiceName, voiceMidiFilePath)

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
                                         % (soundFontDirectoryName, x))
        soundFonts = map(concatDirectoryProc, soundFontNameList)
        targetFilePath = "%s/%s.wav" % (self._audioDirectoryPath, voiceName)

        # processing midi file via fluidsynth
        OperatingSystem.showMessageOnConsole("== fluidsynth "
                                             + targetFilePath)

        command = ([ fluidsynthCommand,
                     "-n", "-i", "-g", "1",
                     "-f", fluidsynthSettingsFilePath,
                     "-F", targetFilePath ]
                   + soundFonts
                   + [ voiceMidiFilePath ])
        OperatingSystem.executeCommand(command, False,
                                       stdout=OperatingSystem.nullDevice)

        # cleanup
        OperatingSystem.removeFile(fluidsynthSettingsFilePath,
                                   debuggingIsActive)

        Logging.trace("<<")

    # --------------------

    def _constructSettingsForOptionalVoices (self, optionalVoiceMap,
                                             voiceNameList):
        """Constructs a list of triples from mapping of optional
           voices <optionalVoiceMap> and given <voiceNameList>, where
           each triple represents a target audio file with its album
           name suffix, its song title suffix and the voice name list
           used for this audio file"""

        Logging.trace(">>")

        result = []

        # calculate power set as list
        optionalVoiceList = optionalVoiceMap.keys()
        voiceNameSubsetList = self._powerset(optionalVoiceList)
        voiceNameSubsetCount = len(voiceNameSubsetList)

        for i in xrange(voiceNameSubsetCount):
            j = -(i+1)
            voiceNameSubset           = voiceNameSubsetList[i]
            currentVoiceNameList = list(set(voiceNameList)
                                        - set(voiceNameSubset))
            albumNameSuffix = "_".join([optionalVoiceMap[name][0]
                                        for name in voiceNameSubset])
            songTitleSuffix = ("-" +
                               "".join([optionalVoiceMap[name][1]
                                        for name in voiceNameSubset]))
            songTitleSuffix = iif(songTitleSuffix == "-",
                                  "ALL", songTitleSuffix)

            newEntry = (albumNameSuffix, songTitleSuffix, currentVoiceNameList)
            Logging.trace("--: appending %s for subset=%s",
                          newEntry, voiceNameSubset)
            result.append(newEntry)

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def _makeFilteredMidiFile (self, voiceName, midiFilePath,
                               voiceMidiFilePath):
        """Filters tracks in midi file named <midiFilePath> belonging
           to voice with <voiceName> and writes them to
           <voiceMidiFilePath>"""

        Logging.trace(">>: voice = %s, midiFile = '%s', targetFile = '%s'",
                      voiceName, midiFilePath, voiceMidiFilePath)

        midiTransformer = MidiTransformer(midiFilePath, debuggingIsActive)
        midiTransformer.filterByTrackNamePrefix(voiceName)
        midiTransformer.save(voiceMidiFilePath)

        Logging.trace("<<")

    #--------------------

    def _mixdownToWavFile (self, songTitle, voiceNameList,
                           voiceNameToVolumeMap, attenuationLevel,
                           targetFilePath):
        """Constructs and executes a command for audio mixdown of song
           with <songTitle> to target file with <targetFilePath> from
           given <voiceNameList>, the mapping to volumes
           <voiceNameToVolumeMap> with loudness attenuation given by
           <attenuationLevel>"""

        Logging.trace(">>: voiceNames = %s, target = '%s'",
                      voiceNameList, targetFilePath)

        command = [ soxCommand, "--combine", "mix" ]

        for voiceName in voiceNameList:
            audioFilePath = (processedAudioFileTemplate
                             % (self._audioDirectoryPath, voiceName))
            volume = voiceNameToVolumeMap.get(voiceName, 1)
            command += [ "-v", volume, audioFilePath ]

        command += [ targetFilePath, "norm", str(attenuationLevel) ]

        OperatingSystem.showMessageOnConsole("== make mix file: %s"
                                             % songTitle)
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------

    def _powerset (self, currentList):
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
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, aacCommand, ffmpegCommand, fluidsynthCommand,
                    soxCommand, soundFontDirectoryName, soundFontNameList,
                    debuggingIsActive):
        """Sets some global processing data like e.g. the command
           paths."""

        Logging.trace(">>: aac = '%s', ffmpeg = '%s', fluidsynth = '%s',"
                      + " sox = '%s', sfDirectory = '%s', sfList = %s,"
                      + " debugging = %s",
                      aacCommand, ffmpegCommand, fluidsynthCommand,
                      soxCommand, soundFontDirectoryName,
                      str(soundFontNameList), debuggingIsActive)

        globals()['aacCommand']             = aacCommand
        globals()['debuggingIsActive']      = debuggingIsActive
        globals()['ffmpegCommand']          = ffmpegCommand
        globals()['fluidsynthCommand']      = fluidsynthCommand
        globals()['soundFontDirectoryName'] = soundFontDirectoryName
        globals()['soundFontNameList']      = soundFontNameList
        globals()['soxCommand']             = soxCommand

        Logging.trace("<<")

    #--------------------

    def __init__ (self, audioDirectoryPath):
        """Initializes generator with target directory of all audio
           files to be stored in <audioDirectoryPath>"""

        Logging.trace(">>: audioDirectoryPath = '%s'", audioDirectoryPath)

        self._audioDirectoryPath = audioDirectoryPath

        Logging.trace("<<")

    #--------------------

    def copyOverrideFile (self, filePath, voiceName):
        """Sets refined file from <filePath> for voice with
           <voiceName>"""

        Logging.trace(">>")

        message = "== overriding %s from file" % voiceName
        OperatingSystem.showMessageOnConsole(message)

        targetFilePath = (processedAudioFileTemplate
                          % (self._audioDirectoryPath, voiceName))
        command = (ffmpegCommand,
                   "-y", "-i", filePath, targetFilePath)
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------

    def generateRawAudio (self, midiFilePath, voiceName):
        """Generates audio wave file for <voiceName> from midi file
           with <midiFilePath> in target directory; if several midi
           tracks match voice name, the resulting audio files are
           mixed; output is dry (no chorus, reverb and delay) and
           contains leading and trailing silent passages"""

        Logging.trace(">>: voice = %s, midiFile = '%s'",
                      voiceName, midiFilePath)

        tempMidiFilePath = "tempRender.mid"
        self._makeFilteredMidiFile(voiceName, midiFilePath, tempMidiFilePath)
        self._convertMidiToAudio(tempMidiFilePath, voiceName)
        OperatingSystem.removeFile(tempMidiFilePath, debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    def generateRefinedAudio (self, voiceName, soundVariant, reverbLevel):
        """Generates refined audio wave file for <voiceName> from
           raw audio file in target directory; """

        Logging.trace(">>: voice = %s, variant = %s, reverb = %4.3f",
                      voiceName, soundVariant, reverbLevel)

        extendedSoundVariant = soundVariant.upper()

        if extendedSoundVariant != "COPY":
            uppercasedVoiceName = voiceName.upper()
            uppercasedVoiceName = iif(uppercasedVoiceName == "KEYBOARDSIMPLE",
                                      "KEYBOARD", uppercasedVoiceName)
            extendedSoundVariant = "%s_%s" % (uppercasedVoiceName,
                                              extendedSoundVariant)

        message = "== processing %s (%s)" % (voiceName, soundVariant)
        OperatingSystem.showMessageOnConsole(message)

        soundProcessorCommand = ("C:/Programme_TT/Multimedia/Audio"
                                 + "/processSound.bat")
        reverbLevel = adaptToRange(int(reverbLevel * 128), 0, 127)
        targetDirectoryPath = self._audioDirectoryPath.replace("/", "\\")

        command = (soundProcessorCommand,
                   extendedSoundVariant, str(reverbLevel),
                   targetDirectoryPath, voiceName)
        OperatingSystem.executeCommand(command, False)


        Logging.trace("<<")

    #--------------------

    def mixdown (self, songData, voiceNameToVolumeMap):
        """Combines the processed audio files for all voices in
           <songData.voiceNameList> into several combination files and
           converts them to aac format; <songData> defines the voice
           volumes, the relative normalization level, the optional
           voices as well as the tags and suffices for the final files"""

        Logging.trace(">>: songData = %s, voiceNameToVolumeMap = %s",
                      songData, voiceNameToVolumeMap)

        optionalVoiceMap = songData.optionalVoiceNameToSuffixMap
        waveIntermediateFilePath = self._audioDirectoryPath + "/result.wav"

        voiceProcessingList = \
            self._constructSettingsForOptionalVoices(optionalVoiceMap,
                                                     songData.voiceNameList)
        albumName = songData.albumName
        songTitle = songData.title
        attenuationLevel = songData.attenuationLevel

        for v in voiceProcessingList:
            albumNameSuffix, songTitleSuffix, currentVoiceNameList = v
            currentAlbumName = iif(albumNameSuffix == "", albumName,
                                   "%s - %s" % (albumName, albumNameSuffix))
            currentSongTitle = "%s [%s]" % (songTitle, songTitleSuffix)

            self._mixdownToWavFile(currentSongTitle, currentVoiceNameList,
                                   voiceNameToVolumeMap, attenuationLevel,
                                   waveIntermediateFilePath)

            fileSuffix = iif(songTitleSuffix == "ALL",
                             "", songTitleSuffix.lower())
            targetFilePath = ("%s/%s%s%s.m4a"
                              % (songData.audioTargetDirectoryPath,
                                 songData.audioTargetFileNamePrefix,
                                 songData.fileNamePrefix, fileSuffix))
            self._compressAudio(waveIntermediateFilePath, songData,
                                currentSongTitle, currentAlbumName,
                                targetFilePath)

        Logging.trace("<<")
