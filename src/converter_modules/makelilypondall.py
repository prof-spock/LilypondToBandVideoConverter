# -*- coding: utf-8-unix -*-
# makeLilypondAll -- script that produces lilypond files and target files
#                    for single voices, a complete score, a midi file and
#                    videos based on a configuration file
#

#


# It is assumed that the include file has the following names defined:
#    voices:        "bass", "myDrums" (as "drums" is a reserved identifier),
#                   "guitar", "keyboardTop", "keyboardBottom", "vocals"
#                   (unless the voices parameter is set)
#    chord list:    "allChordsXXX" where XXX is the capitalised
#                   voice name (chords are only added for voices that do
#                   neither match "vocals" nor "drums")
#    tempo list:    "tempoTrack" (only necessary when mode = "MIDI")
#    lyrics lines:  they are labelled "vocLyricsA", "vocLyricsB", ...
#                   or "bgVocLyricsA", "bgVocLyricsB", ...

#--------------------

import argparse
from collections import namedtuple

from audiotrackmanager import AudioTrackManager
from lilypondfilegenerator import LilypondFile
from lilypondpngvideogenerator import LilypondPngVideoGenerator
from miditransformer import MidiTransformer
from mla_overallsettingshandler import MLA_OverallSettings
from mla_songconfigurationdatahandler import MLA_SongConfigurationData
from operatingsystem import OperatingSystem
from simplelogging import Logging
from ttbase import adaptToRange, convertStringToList, iif
from validitychecker import ValidityChecker
from videoaudiocombiner import VideoAudioCombiner

#====================
# TYPE DEFINITIONS
#====================

_TrackSettingsType = namedtuple("_TrackSettingsType",
                                "voiceName midiChannel midiInstrument"
                                + " midiVolume panPosition reverbLevel")

#====================

settingsConfigurationFileName = "makelilypondall.cfg"
countInMeasures = 2

subtitleFileNameTemplate = "%s_subtitle.srt"
silentVideoFileNameTemplate = "%s_noaudio%s.mp4"

#--------------------

configData = None

processingMode = None
selectedVoiceNameList = []
songData = None

#--------------------
#--------------------

def intersection (listA, listB):
    """Returns the intersection of lists <listA> and <listB>."""

    result = (element for element in listA if element in listB)
    return result

#--------------------

def makeMap (listA, listB):
    """Returns a map from the elements in <listA> to <listB>."""

    result = {}

    for i in xrange(len(listA)):
        key   = listA[i]
        value = listB[i]
        result[key] = value

    return result

#====================

class _CommandLineOptions:
    """This module handles command line options and checks them."""

    #--------------------

    @classmethod
    def check (cls, argumentList):
        """Checks whether command line options given in <argumentList>
           are okay"""

        Logging.trace(">>")
        configurationFilePath = argumentList.configurationFilePath
        ValidityChecker.isReadableFile(configurationFilePath,
                                       "configurationFilePath")
        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls):
        """Reads commandline options and sets variables appropriately."""

        global processingMode, selectedVoiceNameList

        Logging.trace(">>")

        programDescription = ("Generates lilypond files and target files"
                              + " for single voices, a complete score,"
                              + " a midi file and videos based on a"
                              + " configuration file")
        p = argparse.ArgumentParser(description=programDescription)

        p.add_argument("configurationFilePath",
                       help="name of configuration file for song")
        p.add_argument("--mode",
                       required=True,
                       choices=["all", "preprocess", "postprocess",
                                "voices", "score", "midi", "silentvideo",
                                "rawaudio", "refinedaudio", "mixdown",
                                "finalvideo"],
                       help=("(for preprocessing) tells whether a voice"
                             + " extract, a full score"
                             + " a video or a midi should be produced;"
                             + " (for postprocessing) tells whether the"
                             + " single audio tracks, the audio mixdown"
                             + " or the final video shall be produced"))
        p.add_argument("--voices",
                       default="",
                       help=("slash separated list of voice names to be"
                             + " processed (optional, default is all voices)"))

        argumentList = p.parse_args()

        if argumentList.voices > "":
            selectedVoiceNameList = convertStringToList(argumentList.voices)

        processingMode = argumentList.mode

        Logging.trace("<<: arguments = %s, selectedVoiceNameList = %s",
                      str(argumentList), str(selectedVoiceNameList))
        return argumentList

