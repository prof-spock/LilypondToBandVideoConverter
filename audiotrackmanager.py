#!/bin/python
# audiotrackmanager -- generates audio tracks from midi file and provides
#                      several transformations on it (e.g. instrument
#                      postprocessing and mixdown
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================

from miditransformation import MidiTransformer
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

#====================

class AudioTrackManager:
    """This class encapsulates services for audio tracks generated
       from a midi file."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _convertMidiToAudio (self, voiceMidiFileName, voiceName):
        """Converts voice data in midi file with <voiceMidiFileName>
           to raw audio file in audio directory with <voiceName>"""

        Logging.trace(">>: voice = %s, midiFile = '%s'",
                      voiceName, voiceMidiFileName)

        # prepare config file for fluidsynth
        fluidsynthSettingsFileName = ("%s/%s"
                                      % (self._audioDirectoryPath,
                                         "fluidsynthsettings.txt"))
        fluidsynthSettingsFile = open(fluidsynthSettingsFileName, "w")
        st = "rev_setlevel 0\nrev_setwidth 1.5\nrev_setroomsize 0.5"
        fluidsynthSettingsFile.write(st)
        fluidsynthSettingsFile.close()
        Logging.trace("--: settings file '%s' generated",
                      fluidsynthSettingsFileName)

        concatDirectoryProc = (lambda x: "%s/%s"
                                         % (soundFontDirectoryName, x))
        soundFonts = map(concatDirectoryProc, soundFontNameList)
        targetFileName = "%s/%s.wav" % (self._audioDirectoryPath, voiceName)

        # processing midi file via fluidsynth
        OperatingSystem.showMessageOnConsole("== fluidsynth "
                                             + targetFileName)
        command = ([fluidsynthCommand,
                    "-n", "-i", "-g", "1",
                    "-f", fluidsynthSettingsFileName,
                    "-F", targetFileName]
                   + soundFonts
                   + [ voiceMidiFileName ])
        OperatingSystem.executeCommand(command, False,
                                       stdout=OperatingSystem.nullDevice)

        # cleanup
        OperatingSystem.removeFile(fluidsynthSettingsFileName,
                                   debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    def _makeFilteredMidiFile (self, voiceName, midiFileName,
                               voiceMidiFileName):
        """Filters tracks in midi file named <midiFileName> belonging
           to voice with <voiceName> and writes them to
           <voiceMidiFileName>"""

        Logging.trace(">>: voice = %s, midiFile = '%s', targetFile = '%s'",
                      voiceName, midiFileName, voiceMidiFileName)

        midiTransformer = MidiTransformer(midiFileName, debuggingIsActive)
        midiTransformer.filterByTrackNamePrefix(voiceName)
        midiTransformer.save(voiceMidiFileName)
        
        Logging.trace("<<")

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

    def copyOverrideFile (self, fileName, voiceName):
        """Sets refined file from <fileName>"""

        Logging.trace(">>")

        message = "== overriding %s from file" % voiceName
        OperatingSystem.showMessageOnConsole(message)

        targetFileName = "%s/%s" % (self._audioDirectoryPath,
                                    voiceName + "-processed.wav")
        command = (ffmpegCommand,
                   "-y", "-i", fileName, targetFileName)
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------

    def generateRawAudio (self, midiFileName, voiceName):
        """Generates audio wave file for <voiceName> from midi file
           with <midiFileName> in target directory; if several midi
           tracks match voice name, the resulting audio files are
           mixed; output is dry (no chorus, reverb and delay) and
           contains leading and trailing silent passages"""

        Logging.trace(">>: voice = %s, midiFile = '%s'",
                      voiceName, midiFileName)

        tempMidiFileName = "tempRender.mid"
        self._makeFilteredMidiFile(voiceName, midiFileName, tempMidiFileName)
        self._convertMidiToAudio(tempMidiFileName, voiceName)
        OperatingSystem.removeFile(tempMidiFileName, debuggingIsActive)

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

    def mixdown (self, albumName, songTitle, voiceNameList,
                 voiceNameToVolumeMap, optionalVoiceMap):
        """Combines the processed audio files for all voices in
           <voiceNameList> into several combination files and converts
           them to aac format; voice volumes are given via
           <voiceNameToVolumeMap>; the optional voices are given by
           the keys in <optionalVoiceMap> and the final files are
           tagged with <albumName> and <songTitle> with suffices given
           by <optionalVoiceMap>"""

        Logging.trace(">>: albumName = '%s', songTitle = '%s',"
                      + " voiceNameList = %s, voiceNameToVolumeMap = %s,",
                      + " optionalVoiceMap = %s",
                      albumName, songTitle, voiceNameList,
                      voiceNameToVolumeMap, optionalVoiceMap)

        Logging.trace("<<")
