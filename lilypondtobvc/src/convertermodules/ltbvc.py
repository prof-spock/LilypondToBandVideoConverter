# -*- coding: utf-8-unix -*-
# ltbvc -- script that produces lilypond files and target files
#          for single voices, a complete score, a midi file, audio and
#          video files based on a configuration file from a lilypond
#          music fragment file

# author: Dr. Thomas Tensi, 2006 - 2018

#====================
# IMPORTS
#====================

import argparse
import sys

from basemodules.operatingsystem import OperatingSystem
from basemodules.simplelogging import Logging
from basemodules.ttbase import convertStringToList, iif
from basemodules.validitychecker import ValidityChecker

from .audiotrackmanager import AudioTrackManager
from .lilypondfilegenerator import LilypondFile
from .lilypondpngvideogenerator import LilypondPngVideoGenerator
from .ltbvc_businesstypes import TrackSettings
from .ltbvc_configurationdatahandler import LTBVC_ConfigurationData
from .miditransformer import MidiTransformer
from .videoaudiocombiner import VideoAudioCombiner

#====================
# TYPE DEFINITIONS
#====================

countInMeasures = 2

subtitleFileNameTemplate = "%s_subtitle.srt"
silentVideoFileNameTemplate = "%s_noaudio%s.mp4"

#--------------------

configData = None

