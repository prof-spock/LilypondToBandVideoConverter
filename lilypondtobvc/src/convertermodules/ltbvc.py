# ltbvc -- script that produces lilypond files and destination files
#          for single voices, a complete score, a midi file, audio and
#          video files based on a configuration file from a lilypond
#          music fragment file
#
# author: Dr. Thomas Tensi, 2006 - 2026

#====================
# IMPORTS
#====================

import argparse
import re
import time

from basemodules.datatypesupport import SETATTR
from basemodules.operatingsystem import OperatingSystem
from basemodules.progressmessage import ProgressMessage
from basemodules.simplelogging import Logging, Logging_Level
from basemodules.simpletypes import \
    Boolean, Callable, List, Map, Natural, Real, String, \
    StringList, StringMap, StringSet, Tuple
from basemodules.stringutil import deserializeToList
from basemodules.ttbase import iif
from basemodules.validitychecker import ValidityChecker

from .audiotrackmanager import AudioTrackManager
from .lilypondfilegenerator import LilypondFile
from .lilypondpngvideogenerator import LilypondPngVideoGenerator
from .ltbvc_businesstypes import \
    MidiTrackSettings, VideoDestination, VideoFileKind
from .ltbvc_configurationdatahandler import LTBVC_ConfigurationData
from .miditransformer import MidiTransformer
from .videoaudiocombiner import VideoAudioCombiner

#====================

_programName = "lilypondToBandVideoConverter"
_subtitleFileNameTemplate = "%s_subtitle.srt"
_silentVideoFileNameTemplate = "%s_noaudio%s.%s"

# file name used for disabling logging
lowerCasedNullLoggingFileName = "none"

#--------------------
#--------------------

def intersection (listA : List, listB : List) -> List:
    """Returns the intersection of lists <listA> and <listB>."""

    result = (element for element in listA if element in listB)
    return result

#--------------------

def makeMap (listA : List, listB : List) -> Map:
    """Returns a map from the elements in <listA> to <listB> assuming
       that list lengths are equal"""

    result = {}

    for i, key in enumerate(listA):
        value = listB[i]
        result[key] = value

    return result

#====================
# TYPE DEFINITIONS
#====================

class _CommandLineOptions:
    """This module handles command line options and checks them."""

    #--------------------

    @classmethod
    def checkArguments (cls,
                        argumentList : StringList):
        """Checks whether command line options given in <argumentList>
           are okay"""

        Logging.trace(">>")

        configurationFilePath = argumentList.configurationFilePath
        loggingFilePath = argumentList.loggingFilePath
        givenPhaseSet = set(deserializeToList(argumentList.phases, "/"))

        ValidityChecker.isReadableFile(configurationFilePath,
                                       "configurationFilePath")

        if loggingFilePath is not None:
            if loggingFilePath.lower() != lowerCasedNullLoggingFileName:
                ValidityChecker.isWritableFile(loggingFilePath,
                                               "loggingFilePath")

        allowedPhaseSet = set(["all", "preprocess", "postprocess",
                               "extract", "score", "midi", "silentvideo",
                               "rawaudio", "refinedaudio", "mix",
                               "finalvideo"])
        Logging.trace("--: given phase set %r, allowed phase set %r",
                      givenPhaseSet, allowedPhaseSet)
        ValidityChecker.isValid(givenPhaseSet.issubset(allowedPhaseSet),
                                "bad phases - %s"
                                % str(list(givenPhaseSet))[1:-1])

        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls):
        """Reads commandline options and sets variables appropriately;
           returns tuple of variables read"""

        Logging.trace(">>")

        programDescription = ("Generates lilypond files and destination"
                              + " files for single voices, a complete"
                              + " score, a midi file and videos based"
                              + " on a configuration file")
        p = argparse.ArgumentParser(prog = _programName,
                                    description = programDescription)

        p.add_argument("-k", action="store_true", dest="keepFiles",
                       help="tells to keep intermediate files")
        p.add_argument("configurationFilePath",
                       help="name of configuration file for song")
        p.add_argument("-l", "--loggingFilePath",
                       help="name of logging file (for debugging)")
        p.add_argument("--phases",
                       required=True,
                       help=("slash-separated list of phase names to be"
                             + " executed; (for preprocessing) tells whether"
                             + " a voice extract, a full score"
                             + " a video or a midi should be produced;"
                             + " (for postprocessing) tells whether the"
                             + " single audio tracks, the audio mixing"
                             + " or the final video shall be produced"))
        p.add_argument("--voices",
                       default="",
                       help=("slash-separated list of voice names to be"
                             + " processed (optional, default is all voices)"))

        argumentList = p.parse_args()

        if argumentList.voices == "":
            selectedVoiceNameSet = set()
        else:
            selectedVoiceNameSet = \
              set(deserializeToList(argumentList.voices,"/"))

        processingPhaseSet = set(deserializeToList(argumentList.phases, "/"))
        intermediateFilesAreKept = argumentList.keepFiles

        result = (intermediateFilesAreKept, processingPhaseSet,
                  selectedVoiceNameSet, argumentList)

        Logging.trace("<<: intermediateFilesAreKept = %r,"
                      + " processingPhaseSet = %r,"
                      + " selectedVoiceNameSet = %r,"
                      + " arguments = %r",
                      intermediateFilesAreKept, processingPhaseSet,
                      selectedVoiceNameSet, argumentList)
        return result

