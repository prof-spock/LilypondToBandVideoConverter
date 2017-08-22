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
from mla_configurationdatahandler import MLA_ConfigurationData
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

processingPhaseSet = None
selectedVoiceNameSet = set()

#--------------------
#--------------------

def intersection (listA, listB):
    """Returns the intersection of lists <listA> and <listB>."""

    result = (element for element in listA if element in listB)
    return result

#--------------------

def makeMap (listA, listB):
    """Returns a map from the elements in <listA> to <listB> assuming
       that list lengths are equal"""

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
        processingPhaseSet = set(convertStringToList(argumentList.phases, "/"))

        ValidityChecker.isReadableFile(configurationFilePath,
                                       "configurationFilePath")
        allowedPhaseSet = set(["all", "preprocess", "postprocess",
                               "voices", "score", "midi", "silentvideo",
                               "rawaudio", "refinedaudio", "mixdown",
                               "finalvideo"])
        Logging.trace("--: given phase set %s, allowed phase set %s",
                      processingPhaseSet, allowedPhaseSet)
        ValidityChecker.isValid(processingPhaseSet.issubset(allowedPhaseSet),
                                "phases")

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls):
        """Reads commandline options and sets variables appropriately."""

        global processingPhaseSet, selectedVoiceNameSet

        Logging.trace(">>")

        programDescription = ("Generates lilypond files and target files"
                              + " for single voices, a complete score,"
                              + " a midi file and videos based on a"
                              + " configuration file")
        p = argparse.ArgumentParser(description=programDescription)

        p.add_argument("configurationFilePath",
                       help="name of configuration file for song")
        p.add_argument("--phases",
                       required=True,
                       help=("slash-separated list of phase names to be"
                             + " executed; (for preprocessing) tells whether"
                             + " a voice extract, a full score"
                             + " a video or a midi should be produced;"
                             + " (for postprocessing) tells whether the"
                             + " single audio tracks, the audio mixdown"
                             + " or the final video shall be produced"))
        p.add_argument("--voices",
                       default="",
                       help=("slash-separated list of voice names to be"
                             + " processed (optional, default is all voices)"))

        argumentList = p.parse_args()

        if argumentList.voices > "":
            selectedVoiceNameSet = \
              set(convertStringToList(argumentList.voices,"/"))

        processingPhaseSet = set(convertStringToList(argumentList.phases, "/"))

        Logging.trace("<<: arguments = %s, processingPhaseSet = %s,"
                      + " selectedVoiceNameSet = %s",
                      argumentList, processingPhaseSet, selectedVoiceNameSet)
        return argumentList

#====================