#====================

class _LilypondProcessor:
    """Handles generation of extracts, score, midi file and silent
       video."""

    _lilypondCommand = "lilypond"
    _moveCommand     = "mv"
    _midiFileNameTemplate = "%s-std.mid"

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _calculateTrackToSettingsMap (cls):
        """Collects data from configuration file for all the settings
           of each track and returns map from track name to midi
           channel, volume, pan position and reverb level"""

        Logging.trace(">>")

        result = {}

        for i in xrange(len(songData.voiceNameList)):
            voiceName       = songData.voiceNameList[i]
            voiceDescriptor = songData.voiceNameToVoiceDataMap[voiceName]

            midiChannel    = voiceDescriptor.midiChannel
            midiInstrument = voiceDescriptor.midiInstrument
            midiVolume     = voiceDescriptor.midiVolume
            panPosition    = voiceDescriptor.panPosition
            reverbLevel    = voiceDescriptor.reverbLevel

            if panPosition == "C":
                panPosition = 64
            else:
                suffix      = panPosition[-1]
                offset      = int(float(panPosition[0:-1]) * 63)
                Logging.trace("--: panPosition = %s, pan = %d, suffix = %s",
                              panPosition, offset, suffix)
                panPosition = iif(suffix == "L", 63 - offset, 65 + offset)

            reverbLevel = int(127 * reverbLevel)
                
            trackSettingsEntry = \
                _TrackSettingsType( \
                    voiceName=voiceName,
                    midiChannel=adaptToRange(midiChannel, 0, 15),
                    midiInstrument=adaptToRange(midiInstrument, 0, 127),
                    midiVolume=adaptToRange(midiVolume, 0, 127),
                    panPosition=adaptToRange(panPosition, 0, 127),
                    reverbLevel=adaptToRange(reverbLevel, 0, 127))
                                   
            result[voiceName] = trackSettingsEntry

        Logging.trace("<<: %s", str(result))
        return result
        
    #--------------------

    @classmethod
    def _makePdf (cls, processingMode, targetFileNamePrefix, voiceNameList,
                  lyricsCountVocals, lyricsCountBgVocals):
        """Processes lilypond file and generates extract or score PDF
           file."""

        Logging.trace(">>: targetFilePrefix = '%s', voiceNameList='%s'"
                      + " lyricsCountVoc = %d, lyricsCountBgVoc = %d",
                      targetFileNamePrefix, str(voiceNameList),
                      lyricsCountVocals, lyricsCountBgVocals)

        tempLilypondFilePath = configData.tempLilypondFilePath
        lilypondFile = LilypondFile(tempLilypondFilePath)
        lilypondFile.generate(songData.includeFilePath, processingMode,
                              voiceNameList,
                              songData.title, songData.year,
                              lyricsCountVocals, lyricsCountBgVocals,
                              songData.useSpecialLayoutForExtracts)
        cls._processLilypond(tempLilypondFilePath, targetFileNamePrefix)
        OperatingSystem.moveFile(targetFileNamePrefix + ".pdf",
                                 configData.targetDirectoryPath)
        OperatingSystem.removeFile(tempLilypondFilePath,
                                   songData.debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _processLilypond (cls, lilypondFilePath, targetFileNamePrefix):
        """Processes <lilypondFilePath> and stores result in file with
           <targetFileNamePrefix>."""

        Logging.trace(">>: lilyFile = '%s', targetFileNamePrefix='%s'",
                      lilypondFilePath, targetFileNamePrefix)

        OperatingSystem.showMessageOnConsole("== processing "
                                             + targetFileNamePrefix)
        command = (cls._lilypondCommand,
                   "--output", targetFileNamePrefix,
                   lilypondFilePath)
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def processFinalVideo (cls):
        """Generates final videos from silent video, audio tracks and
           subtitle files."""

        Logging.trace(">>")

        tempSubtitleFilePath = "tempSubtitle.srt"
        tempMp4FilePath = "tempVideoWithSubtitles.mp4"

        # --- shift subtitles ---
        subtitleFilePath = "%s/%s" % (configData.targetDirectoryPath,
                                      (subtitleFileNameTemplate
                                       % songData.fileNamePrefix))
        VideoAudioCombiner.shiftSubtitleFile(subtitleFilePath,
                                             tempSubtitleFilePath,
                                             songData.shiftOffset)

        for videoDevice in configData.videoDeviceList:
            silentMp4FilePath = (("%s/" + silentVideoFileNameTemplate)
                                 % (configData.targetDirectoryPath,
                                    songData.fileNamePrefix,
                                    videoDevice.fileNameSuffix))

            if not songData.useHardVideoSubtitles:
                videoFilePath = silentMp4FilePath
                effectiveSubtitleFilePath = tempSubtitleFilePath
            else:
                videoFilePath = tempMp4FilePath
                effectiveSubtitleFilePath = ""
                VideoAudioCombiner.insertHardSubtitles( \
                                        silentMp4FilePath,
                                        tempSubtitleFilePath,
                                        videoFilePath,
                                        songData.shiftOffset,
                                        videoDevice.subtitleColor,
                                        videoDevice.subtitleFontSize)

            targetDirectoryPath = videoDevice.targetVideoDirectory
            ValidityChecker.isDirectory(targetDirectoryPath,
                                        "video target directory")
            targetVideoFilePath = ("%s/%s%s-%s.mp4"
                                   % (targetDirectoryPath,
                                      songData.targetFileNamePrefix,
                                      songData.fileNamePrefix,
                                      videoDevice.name))
            trackDataList = \
                AudioTrackManager.constructSettingsForOptionalVoices(songData)

            VideoAudioCombiner.combine(songData.voiceNameList, trackDataList,
                                       videoFilePath, targetVideoFilePath,
                                       effectiveSubtitleFilePath)

            mediaType = "TV Show"
            VideoAudioCombiner.tagVideoFile(targetVideoFilePath,
                                            songData.albumName,
                                            songData.artistName,
                                            songData.albumArtFilePath,
                                            songData.title, mediaType,
                                            songData.year)

        debuggingIsActive = songData.debuggingIsActive
        OperatingSystem.removeFile(tempSubtitleFilePath, debuggingIsActive)
        OperatingSystem.removeFile(tempMp4FilePath, debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processMidi (cls):
        """Generates midi file from lilypond file."""

        Logging.trace(">>")

        debuggingIsActive = songData.debuggingIsActive
        tempLilypondFilePath = configData.tempLilypondFilePath
        lilypondFile = LilypondFile(tempLilypondFilePath)
        lilypondFile.generate(songData.includeFilePath, "midi",
                              songData.voiceNameList, "", songData.year,
                              songData.lyricsCountVocals,
                              songData.lyricsCountBgVocals,
                              songData.useSpecialLayoutForExtracts)

        tempMidiFileNamePrefix = songData.fileNamePrefix + "-temp"
        tempMidiFileName = tempMidiFileNamePrefix + ".mid"
        targetMidiFileName = (cls._midiFileNameTemplate
                              % songData.fileNamePrefix)

        cls._processLilypond(tempLilypondFilePath, tempMidiFileNamePrefix)

        # postprocess MIDI file
        trackToSettingsMap = cls._calculateTrackToSettingsMap()

        midiTransformer = MidiTransformer(tempMidiFileName, debuggingIsActive)
        midiTransformer.addMissingTrackNames()
        midiTransformer.humanizeTracks(songData.styleHumanizationKind)
        midiTransformer.positionInstruments(trackToSettingsMap)
        midiTransformer.addProcessingDateToTracks()
        midiTransformer.save(targetMidiFileName)

        OperatingSystem.moveFile(targetMidiFileName,
                                 configData.targetDirectoryPath)
        OperatingSystem.removeFile(tempMidiFileName, debuggingIsActive)
        OperatingSystem.removeFile(tempLilypondFilePath, debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processMixdown (cls):
        """Mixdown audio tracks."""

        Logging.trace(">>")

        audioTrackManager = \
             AudioTrackManager(configData.tempAudioDirectoryPath)

        voiceNameToVolumeMap = {}

        for voiceName in songData.voiceNameList:
            descriptor = songData.voiceNameToVoiceDataMap[voiceName]
            voiceNameToVolumeMap[voiceName] = descriptor.audioVolume

        audioTrackManager.mixdown(songData, voiceNameToVolumeMap)
        
        Logging.trace("<<")

    #--------------------

    @classmethod
    def processRawAudio (cls):
        """Generates unprocessed audio files from generated midi file."""

        Logging.trace(">>")

        midiFilePath = (configData.targetDirectoryPath + "/"
                        + cls._midiFileNameTemplate % songData.fileNamePrefix)

        audioTrackManager = \
             AudioTrackManager(configData.tempAudioDirectoryPath)

        for voiceName in selectedVoiceNameList:
            audioTrackManager.generateRawAudio(midiFilePath, voiceName)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processRefinedAudio (cls):
        """Generates refined audio files from raw audio file."""

        Logging.trace(">>")

        voiceNameList = selectedVoiceNameList[:]
        audioTrackManager = \
             AudioTrackManager(configData.tempAudioDirectoryPath)

        # check whether the overridden voices are in list of selected
        # voices and remove them
        overriddenVoiceNameList = songData.voiceNameToOverrideFileMap.keys()
        overriddenVoiceNameList = list(set(voiceNameList)
                                       & set(overriddenVoiceNameList))
        voiceNameList = list(set(voiceNameList)
                             - set(overriddenVoiceNameList))

        Logging.trace("--: effective voiceNameList = %s,"
                      + " overriddenVoiceNameList = %s",
                      voiceNameList, overriddenVoiceNameList)

        for voiceName in voiceNameList:
            Logging.trace("--: processing voice %s", voiceName)
            voiceDescriptor = songData.voiceNameToVoiceDataMap[voiceName]
            soundVariant = voiceDescriptor.soundVariant
            reverbLevel  = voiceDescriptor.reverbLevel
            audioTrackManager.generateRefinedAudio(voiceName, soundVariant,
                                                   reverbLevel)

        for voiceName in overriddenVoiceNameList:
            overrideFile = songData.voiceNameToOverrideFileMap[voiceName]
            audioTrackManager.copyOverrideFile(overrideFile, voiceName)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processScore (cls):
        """Generates score as PDF and moves them to local target
           directory."""

        Logging.trace(">>")

        cls._makePdf("score", songData.fileNamePrefix + "_score",
                     songData.voiceNameList, songData.lyricsCountVocals,
                     songData.lyricsCountBgVocals)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processSilentVideo (cls):
        """Generates video without audio from lilypond file."""

        Logging.trace(">>")

        mmPerInch = 25.4
        debuggingIsActive = songData.debuggingIsActive
        targetSubtitleFileName = (subtitleFileNameTemplate
                                  % songData.fileNamePrefix)
        tempLilypondFilePath = configData.tempLilypondFilePath

        for videoDevice in configData.videoDeviceList:
            message = ("== generating silent video for %s" % videoDevice.name)
            OperatingSystem.showMessageOnConsole(message)

            effectiveVideoResolution = (videoDevice.resolution
                                        * configData.videoScalingFactor)
            factor = mmPerInch / videoDevice.resolution
            videoWidth  = videoDevice.width  * factor
            videoHeight = videoDevice.height * factor
            videoLineWidth = videoWidth - 2 * videoDevice.leftRightMargin
            lilypondFile = LilypondFile(tempLilypondFilePath)
            lilypondFile.setVideoParameters(effectiveVideoResolution,
                                            videoDevice.systemSize,
                                            videoDevice.topBottomMargin,
                                            videoWidth, videoHeight,
                                            videoLineWidth)
            lilypondFile.generate(songData.includeFilePath, "video",
                                  songData.videoVoiceNameList,
                                  songData.title, songData.year,
                                  songData.lyricsCountVocals,
                                  songData.lyricsCountBgVocals,
                                  songData.useSpecialLayoutForExtracts)
            targetMp4FileName = (silentVideoFileNameTemplate
                                 % (songData.fileNamePrefix,
                                    videoDevice.fileNameSuffix))
            videoGenerator = \
                LilypondPngVideoGenerator(tempLilypondFilePath,
                                          targetMp4FileName,
                                          targetSubtitleFileName,
                                          songData.tempoTrackList,
                                          countInMeasures,
                                          configData.videoFrameRate,
                                          configData.videoScalingFactor,
                                          debuggingIsActive)
            videoGenerator.process()
            videoGenerator.cleanup()

            OperatingSystem.moveFile(targetMp4FileName,
                                     configData.targetDirectoryPath)
            OperatingSystem.moveFile(targetSubtitleFileName,
                                     configData.targetDirectoryPath)

        OperatingSystem.removeFile(tempLilypondFilePath, debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processVoices (cls):
        """Generates voice extracts as PDF and move them to local
           target directory."""

        Logging.trace(">>")

        lyricsCountV  = iif(songData.useSpecialLayoutForExtracts,
                            songData.lyricsCountVocalsStandalone,
                            songData.lyricsCountVocals)
        lyricsCountBg = iif(songData.useSpecialLayoutForExtracts,
                            songData.lyricsCountBgVocalsStandalone,
                            songData.lyricsCountBgVocals)

        relevantVoiceNameList = intersection(songData.voiceNameList,
                                             selectedVoiceNameList)

        for voiceName in relevantVoiceNameList:
            Logging.trace("--: processing '%s'", voiceName)
            singleVoiceNameList = [ voiceName ]
            targetFileNamePrefix = "%s-%s" % (songData.fileNamePrefix,
                                              voiceName)
            cls._makePdf("voice", targetFileNamePrefix,
                         singleVoiceNameList, lyricsCountV, lyricsCountBg)

        Logging.trace("<<")

#--------------------
#--------------------

def conditionalExecuteHandlerProc (processingMode, requiredMode,
                                   isPreprocessing, handlerProc):
    """Checks <processingMode> for equality to <requiredMode>, for
       being part of the group pre- or postprocessing (depending on
       <isPreprocessing>) and executes <handlerProc> when processing
       mode matches"""

    Logging.trace(">>: processingMode = %s, requiredMode = %s,"
                  + " isPreprocessing = %s", processingMode, requiredMode,
                  isPreprocessing)

    allowedModeList = [ "all", requiredMode,
                        iif(isPreprocessing, "preprocess", "postprocess") ]

    if processingMode in allowedModeList:
        handlerProc()
    
    Logging.trace("<<")

#--------------------

def initialize ():
    global selectedVoiceNameList, songData

    Logging.trace(">>")

    LilypondFile.initialize(configData.lilypondMacroIncludePath)
    LilypondPngVideoGenerator.initialize(configData.ffmpegCommand,
                                         configData.lilypondCommand)
    VideoAudioCombiner.initialize(configData.ffmpegCommand,
                                  configData.mp4boxCommand)

    argumentList = _CommandLineOptions.read()
    _CommandLineOptions.check(argumentList)

    songConfigurationFileName = argumentList.configurationFilePath
    songData = MLA_SongConfigurationData()
    songData.readFile(songConfigurationFileName, selectedVoiceNameList)

    AudioTrackManager.initialize(configData.soundProcessorConfigFileName,
                                 configData.aacCommand,
                                 configData.ffmpegCommand,
                                 configData.fluidsynthCommand,
                                 configData.soxCommand,
                                 configData.soundFontDirectoryPath,
                                 configData.soundFontNameList,
                                 songData.debuggingIsActive)
    MidiTransformer.initialize(configData.humanizerConfigurationFileName,
                               songData.humanizedVoiceNameList)

    Logging.trace("<<")

#--------------------

def main ():
    global configData, selectedVoiceNameList

    configurationFilePath = \
        (OperatingSystem.dirname(OperatingSystem.scriptFilePath())
         + "/" + settingsConfigurationFileName)
    configData = MLA_OverallSettings()
    configData.readFile(configurationFilePath)

    if configData.loggingFilePath > "":
        Logging.initialize(Logging.Level_verbose, configData.loggingFilePath)
        # repeat reading of config data for having it logged
        configData.readFile(configurationFilePath)
        configData.checkValidity()
        
    initialize()

    Logging.trace(">>: processingMode = '%s'", processingMode)

    actionList = \
        (("voices",       True,  _LilypondProcessor.processVoices),
         ("score",        True,  _LilypondProcessor.processScore),
         ("midi",         True,  _LilypondProcessor.processMidi),
         ("silentvideo",  True,  _LilypondProcessor.processSilentVideo),
         ("rawaudio",     False, _LilypondProcessor.processRawAudio),
         ("refinedaudio", False, _LilypondProcessor.processRefinedAudio),
         ("mixdown",      False, _LilypondProcessor.processMixdown),
         ("finalvideo",   False, _LilypondProcessor.processFinalVideo))

    for requiredMode, isPreprocessing, handlerProc in actionList:
        conditionalExecuteHandlerProc(processingMode, requiredMode,
                                      isPreprocessing, handlerProc)

    Logging.trace("<<")

#--------------------

main()