#====================

class _LilypondProcessor:
    """Handles generation of extracts, score, midi file and silent
       video."""

    _configData = None
    _selectedVoiceNameSet = set()
    _lilypondCommand = None
    _midiFileNameTemplate = "%s-std.mid"
    _pathSeparator = OperatingSystem.pathSeparator

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _adaptTempFileName (cls,
                            processingPhase : String,
                            voiceNameList : StringList):
        """Constructs a temporary lilypond file name from configuration data
           and settings <processingPhase> and <voiceNameList>"""

        Logging.trace(">>: phase = %r, voices = %r",
                      processingPhase, voiceNameList)

        template = cls._configData.tempLilypondFilePath

        if processingPhase == "extract":
            # assume there is only one voice in voice list
            voiceName = voiceNameList[0]
            template = template.replace("${voiceName}", voiceName)
        else:
            # strip off the voice name placeholder and any separator
            # characters
            regexp = re.compile(r"[\(\[_\- ]*\$\{voiceName\}[\)\]_\- ]*")
            template = regexp.sub("", template)

        result = template.replace("${phase}", processingPhase)
        Logging.trace("<<: %r", result)
        return result
        
    #--------------------

    @classmethod
    def _calculateMidiMapsFromConfiguration (cls) -> Tuple:
        """Collects data from configuration file and returns mappings from
           voice name to midi instrument, midi volume and midi pan
           position"""

        Logging.trace(">>")

        voiceNameToVoiceDataMap = cls._configData.voiceNameToVoiceDataMap

        voiceNameToMidiInstrumentMap = {}
        voiceNameToMidiVolumeMap     = {}
        voiceNameToMidiPanMap        = {}

        for _, voiceName in enumerate(cls._configData.voiceNameList):
            voiceDescriptor = voiceNameToVoiceDataMap[voiceName]
            Logging.trace("--: %r", voiceDescriptor)

            midiInstrument = voiceDescriptor.midiInstrument
            midiVolume     = voiceDescriptor.midiVolume
            panPosition    = voiceDescriptor.panPosition

            midiInstrumentBank, midiInstrument = \
                cls._stringToMidiInstrument(midiInstrument)
            panPosition = cls._stringToMidiPanPosition(panPosition)

            voiceNameToMidiInstrumentMap[voiceName] = midiInstrument
            voiceNameToMidiVolumeMap[voiceName]     = midiVolume
            voiceNameToMidiPanMap[voiceName]        = panPosition

        result = (voiceNameToMidiInstrumentMap,
                  voiceNameToMidiVolumeMap,
                  voiceNameToMidiPanMap)

        Logging.trace("<<: %r", result)
        return result

    #--------------------
        
    @classmethod
    def _calculateTrackToSettingsMap (cls) -> StringMap:
        """Collects data from configuration file for all the settings
           of each track and returns map from track name to midi
           channel, volume, pan position and reverb level"""

        Logging.trace(">>")

        result = {}
        voiceNameToVoiceDataMap = cls._configData.voiceNameToVoiceDataMap

        for _, voiceName in enumerate(cls._configData.voiceNameList):
            voiceDescriptor = voiceNameToVoiceDataMap[voiceName]
            Logging.trace("--: %r", voiceDescriptor)

            midiChannel    = voiceDescriptor.midiChannel
            midiInstrument = voiceDescriptor.midiInstrument
            midiVolume     = voiceDescriptor.midiVolume
            panPosition    = voiceDescriptor.panPosition
            reverbLevel    = voiceDescriptor.reverbLevel

            midiPanPosition = cls._stringToMidiPanPosition(panPosition)
            midiInstrumentBank, midiInstrument = \
                cls._stringToMidiInstrument(midiInstrument)
            midiReverbLevel = int(127 * reverbLevel)

            trackSettingsEntry = \
                MidiTrackSettings(voiceName, midiChannel,
                                  midiInstrumentBank, midiInstrument,
                                  midiVolume, midiPanPosition,
                                  midiReverbLevel)

            result[voiceName] = trackSettingsEntry

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _findOverriddenVoiceSets (cls,
                                  voiceNameSet : StringSet) -> StringSet:
        """Calculates set of overridden voices and remaining set
           of selected voices"""

        overriddenVoiceNameSet = \
          set(cls._configData.voiceNameToOverrideFileNameMap.keys())

        Logging.trace(">>: overriddenVoiceSet = %r, voiceSet = %r",
                      overriddenVoiceNameSet, voiceNameSet)

        overriddenVoiceNameSet = (set(voiceNameSet)
                                  & set(overriddenVoiceNameSet))
        voiceNameSet = (voiceNameSet - set(overriddenVoiceNameSet))
        result = (overriddenVoiceNameSet, voiceNameSet)

        Logging.trace("<<: result = %r", result)
        return result

    #--------------------

    @classmethod
    def _makePdf (cls,
                  processingPhase : String,
                  destinationFileNamePrefix : String,
                  voiceNameList : StringList):
        """Processes lilypond file and generates extract or score PDF
           file."""

        Logging.trace(">>: destinationFilePrefix = %r,"
                      + " voiceNameList=%r",
                      destinationFileNamePrefix, voiceNameList)

        tempLilypondFilePath = \
            cls._adaptTempFileName(processingPhase, voiceNameList)
        configData = cls._configData
        lilypondFile = LilypondFile(tempLilypondFilePath)
        lilypondFile.generate(configData.includeFilePath,
                              configData.lilypondVersion,
                              processingPhase, voiceNameList,
                              configData.title,
                              configData.songComposerText,
                              configData.voiceNameToChordsMap,
                              configData.voiceNameToLyricsMap,
                              configData.voiceNameToScoreNameMap,
                              configData.measureToTempoMap,
                              configData.phaseAndVoiceNameToClefMap,
                              configData.phaseAndVoiceNameToStaffListMap)
        cls._processLilypond(tempLilypondFilePath,
                             destinationFileNamePrefix)
        OperatingSystem.moveFile(destinationFileNamePrefix + ".pdf",
                                 configData.destinationDirectoryPath)
        OperatingSystem.removeFile(tempLilypondFilePath,
                                   configData.intermediateFilesAreKept)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _postprocessMidiFile (cls, midiFileName):
        """Postprocesses previously generated MIDI file named
           <midiFileName> adding some humanization"""

        Logging.trace(">>")

        configData = cls._configData
        destinationMidiFileName = (cls._midiFileNameTemplate
                                   % configData.fileNamePrefix)

        ProgressMessage.reportProcessingStart("adapting MIDI into "
                                              + destinationMidiFileName)

        trackToSettingsMap = cls._calculateTrackToSettingsMap()

        midiTransformer = \
            MidiTransformer(midiFileName,
                            configData.intermediateFilesAreKept,
                            configData.largeBankNumbersAreSupported)
        midiTransformer.addMissingTrackNames()
        midiTransformer.humanizeTracks(configData.countInMeasureCount,
                        configData.measureToHumanizationStyleNameMap)
        midiTransformer.positionInstruments(trackToSettingsMap)
        midiTransformer.addProcessingDateToTracks(trackToSettingsMap.keys())
        midiTransformer.save(destinationMidiFileName)

        OperatingSystem.moveFile(destinationMidiFileName,
                                 configData.destinationDirectoryPath)

        ProgressMessage.reportProcessingEnd()

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _processLilypond (cls,
                          lilypondFilePath : String,
                          destinationFileNamePrefix : String):
        """Processes <lilypondFilePath> and stores result in file with
           <destinationFileNamePrefix>."""

        Logging.trace(">>: lilyFile = %r, destinationFileNamePrefix=%r",
                      lilypondFilePath, destinationFileNamePrefix)

        ProgressMessage.reportProcessingStart("processing %s with lilypond"
                                              % destinationFileNamePrefix)
        command = (cls._lilypondCommand,
                   "--output", destinationFileNamePrefix,
                   lilypondFilePath)
        OperatingSystem.executeCommand(command, True)
        ProgressMessage.reportProcessingEnd()

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _processSingleFinalVideoFile (cls,
                                      videoDestination : VideoDestination,
                                      videoFileKindName : String,
                                      videoFileExtension : String,
                                      voiceNameList : StringList,
                                      silentVideoFilePath : String,
                                      tempMp4FilePath : String,
                                      tempSubtitleFilePath : String,
                                      destinationVideoFilePath : String):
        """Generates final video from silent video, audio tracks and
           subtitle files for given <videoDestination>;
           <videoFileExtension> gives the extension of the video file
           generated, <voiceNameList> gives the list of affected
           voices, <silentVideoFilePath> the path of the silent video
           source, <tempMp4FilePath> the path for a generated
           temporary MP4 video, <tempSubtitleFilePath> the path of the
           subtitle file and <destinationVideoFilePath> the path for the
           destination files"""

        Logging.trace(">>: videoDestination = %s,"
                      + " videoFileExtension = '%s',"
                      + " silentVideoFilePath = '%s',"
                      + " voiceNameList = %r,"
                      + " tempMp4FilePath = '%s',"
                      + " tempSubtitleFilePath = '%s',"
                      + " destinationVideoFilePath = '%s'",
                      videoDestination, videoFileExtension,
                      silentVideoFilePath, voiceNameList,
                      tempMp4FilePath, tempSubtitleFilePath,
                      destinationVideoFilePath)

        isTarFile = (videoFileExtension == "tar")
        messageTemplate = (iif(isTarFile, "copying",  "generating")
                           + " final video for %s")
        message = (messageTemplate % videoFileKindName)
        ProgressMessage.reportProcessingStart(message)

        if isTarFile:
            if not OperatingSystem.hasFile(silentVideoFilePath):
                Logging.trace("cannot copy file %s", silentVideoFilePath)
                message = ("ERR: cannot find %s" % silentVideoFilePath)
                OperatingSystem.showMessageOnConsole(message)
            else:
                OperatingSystem.copyFile(silentVideoFilePath,
                                         destinationVideoFilePath)
        else:
            configData = cls._configData

            if not videoDestination.subtitlesAreHardcoded:
                videoFilePath = silentVideoFilePath
                effectiveSubtitleFilePath = tempSubtitleFilePath
            else:
                videoFilePath = tempMp4FilePath
                effectiveSubtitleFilePath = ""
                VideoAudioCombiner.insertHardSubtitles( \
                                    silentVideoFilePath,
                                    tempSubtitleFilePath,
                                    videoFilePath,
                                    configData.shiftOffset,
                                    videoDestination.subtitleColor,
                                    videoDestination.subtitleFontSize,
                                    videoDestination.ffmpegPresetName)

            trackDataList = \
               AudioTrackManager \
               .constructSettingsForAudioTracks(configData)

            VideoAudioCombiner.combine(voiceNameList,
                                       trackDataList,
                                       videoFilePath,
                                       destinationVideoFilePath,
                                       effectiveSubtitleFilePath)

            VideoAudioCombiner.tagVideoFile( \
                                    destinationVideoFilePath,
                                    configData.albumName,
                                    configData.artistName,
                                    configData.albumArtFilePath,
                                    configData.title,
                                    videoDestination.mediaType,
                                    configData.songYear)

        ProgressMessage.reportProcessingEnd()

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _processSingleSilentVideoFile(cls,
                                      videoDestination : VideoDestination,
                                      videoFileKind : VideoFileKind,
                                      voiceNameList : StringList,
                                      tempLilypondFilePath : String,
                                      destinationDirectoryPath : String):
        """Generates silent video from lilypond notation pages for
           given <videoDestination> and <videoFileKind>; <voiceNameList>
           gives the list of affected voices, <tempLilypondFilePath>
           the path for the generated lilypond file and
           <destinationDirectoryPath> the destination path for the silent video
           file"""

        Logging.trace(">>: videoDestination = %s,"
                      + " videoFileKind = %s,"
                      + " voiceNameList = %r,"
                      + " tempLilypondFilePath = '%s',"
                      + " destinationDirectoryPath = '%s'",
                      videoDestination, videoFileKind, voiceNameList,
                      tempLilypondFilePath, destinationDirectoryPath)
                                                      
        configData = cls._configData
        destinationSubtitleFileName = (destinationDirectoryPath
                                  + cls._pathSeparator
                                  + (_subtitleFileNameTemplate
                                     % configData.fileNamePrefix))
        
        intermediateFilesAreKept = configData.intermediateFilesAreKept
        intermediateFileDirectoryPath = \
            configData.intermediateFileDirectoryPath
        mmPerInch = 25.4
        factor = mmPerInch / videoDestination.resolution
        videoWidth  = videoDestination.width  * factor
        videoHeight = videoDestination.height * factor
        videoLineWidth = \
            videoWidth - 2 * videoDestination.leftRightMargin

        lilypondFile = LilypondFile(tempLilypondFilePath)
        lilypondFile.setVideoParameters(videoDestination.name,
                                        videoDestination.resolution,
                                        videoDestination.systemSize,
                                        videoDestination.topBottomMargin,
                                        videoWidth, videoHeight,
                                        videoLineWidth)

        lilypondFile.generate(configData.includeFilePath,
                      configData.lilypondVersion, "video",
                      voiceNameList,
                      configData.title,
                      configData.songComposerText,
                      configData.voiceNameToChordsMap,
                      configData.voiceNameToLyricsMap,
                      configData.voiceNameToScoreNameMap,
                      configData.measureToTempoMap,
                      configData.phaseAndVoiceNameToClefMap,
                      configData.phaseAndVoiceNameToStaffListMap)

        frameRate = videoDestination.frameRate
        videoFileExtension = cls._videoFileExtension(frameRate)

        destinationVideoFileName = (destinationDirectoryPath
                             + cls._pathSeparator
                             + (_silentVideoFileNameTemplate
                                % (configData.fileNamePrefix,
                                   videoFileKind.fileNameSuffix,
                                   videoFileExtension)))
        videoGenerator = \
            LilypondPngVideoGenerator(tempLilypondFilePath,
                                      destinationVideoFileName,
                                      destinationSubtitleFileName,
                                      configData.measureToTempoMap,
                                      configData.countInMeasureCount,
                                      frameRate,
                                      videoDestination.scalingFactor,
                                      videoDestination.ffmpegPresetName,
                                      intermediateFileDirectoryPath,
                                      intermediateFilesAreKept)

        videoGenerator.process()
        videoGenerator.cleanup()

        ##OperatingSystem.moveFile(destinationVideoFileName,
        ##                         configData.destinationDirectoryPath)
        ##OperatingSystem.moveFile(destinationSubtitleFileName,
        ##                         configData.destinationDirectoryPath)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def _stringToMidiInstrument(cls,
                                st : String) -> Tuple:
        """Converts <st> to midi instrument bank plus instrument based on
           separator ':' (if any)"""

        Logging.trace(">>: %r", st)

        if ':' not in st:
            midiInstrumentBank, midiInstrument = 0, int(st)
        else:
            midiInstrumentBank, midiInstrument = st.split(":")
            midiInstrumentBank = int(midiInstrumentBank)
            midiInstrument     = int(midiInstrument)

        result = (midiInstrumentBank, midiInstrument)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _stringToMidiPanPosition (cls,
                                  st : String) -> Natural:
        """Returns pan position in range [0, 127] for given <st>"""

        Logging.trace(">>: %r", st)
        
        if st == "C":
            result = 64
        else:
            suffix      = st[-1]
            offset      = int(float(st[0:-1]) * 63)
            Logging.trace("--: panPosition = %r, pan = %d, suffix = %r",
                          st, offset, suffix)
            result = iif(suffix == "L", 63 - offset, 65 + offset)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _videoFileExtension (cls,
                             frameRate : Real) -> String:
        """Returns the video file extension for a given <frameRate>;
           it is 'tar' for a zero frame rate, 'mp4' otherwise"""

        Logging.trace(">>: %s", frameRate)
        result = iif(frameRate == 0.0, "tar", "mp4")
        Logging.trace("<<: %r", result)
        return result
    
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def processExtract (cls):
        """Generates voice extracts as PDF and move them to local
           destination directory."""

        Logging.trace(">>")

        relevantVoiceNameSet = (cls._selectedVoiceNameSet
                                & cls._configData.extractVoiceNameSet)

        for voiceName in relevantVoiceNameSet:
            Logging.trace("--: processing %s", voiceName)
            singleVoiceNameList = [ voiceName ]
            destinationFileNamePrefix = \
                ("%s-%s" % (cls._configData.fileNamePrefix,
                            voiceName))
            cls._makePdf("extract",
                         destinationFileNamePrefix, singleVoiceNameList)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processFinalVideo (cls):
        """Generates final videos from silent video, audio tracks and
           subtitle files."""

        Logging.trace(">>")

        configData = cls._configData
        intermediateFileDirectoryPath = \
            configData.intermediateFileDirectoryPath
        tempSubtitleFilePath = (intermediateFileDirectoryPath
                                + "/tempSubtitle.srt")
        tempMp4FilePath = (intermediateFileDirectoryPath
                           + "/tempVideoWithSubtitles.mp4")

        # --- shift subtitles ---
        subtitleFilePath = "%s/%s" % (configData.destinationDirectoryPath,
                                      (_subtitleFileNameTemplate
                                       % configData.fileNamePrefix))
        VideoAudioCombiner.shiftSubtitleFile(subtitleFilePath,
                                             tempSubtitleFilePath,
                                             configData.shiftOffset)

        for videoFileKindName, videoFileKind \
            in configData.videoFileKindMap.items():
            # only use the actual voices in song
            voiceNameList = [ voiceName
                              for voiceName in videoFileKind.voiceNameList
                              if voiceName in configData.voiceNameList ]

            if len(voiceNameList) == 0:
                Logging.trace("--: no voices found for %s", videoFileKind)
            else:
                videoDestinationName = videoFileKind.destination

                if videoDestinationName not in configData.videoDestinationMap:
                    Logging.traceError("unknown video destination %s for file"
                                       + " kind %s",
                                       videoDestinationName, videoFileKindName)
                else:
                    videoDestination = \
                        configData.videoDestinationMap[videoDestinationName]
                    frameRate = videoDestination.frameRate
                    videoFileExtension = cls._videoFileExtension(frameRate)

                    silentVideoFilePath = \
                        (("%s/" + _silentVideoFileNameTemplate)
                         % (configData.destinationDirectoryPath,
                            configData.fileNamePrefix,
                            videoFileKind.fileNameSuffix,
                            videoFileExtension))
                    destinationDirectoryPath = videoFileKind.directoryPath
                    ValidityChecker.isDirectory(destinationDirectoryPath,
                                                "video destination directory")
                    destinationVideoFilePath = \
                        ("%s/%s%s%s.%s"
                         % (destinationDirectoryPath,
                            configData.destinationFileNamePrefix,
                            configData.fileNamePrefix,
                            videoFileKind.fileNameSuffix,
                            videoFileExtension))

                    cls._processSingleFinalVideoFile(videoDestination,
                                                     videoFileKindName,
                                                     videoFileExtension,
                                                     voiceNameList,
                                                     silentVideoFilePath,
                                                     tempMp4FilePath,
                                                     tempSubtitleFilePath,
                                                     destinationVideoFilePath)

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

        configData = cls._configData
        tempLilypondFilePath = cls._adaptTempFileName("midi", [])
        lilypondFile = LilypondFile(tempLilypondFilePath)
        tempMidiFileNamePrefix = (configData.intermediateFileDirectoryPath
                                  + cls._pathSeparator
                                  + configData.fileNamePrefix + "-temp")
        tempMidiFileName = tempMidiFileNamePrefix + ".mid"

        voiceNameToMidiInstrumentMap, \
        voiceNameToMidiVolumeMap, \
        voiceNameToMidiPanMap = cls._calculateMidiMapsFromConfiguration()

        lilypondFile.setMidiParameters(voiceNameToMidiInstrumentMap,
                                       voiceNameToMidiVolumeMap,
                                       voiceNameToMidiPanMap)
        lilypondFile.generate(configData.includeFilePath,
                              configData.lilypondVersion, "midi",
                              configData.midiVoiceNameList,
                              configData.title,
                              configData.songComposerText,
                              configData.voiceNameToChordsMap,
                              configData.voiceNameToLyricsMap,
                              configData.voiceNameToScoreNameMap,
                              configData.measureToTempoMap,
                              configData.phaseAndVoiceNameToClefMap,
                              configData.phaseAndVoiceNameToStaffListMap)
        cls._processLilypond(tempLilypondFilePath, tempMidiFileNamePrefix)
        cls._postprocessMidiFile(tempMidiFileName)

        OperatingSystem.removeFile(tempLilypondFilePath,
                                   configData.intermediateFilesAreKept)
        OperatingSystem.removeFile(tempMidiFileName,
                                   configData.intermediateFilesAreKept)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processMix (cls):
        """Mix audio tracks."""

        Logging.trace(">>")

        audioTrackManager = \
            AudioTrackManager(cls._configData.tempAudioDirectoryPath)
        audioTrackManager.mix(cls._configData)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processRawAudio (cls):
        """Generates unprocessed audio files from generated midi file."""

        Logging.trace(">>")

        configData = cls._configData
        songName = configData.title
        midiFilePath = (configData.destinationDirectoryPath + "/"
                        + (cls._midiFileNameTemplate
                           % configData.fileNamePrefix))

        relevantVoiceNameSet = (cls._selectedVoiceNameSet
                                & configData.audioVoiceNameSet)
        audioTrackManager = \
             AudioTrackManager(configData.tempAudioDirectoryPath)

        for voiceName in relevantVoiceNameSet:
            audioTrackManager.generateRawAudio(songName, midiFilePath,
                                               voiceName,
                                               configData.shiftOffset)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processRefinedAudio (cls):
        """Generates refined audio files from raw audio file."""

        Logging.trace(">>")

        configData = cls._configData
        songName = configData.title
        audioTrackManager = \
             AudioTrackManager(configData.tempAudioDirectoryPath)
        relevantVoiceNameSet = (cls._selectedVoiceNameSet
                                & configData.audioVoiceNameSet)
        overriddenVoiceNameSet, voiceNameSet = \
            cls._findOverriddenVoiceSets(relevantVoiceNameSet)

        for voiceName in voiceNameSet:
            Logging.trace("--: processing voice %s", voiceName)
            voiceDescriptor = configData.voiceNameToVoiceDataMap[voiceName]
            soundVariant = voiceDescriptor.soundVariant
            reverbLevel  = voiceDescriptor.reverbLevel
            audioTrackManager.generateRefinedAudio(songName, voiceName,
                                                   soundVariant, reverbLevel)

        for voiceName in overriddenVoiceNameSet:
            overrideFile = \
                configData.voiceNameToOverrideFileNameMap[voiceName]
            audioTrackManager.copyOverrideFile(songName, voiceName,
                                               overrideFile,
                                               configData.shiftOffset)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processScore (cls):
        """Generates score as PDF and moves them to local destination
           directory."""

        Logging.trace(">>")

        cls._makePdf("score",
                     cls._configData.fileNamePrefix + "_score",
                     cls._configData.scoreVoiceNameList)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def processSilentVideo (cls):
        """Generates video without audio from lilypond file."""

        Logging.trace(">>")

        configData = cls._configData
        intermediateFilesAreKept = configData.intermediateFilesAreKept
        intermediateFileDirectoryPath = \
            configData.intermediateFileDirectoryPath
        destinationDirectoryPath = configData.destinationDirectoryPath
        tempLilypondFilePath = cls._adaptTempFileName("silentvideo", [])

        for _, videoFileKind in configData.videoFileKindMap.items():
            # only use the actual voices in song
            voiceNameList = [ voiceName
                              for voiceName in videoFileKind.voiceNameList
                              if voiceName in configData.voiceNameList ]

            if len(voiceNameList) == 0:
                Logging.trace("--: no voices found for %s", videoFileKind)
            else:
                message = ("generating silent video for %s"
                           % videoFileKind.name)
                ProgressMessage.reportProcessingStart(message)
                videoDestinationName = videoFileKind.destination

                if videoDestinationName not in configData.videoDestinationMap:
                    Logging.traceError("unknown video destination %s for"
                                       + " file kind %s",
                                       videoDestinationName, videoFileKind.name)
                else:
                    videoDestination = \
                        configData.videoDestinationMap[videoDestinationName]
                    cls._processSingleSilentVideoFile(videoDestination,
                                                      videoFileKind,
                                                      voiceNameList,
                                                      tempLilypondFilePath,
                                                      destinationDirectoryPath)

                ProgressMessage.reportProcessingEnd()

        OperatingSystem.removeFile(tempLilypondFilePath,
                                   configData.intermediateFilesAreKept)

        Logging.trace("<<")