class _LilypondProcessor:
    """Handles generation of extracts, score, midi file and silent
       video."""

    _lilypondCommand = None
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

        for i in xrange(len(configData.voiceNameList)):
            voiceName       = configData.voiceNameList[i]
            voiceDescriptor = configData.voiceNameToVoiceDataMap[voiceName]

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

        Logging.trace("<<: %s", result)
        return result
        
    #--------------------
        
    @classmethod
    def _findVoiceSets (cls, configData, voiceNameSet):
        """Calculates set of overridden voices and remaining set of selected
           voices"""

        overriddenVoiceNameSet = \
          set(configData.voiceNameToOverrideFileMap.keys())

        Logging.trace(">>: overriddenVoiceSet = %s, voiceSet = %s",
                      overriddenVoiceNameSet, voiceNameSet)

        overriddenVoiceNameSet = (set(voiceNameSet)
                                  & set(overriddenVoiceNameSet))
        voiceNameSet = (voiceNameSet - set(overriddenVoiceNameSet))
        result = (overriddenVoiceNameSet, voiceNameSet)

        Logging.trace("<<: result = %s", result)
        return result

    #--------------------

    @classmethod
    def _makePdf (cls, processingPhase, targetFileNamePrefix, voiceNameList,
                  lyricsCountVocals, lyricsCountBgVocals):
        """Processes lilypond file and generates extract or score PDF
           file."""

        Logging.trace(">>: targetFilePrefix = '%s', voiceNameList='%s'"
                      + " lyricsCountVoc = %d, lyricsCountBgVoc = %d",
                      targetFileNamePrefix, voiceNameList,
                      lyricsCountVocals, lyricsCountBgVocals)

        tempLilypondFilePath = configData.tempLilypondFilePath
        lilypondFile = LilypondFile(tempLilypondFilePath)
        lilypondFile.generate(configData.includeFilePath, processingPhase,
                              voiceNameList,
                              configData.title,
                              configData.songComposerText,
                              lyricsCountVocals, lyricsCountBgVocals)
        cls._processLilypond(tempLilypondFilePath, targetFileNamePrefix)
        OperatingSystem.moveFile(targetFileNamePrefix + ".pdf",
                                 configData.targetDirectoryPath)
        OperatingSystem.removeFile(tempLilypondFilePath,
                                   configData.debuggingIsActive)

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
                                       % configData.fileNamePrefix))
        VideoAudioCombiner.shiftSubtitleFile(subtitleFilePath,
                                             tempSubtitleFilePath,
                                             configData.shiftOffset)

        for videoDevice in configData.videoDeviceList:
            silentMp4FilePath = (("%s/" + silentVideoFileNameTemplate)
                                 % (configData.targetDirectoryPath,
                                    configData.fileNamePrefix,
                                    videoDevice.fileNameSuffix))

            if not configData.useHardVideoSubtitles:
                videoFilePath = silentMp4FilePath
                effectiveSubtitleFilePath = tempSubtitleFilePath
            else:
                videoFilePath = tempMp4FilePath
                effectiveSubtitleFilePath = ""
                VideoAudioCombiner.insertHardSubtitles( \
                                        silentMp4FilePath,
                                        tempSubtitleFilePath,
                                        videoFilePath,
                                        configData.shiftOffset,
                                        videoDevice.subtitleColor,
                                        videoDevice.subtitleFontSize)

            targetDirectoryPath = videoDevice.targetVideoDirectory
            ValidityChecker.isDirectory(targetDirectoryPath,
                                        "video target directory")
            targetVideoFilePath = ("%s/%s%s-%s.mp4"
                                   % (targetDirectoryPath,
                                      configData.targetFileNamePrefix,
                                      configData.fileNamePrefix,
                                      videoDevice.name))
            trackDataList = \
                AudioTrackManager.constructSettingsForOptionalVoices(configData)

            VideoAudioCombiner.combine(configData.voiceNameList,
                                       trackDataList, videoFilePath,
                                       targetVideoFilePath,
                                       effectiveSubtitleFilePath)

            mediaType = "TV Show"
            VideoAudioCombiner.tagVideoFile(targetVideoFilePath,
                                            configData.albumName,
                                            configData.artistName,
                                            configData.albumArtFilePath,
                                            configData.title,
                                            mediaType,
                                            configData.songYear)

        debuggingIsActive = configData.debuggingIsActive
        OperatingSystem.removeFile(tempSubtitleFilePath, debuggingIsActive)
        OperatingSystem.removeFile(tempMp4FilePath, debuggingIsActive)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processMidi (cls):
        """Generates midi file from lilypond file."""

        Logging.trace(">>")

        debuggingIsActive = configData.debuggingIsActive
        tempLilypondFilePath = configData.tempLilypondFilePath
        lilypondFile = LilypondFile(tempLilypondFilePath)
        lilypondFile.generate(configData.includeFilePath, "midi",
                              configData.midiVoiceNameList, configData.title,
                              configData.songComposerText,
                              configData.lyricsCountVocals,
                              configData.lyricsCountBgVocals)

        tempMidiFileNamePrefix = configData.fileNamePrefix + "-temp"
        tempMidiFileName = tempMidiFileNamePrefix + ".mid"
        targetMidiFileName = (cls._midiFileNameTemplate
                              % configData.fileNamePrefix)

        cls._processLilypond(tempLilypondFilePath, tempMidiFileNamePrefix)

        # postprocess MIDI file
        trackToSettingsMap = cls._calculateTrackToSettingsMap()

        midiTransformer = MidiTransformer(tempMidiFileName, debuggingIsActive)
        midiTransformer.addMissingTrackNames()
        midiTransformer.humanizeTracks(configData.styleHumanizationKind)
        midiTransformer.positionInstruments(trackToSettingsMap)
        midiTransformer.addProcessingDateToTracks(trackToSettingsMap.keys())
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

        for voiceName in configData.voiceNameList:
            descriptor = configData.voiceNameToVoiceDataMap[voiceName]
            voiceNameToVolumeMap[voiceName] = descriptor.audioVolume

        audioTrackManager.mixdown(configData, voiceNameToVolumeMap)
        
        Logging.trace("<<")

    #--------------------

    @classmethod
    def processRawAudio (cls):
        """Generates unprocessed audio files from generated midi file."""

        Logging.trace(">>")

        midiFilePath = (configData.targetDirectoryPath + "/"
                        + (cls._midiFileNameTemplate
                           % configData.fileNamePrefix))

        audioTrackManager = \
             AudioTrackManager(configData.tempAudioDirectoryPath)

        for voiceName in selectedVoiceNameSet:
            audioTrackManager.generateRawAudio(midiFilePath, voiceName,
                                               configData.shiftOffset)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processRefinedAudio (cls):
        """Generates refined audio files from raw audio file."""

        Logging.trace(">>")

        audioTrackManager = \
             AudioTrackManager(configData.tempAudioDirectoryPath)

        overriddenVoiceNameSet, voiceNameSet = \
            cls._findVoiceSets(configData, selectedVoiceNameSet)

        for voiceName in voiceNameSet:
            Logging.trace("--: processing voice %s", voiceName)
            voiceDescriptor = configData.voiceNameToVoiceDataMap[voiceName]
            soundVariant = voiceDescriptor.soundVariant
            reverbLevel  = voiceDescriptor.reverbLevel
            audioTrackManager.generateRefinedAudio(voiceName, soundVariant,
                                                   reverbLevel)

        for voiceName in overriddenVoiceNameSet:
            overrideFile = configData.voiceNameToOverrideFileMap[voiceName]
            audioTrackManager.copyOverrideFile(overrideFile, voiceName,
                                               configData.shiftOffset)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processScore (cls):
        """Generates score as PDF and moves them to local target
           directory."""

        Logging.trace(">>")

        cls._makePdf("score", configData.fileNamePrefix + "_score",
                     configData.voiceNameList, configData.lyricsCountVocals,
                     configData.lyricsCountBgVocals)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processSilentVideo (cls):
        """Generates video without audio from lilypond file."""

        Logging.trace(">>")

        mmPerInch = 25.4
        debuggingIsActive = configData.debuggingIsActive
        targetSubtitleFileName = (subtitleFileNameTemplate
                                  % configData.fileNamePrefix)
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
            lilypondFile.generate(configData.includeFilePath, "video",
                                  configData.videoVoiceNameList,
                                  configData.title, configData.songComposerText,
                                  configData.lyricsCountVocals,
                                  configData.lyricsCountBgVocals)
            targetMp4FileName = (silentVideoFileNameTemplate
                                 % (configData.fileNamePrefix,
                                    videoDevice.fileNameSuffix))
            videoGenerator = \
                LilypondPngVideoGenerator(tempLilypondFilePath,
                                          targetMp4FileName,
                                          targetSubtitleFileName,
                                          configData.measureToTempoMap,
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

        lyricsCountV  = configData.lyricsCountVocalsStandalone
        lyricsCountBg = configData.lyricsCountBgVocalsStandalone
        
        relevantVoiceNameSet = (selectedVoiceNameSet
                                & configData.extractVoiceNameSet)

        for voiceName in relevantVoiceNameSet:
            Logging.trace("--: processing '%s'", voiceName)
            singleVoiceNameList = [ voiceName ]
            targetFileNamePrefix = "%s-%s" % (configData.fileNamePrefix,
                                              voiceName)
            cls._makePdf("voice", targetFileNamePrefix,
                         singleVoiceNameList, lyricsCountV, lyricsCountBg)

        Logging.trace("<<")

#--------------------
#--------------------

def conditionalExecuteHandlerProc (processingPhase, processingPhaseSet,
                                   isPreprocessing, handlerProc):
    """Checks whether <processingPhase> occurs in <processingPhaseSet>, for
       being part of the group pre- or postprocessing (depending on
       <isPreprocessing>) and executes <handlerProc> when processing
       phase matches"""

    Logging.trace(">>: processingPhase = %s, processingPhaseSet = %s,"
                  + " isPreprocessing = %s",
                  processingPhase, processingPhaseSet, isPreprocessing)

    allowedPhaseSet = set([ "all", processingPhase,
                            iif(isPreprocessing, "preprocess", "postprocess")])

    if len(allowedPhaseSet.intersection(processingPhaseSet)) > 0:
        handlerProc()
    
    Logging.trace("<<")

#--------------------

def initialize ():
    global configData, selectedVoiceNameSet

    Logging.trace(">>")

    argumentList = _CommandLineOptions.read()
    _CommandLineOptions.check(argumentList)

    configData = MLA_ConfigurationData()
    configData.readFile(argumentList.configurationFilePath,
                        selectedVoiceNameSet)
    Logging.setFileName(configData.loggingFilePath)

    # initialize all the submodules with configuration information
    _LilypondProcessor._lilypondCommand = configData.lilypondCommand
    LilypondPngVideoGenerator.initialize(configData.ffmpegCommand,
                                         configData.lilypondCommand)
    VideoAudioCombiner.initialize(configData.ffmpegCommand,
                                  configData.mp4boxCommand)

    LilypondFile.initialize(configData.measureToTempoMap)
    AudioTrackManager.initialize(configData.soundProcessorConfigFileName,
                                 configData.aacCommand,
                                 configData.ffmpegCommand,
                                 configData.fluidsynthCommand,
                                 configData.soxCommand,
                                 configData.soxGlobalOptions,
                                 configData.soundFontDirectoryPath,
                                 configData.soundFontNameList,
                                 configData.debuggingIsActive)
    MidiTransformer.initialize(configData.humanizerConfigurationFileName,
                               configData.humanizedVoiceNameSet)

    Logging.trace("<<")

#--------------------

def main ():
    Logging.initialize()
    Logging.setLevel(Logging.Level_verbose)
    Logging.trace(">>")

    initialize()

    Logging.trace("--: processingPhaseSet = %s", processingPhaseSet)

    actionList = \
        (("voices",       True,  _LilypondProcessor.processVoices),
         ("score",        True,  _LilypondProcessor.processScore),
         ("midi",         True,  _LilypondProcessor.processMidi),
         ("silentvideo",  True,  _LilypondProcessor.processSilentVideo),
         ("rawaudio",     False, _LilypondProcessor.processRawAudio),
         ("refinedaudio", False, _LilypondProcessor.processRefinedAudio),
         ("mixdown",      False, _LilypondProcessor.processMixdown),
         ("finalvideo",   False, _LilypondProcessor.processFinalVideo))

    for processingPhase, isPreprocessing, handlerProc in actionList:
        conditionalExecuteHandlerProc(processingPhase, processingPhaseSet,
                                      isPreprocessing, handlerProc)

    Logging.trace("<<")

#--------------------

main()