processingPhaseSet = None
selectedVoiceNameSet = set()
intermediateFilesAreKept = None

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

    for i in range(len(listA)):
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
                               "extract", "score", "midi", "silentvideo",
                               "rawaudio", "refinedaudio", "mixdown",
                               "finalvideo"])
        Logging.trace("--: given phase set %s, allowed phase set %s",
                      processingPhaseSet, allowedPhaseSet)
        ValidityChecker.isValid(processingPhaseSet.issubset(allowedPhaseSet),
                                "bad phases - %s"
                                % str(list(processingPhaseSet))[1:-1])

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls):
        """Reads commandline options and sets variables appropriately."""

        global intermediateFilesAreKept, processingPhaseSet
        global selectedVoiceNameSet

        Logging.trace(">>")

        programDescription = ("Generates lilypond files and target files"
                              + " for single voices, a complete score,"
                              + " a midi file and videos based on a"
                              + " configuration file")
        p = argparse.ArgumentParser(description=programDescription)

        p.add_argument("-k", action="store_true", dest="keepFiles",
                       help="tells to keep intermediate files")
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
        intermediateFilesAreKept = argumentList.keepFiles

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
    _pathSeparator = OperatingSystem.pathSeparator

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

        for i in range(len(configData.voiceNameList)):
            voiceName       = configData.voiceNameList[i]
            voiceDescriptor = configData.voiceNameToVoiceDataMap[voiceName]
            Logging.trace("--: %s", voiceDescriptor)

            midiChannel    = voiceDescriptor.midiChannel
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

            midiInstrument = voiceDescriptor.midiInstrument

            if ':' not in midiInstrument:
                midiInstrumentBank, midiInstrument = 0, int(midiInstrument)
            else:
                midiInstrumentBank, midiInstrument = midiInstrument.split(":")
                midiInstrumentBank = int(midiInstrumentBank)
                midiInstrument     = int(midiInstrument)

            reverbLevel = int(127 * reverbLevel)

            trackSettingsEntry = \
                TrackSettings(voiceName, midiChannel, midiInstrumentBank,
                              midiInstrument, midiVolume, panPosition,
                              reverbLevel)

            result[voiceName] = trackSettingsEntry

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def _findOverriddenVoiceSets (cls, configData, voiceNameSet):
        """Calculates set of overridden voices and remaining set
           of selected voices"""

        overriddenVoiceNameSet = \
          set(configData.voiceNameToOverrideFileNameMap.keys())

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
    def _makePdf (cls, processingPhase, targetFileNamePrefix,
                  voiceNameList):
        """Processes lilypond file and generates extract or score PDF
           file."""

        Logging.trace(">>: targetFilePrefix = '%s', voiceNameList='%s'",
                      targetFileNamePrefix, voiceNameList)

        tempLilypondFilePath = configData.tempLilypondFilePath
        lilypondFile = LilypondFile(tempLilypondFilePath)
        lilypondFile.generate(configData.includeFilePath, processingPhase,
                              voiceNameList,
                              configData.title,
                              configData.songComposerText,
                              configData.voiceNameToChordsMap,
                              configData.voiceNameToLyricsMap,
                              configData.voiceNameToScoreNameMap,
                              configData.phaseAndVoiceNameToClefMap,
                              configData.phaseAndVoiceNameToStaffListMap)
        cls._processLilypond(tempLilypondFilePath, targetFileNamePrefix)
        OperatingSystem.moveFile(targetFileNamePrefix + ".pdf",
                                 configData.targetDirectoryPath)
        OperatingSystem.removeFile(tempLilypondFilePath,
                                   configData.intermediateFilesAreKept)

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
    def processExtract (cls):
        """Generates voice extracts as PDF and move them to local
           target directory."""

        Logging.trace(">>")

        relevantVoiceNameSet = (selectedVoiceNameSet
                                & configData.extractVoiceNameSet)

        for voiceName in relevantVoiceNameSet:
            Logging.trace("--: processing '%s'", voiceName)
            singleVoiceNameList = [ voiceName ]
            targetFileNamePrefix = "%s-%s" % (configData.fileNamePrefix,
                                              voiceName)
            cls._makePdf("extract", targetFileNamePrefix, singleVoiceNameList)

        Logging.trace("<<")

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

        for name, videoFileKind in configData.videoFileKindMap.items():
            silentMp4FilePath = (("%s/" + silentVideoFileNameTemplate)
                                 % (configData.targetDirectoryPath,
                                    configData.fileNamePrefix,
                                    videoFileKind.fileNameSuffix))
            videoTargetName = videoFileKind.target

            if videoTargetName not in configData.videoTargetMap:
                Logging.trace("--: unknown video target %s for file kind %s",
                              videoTargetName, videoFileKind.name)
            else:
                videoTarget = configData.videoTargetMap[videoTargetName]

                if not videoTarget.subtitlesAreHardcoded:
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
                                            videoTarget.subtitleColor,
                                            videoTarget.subtitleFontSize)

                targetDirectoryPath = videoFileKind.directoryPath
                ValidityChecker.isDirectory(targetDirectoryPath,
                                            "video target directory")
                targetVideoFilePath = ("%s/%s%s-%s.mp4"
                                       % (targetDirectoryPath,
                                          configData.targetFileNamePrefix,
                                          configData.fileNamePrefix,
                                          videoTarget.name))
                trackDataList = \
                   AudioTrackManager.constructSettingsForAudioTracks(configData)

                VideoAudioCombiner.combine(videoFileKind.voiceNameList,
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

        intermediateFilesAreKept = configData.intermediateFilesAreKept
        OperatingSystem.removeFile(tempSubtitleFilePath,
	                           intermediateFilesAreKept)
        OperatingSystem.removeFile(tempMp4FilePath,
	                           intermediateFilesAreKept)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processMidi (cls):
        """Generates midi file from lilypond file."""

        Logging.trace(">>")

        intermediateFilesAreKept = configData.intermediateFilesAreKept
        tempLilypondFilePath = configData.tempLilypondFilePath
        lilypondFile = LilypondFile(tempLilypondFilePath)
        lilypondFile.generate(configData.includeFilePath, "midi",
                              configData.midiVoiceNameList, configData.title,
                              configData.songComposerText,
                              configData.voiceNameToChordsMap,
                              configData.voiceNameToLyricsMap,
                              configData.voiceNameToScoreNameMap,
                              configData.phaseAndVoiceNameToClefMap,
                              configData.phaseAndVoiceNameToStaffListMap)

        tempMidiFileNamePrefix = (configData.intermediateFileDirectoryPath
                                  + cls._pathSeparator
                                  + configData.fileNamePrefix + "-temp")
        tempMidiFileName = tempMidiFileNamePrefix + ".mid"
        targetMidiFileName = (cls._midiFileNameTemplate
                              % configData.fileNamePrefix)

        cls._processLilypond(tempLilypondFilePath, tempMidiFileNamePrefix)

        # postprocess MIDI file
        OperatingSystem.showMessageOnConsole("== adapting MIDI into "
                                             + targetMidiFileName)
        trackToSettingsMap = cls._calculateTrackToSettingsMap()

        midiTransformer = MidiTransformer(tempMidiFileName,
	                                  intermediateFilesAreKept)
        midiTransformer.addMissingTrackNames()
        midiTransformer.humanizeTracks(configData.countInMeasureCount,
                            configData.measureToHumanizationStyleNameMap)
        midiTransformer.positionInstruments(trackToSettingsMap)
        midiTransformer.addProcessingDateToTracks(trackToSettingsMap.keys())
        midiTransformer.save(targetMidiFileName)

        OperatingSystem.moveFile(targetMidiFileName,
                                 configData.targetDirectoryPath)
        OperatingSystem.removeFile(tempMidiFileName,
	                           intermediateFilesAreKept)
        OperatingSystem.removeFile(tempLilypondFilePath,
	                           intermediateFilesAreKept)

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
            voiceNameToVolumeMap[voiceName] = descriptor.audioLevel

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

        relevantVoiceNameSet = (selectedVoiceNameSet
                                & configData.audioVoiceNameSet)
        audioTrackManager = \
             AudioTrackManager(configData.tempAudioDirectoryPath)

        for voiceName in relevantVoiceNameSet:
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
        relevantVoiceNameSet = (selectedVoiceNameSet
                                & configData.audioVoiceNameSet)
        overriddenVoiceNameSet, voiceNameSet = \
            cls._findOverriddenVoiceSets(configData,
                                         relevantVoiceNameSet)

        for voiceName in voiceNameSet:
            Logging.trace("--: processing voice %s", voiceName)
            voiceDescriptor = configData.voiceNameToVoiceDataMap[voiceName]
            soundVariant = voiceDescriptor.soundVariant
            reverbLevel  = voiceDescriptor.reverbLevel
            audioTrackManager.generateRefinedAudio(voiceName, soundVariant,
                                                   reverbLevel)

        for voiceName in overriddenVoiceNameSet:
            overrideFile = configData.voiceNameToOverrideFileNameMap[voiceName]
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
                     configData.scoreVoiceNameList)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processSilentVideo (cls):
        """Generates video without audio from lilypond file."""

        Logging.trace(">>")

        mmPerInch = 25.4
        intermediateFilesAreKept = configData.intermediateFilesAreKept
        intermediateFileDirectoryPath = \
            configData.intermediateFileDirectoryPath
        targetDirectoryPath = configData.targetDirectoryPath
        targetSubtitleFileName = (targetDirectoryPath
                                  + cls._pathSeparator
                                  + (subtitleFileNameTemplate
                                     % configData.fileNamePrefix))
        tempLilypondFilePath = configData.tempLilypondFilePath

        for name, videoFileKind in configData.videoFileKindMap.items():
            message = ("== generating silent video for %s"
                       % videoFileKind.name)
            OperatingSystem.showMessageOnConsole(message)
            videoTargetName = videoFileKind.target

            if videoTargetName not in configData.videoTargetMap:
                Logging.trace("--: unknown video target %s for file kind %s",
                              videoTargetName, videoFileKind.name)
            else:
                videoTarget = configData.videoTargetMap[videoTargetName]
                effectiveVideoResolution = (videoTarget.resolution
                                            * videoTarget.scalingFactor)
                factor = mmPerInch / videoTarget.resolution
                videoWidth  = videoTarget.width  * factor
                videoHeight = videoTarget.height * factor
                videoLineWidth = videoWidth - 2 * videoTarget.leftRightMargin
                lilypondFile = LilypondFile(tempLilypondFilePath)
                lilypondFile.setVideoParameters(videoTarget.name,
                                                effectiveVideoResolution,
                                                videoTarget.systemSize,
                                                videoTarget.topBottomMargin,
                                                videoWidth, videoHeight,
                                                videoLineWidth)
                lilypondFile.generate(configData.includeFilePath, "video",
                                    videoFileKind.voiceNameList,
                                    configData.title,
                                    configData.songComposerText,
                                    configData.voiceNameToChordsMap,
                                    configData.voiceNameToLyricsMap,
                                    configData.voiceNameToScoreNameMap,
                                    configData.phaseAndVoiceNameToClefMap,
                                    configData.phaseAndVoiceNameToStaffListMap)
                targetMp4FileName = (targetDirectoryPath
                                     + cls._pathSeparator
                                     + (silentVideoFileNameTemplate
                                        % (configData.fileNamePrefix,
                                           videoFileKind.fileNameSuffix)))
                videoGenerator = \
                    LilypondPngVideoGenerator(tempLilypondFilePath,
                                              targetMp4FileName,
                                              targetSubtitleFileName,
                                              configData.measureToTempoMap,
                                              countInMeasures,
                                              videoTarget.frameRate,
                                              videoTarget.scalingFactor,
                                              intermediateFileDirectoryPath,
                                              intermediateFilesAreKept)
                videoGenerator.process()
                videoGenerator.cleanup()

                ##OperatingSystem.moveFile(targetMp4FileName,
                ##                         configData.targetDirectoryPath)
                ##OperatingSystem.moveFile(targetSubtitleFileName,
                ##                         configData.targetDirectoryPath)

        OperatingSystem.removeFile(tempLilypondFilePath,
	                           intermediateFilesAreKept)

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

    configData = LTBVC_ConfigurationData()
    configurationFilePath = argumentList.configurationFilePath
    configurationFile = configData.readFile(configurationFilePath)

    if configurationFile is None:
        Logging.trace("--: cannot process configuration file '%s'",
                      configurationFilePath)
        isOkay = False
    else:
        isOkay = True
        loggingFilePath = configData.get("loggingFilePath")

        if loggingFilePath is None:
            Logging.setFileName("STDERR")
            ValidityChecker.isValid(False, "loggingFilePath not set")

        Logging.setFileName(loggingFilePath)
        configData.checkAndSetDerivedVariables(selectedVoiceNameSet)

        # override config file setting from command line option
        if intermediateFilesAreKept:
            configData.intermediateFilesAreKept = True

        # initialize all the submodules with configuration information
        _LilypondProcessor._lilypondCommand = configData.lilypondCommand
        LilypondPngVideoGenerator.initialize(configData.ffmpegCommand,
                                             configData.lilypondCommand)
        VideoAudioCombiner.initialize(configData.ffmpegCommand,
                                      configData.mp4boxCommand)

        LilypondFile.initialize(configData.measureToTempoMap)
        AudioTrackManager.initialize(configData.aacCommandLine,
                                     configData.ffmpegCommand,
                                     configData.fluidsynthCommand,
                                     configData.soxCommandLinePrefix,
                                     configData.soundFontDirectoryPath,
                                     configData.soundFontNameList,
                                     configData.soundStyleNameToTextMap,
                                     configData.intermediateFilesAreKept)
        MidiTransformer.initialize(configData.voiceNameToVariationFactorMap,
                                   configData.humanizationStyleNameToTextMap,
                                   configData.humanizedVoiceNameSet)

    Logging.trace("<<: %s", isOkay)
    return isOkay

#--------------------

def main ():
    Logging.initialize()
    Logging.setLevel(Logging.Level_verbose)
    #Logging.setFileName("/temp/logs/test.log")
    Logging.trace(">>")

    isOkay = initialize()

    if isOkay:
        Logging.trace("--: processingPhaseSet = %s", processingPhaseSet)

        actionList = \
            (("extract",      True,  _LilypondProcessor.processExtract),
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

if __name__ == "__main__":
    main()