#--------------------
#--------------------

def conditionalExecuteHandlerProc (processingPhase : String,
                                   processingPhaseSet : StringSet,
                                   isPreprocessing : Boolean,
                                   handlerProc : Callable):
    """Checks whether <processingPhase> occurs in <processingPhaseSet>, for
       being part of the group pre- or postprocessing (depending on
       <isPreprocessing>) and executes <handlerProc> when processing
       phase matches"""

    Logging.trace(">>: processingPhase = %r, processingPhaseSet = %r,"
                  + " isPreprocessing = %r",
                  processingPhase, processingPhaseSet, isPreprocessing)

    allowedPhaseSet = set([ "all", processingPhase,
                            iif(isPreprocessing, "preprocess", "postprocess")])

    if len(allowedPhaseSet.intersection(processingPhaseSet)) > 0:
        ProgressMessage.reportProcessingStart("phase '%s'" % processingPhase)
        handlerProc()
        ProgressMessage.reportProcessingEnd()

    Logging.trace("<<")

#--------------------

def initialize ():
    """Initializes LTBVC program."""

    Logging.trace(">>")

    intermediateFilesAreKept, processingPhaseSet, \
    selectedVoiceNameSet, argumentList = _CommandLineOptions.read()
    _CommandLineOptions.checkArguments(argumentList)

    # set logging file path from command line (if available)
    loggingFilePath = argumentList.loggingFilePath

    if loggingFilePath is not None:
        if loggingFilePath.lower() != lowerCasedNullLoggingFileName:
            Logging.setFileName(loggingFilePath, False)
        else:
            Logging.setEnabled(False)

    configData = LTBVC_ConfigurationData()
    _LilypondProcessor._configData = configData
    _LilypondProcessor._selectedVoiceNameSet = selectedVoiceNameSet

    configurationFilePath = argumentList.configurationFilePath
    configurationFile = configData.readFile(configurationFilePath)

    if configurationFile is None:
        Logging.trace("--: cannot process configuration file %r",
                      configurationFilePath)
        isOkay = False
    else:
        isOkay = True

        if loggingFilePath is None:
            # get path from configuration file
            loggingFilePath = configData.get("loggingFilePath")

            if loggingFilePath is None:
                Logging.setEnabled(False)
            else:
                Logging.setFileName(loggingFilePath, True)

        configData.checkAndSetDerivedVariables(selectedVoiceNameSet)

        # override config file setting from command line option
        if intermediateFilesAreKept:
            SETATTR(configData, "intermediateFilesAreKept", True)

        # initialize all the submodules with configuration information
        _LilypondProcessor._lilypondCommand = configData.lilypondCommand
        LilypondPngVideoGenerator.initialize(configData.ffmpegCommand,
                                             configData.lilypondCommand)
        VideoAudioCombiner.initialize(configData.ffmpegCommand,
                                      configData.mp4boxCommand)
        AudioTrackManager.initialize(configData.aacCommandLine,
                                     configData.audioProcessorMap,
                                     configData.ffmpegCommand,
                                     configData.midiToWavRenderingCommandLine,
                                     configData.soundStyleNameToTextMap,
                                     configData.intermediateFilesAreKept,
                                     configData.intermediateFileDirectoryPath)
        MidiTransformer.initialize(configData.voiceNameToVariationFactorMap,
                                   configData.humanizationStyleNameToTextMap,
                                   configData.humanizedVoiceNameSet)

    Logging.trace("<<: isOkay = %r, processingPhaseSet = %r",
                  isOkay, processingPhaseSet)
    return isOkay, processingPhaseSet

#--------------------

def main ():
    """Main program for LTBVC."""

    Logging.initialize()
    Logging.setLevel(Logging_Level.verbose)
    Logging.setTracingWithTime(True, 3)
    Logging.trace(">>")

    isOkay, processingPhaseSet = initialize()

    if isOkay:
        Logging.trace("--: processingPhaseSet = %r", processingPhaseSet)

        actionList = \
            (("extract",      True,  _LilypondProcessor.processExtract),
             ("score",        True,  _LilypondProcessor.processScore),
             ("midi",         True,  _LilypondProcessor.processMidi),
             ("silentvideo",  True,  _LilypondProcessor.processSilentVideo),
             ("rawaudio",     False, _LilypondProcessor.processRawAudio),
             ("refinedaudio", False, _LilypondProcessor.processRefinedAudio),
             ("mix",          False, _LilypondProcessor.processMix),
             ("finalvideo",   False, _LilypondProcessor.processFinalVideo))

        for processingPhase, isPreprocessing, handlerProc in actionList:
            conditionalExecuteHandlerProc(processingPhase, processingPhaseSet,
                                          isPreprocessing, handlerProc)

    Logging.trace("<<")
