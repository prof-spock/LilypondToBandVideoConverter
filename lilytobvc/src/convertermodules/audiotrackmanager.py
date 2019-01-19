# -*- coding: utf-8-unix -*-
# audiotrackmanager -- generates audio tracks from midi file and provides
#                      several transformations on it (e.g. instrument
#                      postprocessing and mixdown
#
# author: Dr. Thomas Tensi, 2006 - 2018

#====================
# IMPORTS
#====================

from numbers import Number
import re
import struct
import wave

from basemodules.configurationfile import ConfigurationFile
from basemodules.operatingsystem import OperatingSystem
from basemodules.python2and3support import isString
from basemodules.simplelogging import Logging
from basemodules.stringutil import splitAndStrip, tokenize
from basemodules.ttbase import adaptToRange, iif, iif3, isInRange, MyRandom
from basemodules.utf8file import UTF8File
from basemodules.validitychecker import ValidityChecker

from .ltbvc_businesstypes import humanReadableVoiceName
from .miditransformer import MidiTransformer
from .mp4tagmanager import MP4TagManager

#====================

_processedAudioFileTemplate = "%s/%s-processed.wav"
_tempAudioFileTemplate = "%s/%s-temp_%s.wav"

# the log level for ffmpeg rendering
_ffmpegLogLevel = "error"

#====================

class _WavFile:
    """This class provides services for WAV files like shifting, mixing of
       several files or normalization and aggregated services like mixdown"""

    _chunkSize = 128  # number of frames to be read from wave file in one step
    maximumSampleValue = 32767

    #--------------------
    # INTERNAL FEATURES
    #--------------------

    @classmethod
    def _makeFraction (cls, value):
        """Returns numerator and log2 of denominator representing value"""

        log2denominator = 10
        denominator = int(pow(2, log2denominator))
        numerator = round(value * denominator)
        return (numerator, log2denominator)

    #--------------------

    @classmethod
    def _mix (cls, sampleList, file, volumeFactor):
        """Mixes audio samples from <file> into <sampleList> using
           <volumeFactor>"""

        Logging.trace(">>: file = %s, factor = %4.3f", file, volumeFactor)

        numerator, log2denominator = cls._makeFraction(volumeFactor)
        fileSampleList  = file.readAllSamples()
        fileSampleCount = len(fileSampleList)

        for i in range(fileSampleCount):
            sampleList[i] += (fileSampleList[i] * numerator >> log2denominator)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self, filePath, mode):
        """Opens wav file given by <filePath> for reading or writing
           depending on <mode>"""

        Logging.trace(">>: file = %s, mode = %s", filePath, mode)

        cls = self.__class__

        file = wave.open(filePath, mode)

        if mode == "w":
            channelCount, frameCount, frameSize  = 0, 0, 0
        else:
            channelCount = file.getnchannels()
            frameCount   = file.getnframes()
            frameSize    = file.getsampwidth() * channelCount

        self._path          = filePath
        self._file          = file
        self._channelCount  = channelCount
        self._frameCount    = frameCount
        self._frameSize     = frameSize
        self._buffer        = bytearray(frameCount * frameSize)
        self._bufferIsEmpty = True

        Logging.trace("<<: %s", self)

    #--------------------

    def __str__ (self):
        """Returns string representation of <self>"""

        st = (("_WavFile(path = %s, channels = %d, frameSize = %d,"
               + " frameCount = %d, isEmpty = %s)")
              % (self._path, self._channelCount, self._frameSize,
                 self._frameCount, self._bufferIsEmpty))
        return st

    #--------------------
    #--------------------

    def close (self):
        """Closes <self>"""

        Logging.trace(">>: %s", self)
        self._file.close()
        Logging.trace("<<")

    #--------------------

    def getParameters (self):
        """Gets the parameters for wav file <self>"""

        Logging.trace(">>: self = %s", self)

        channelCount, sampleSize, frameRate, frameCount, _, _ = \
            self._file.getparams()
        result = (channelCount, sampleSize, frameRate, frameCount)

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def frameCount (self):
        """Returns frame count of audio file"""

        Logging.trace(">>: %s", self)
        result = self._file.getnframes()
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def maximumVolume (cls, sampleList):
        """Returns maximum volume in <sampleList>"""

        Logging.trace(">>")

        maxValue = max(*sampleList)
        minValue = min(*sampleList)
        result = max(abs(maxValue), abs(minValue))

        Logging.trace("<<: %d", result)
        return result
        
    #--------------------

    @classmethod
    def mixdown (cls, sourceFilePathList, volumeFactorList,
                 attenuationLevel, targetFilePath):
        """Mixes WAV audio files given in <sourceFilePathList> to target WAV
           file with <targetFilePath> with volumes given by
           <volumeFactorList> with loudness attenuation given by
           <attenuationLevel> via Python modules only"""

        Logging.trace(">>: sourceFiles = %s, volumeFactors = %s,"
                      + " level = %4.3f, targetFile = %s",
                      sourceFilePathList, volumeFactorList, attenuationLevel,
                      targetFilePath)

        OperatingSystem.showMessageOnConsole("  MIX", False)
        sourceFileList = [cls(name, "r") for name in sourceFilePathList]
        sourceFileCount = len(sourceFileList)
        channelCount, sampleSize, frameRate, _ = \
            sourceFileList[0].getParameters()
        frameCount = max([file.frameCount() for file in sourceFileList])
        resultSampleList = (frameCount * channelCount) * [ 0 ]

        for i in range(sourceFileCount):
            OperatingSystem.showMessageOnConsole(" %d" % (i + 1), False)
            sourceFile   = sourceFileList[i]
            volumeFactor = volumeFactorList[i]
            cls._mix(resultSampleList, sourceFile, volumeFactor)

        maximumVolume = cls.maximumVolume(resultSampleList)
        maxValue = cls.maximumSampleValue
        attenuationFactor = pow(2.0, attenuationLevel / 6.0)
        scalingFactor = (1.0 if maximumVolume < (maxValue // 10)
                         else (maxValue * attenuationFactor) / maximumVolume)
        Logging.trace("--: maxVolume = %d, factor = %4.3f",
                      maximumVolume, scalingFactor)
        OperatingSystem.showMessageOnConsole(" S")
        cls.scale(resultSampleList, scalingFactor)

        for file in sourceFileList:
            file.close()

        targetFile = cls(targetFilePath, "w")
        targetFrameCount = len(resultSampleList) // channelCount
        targetFile.setParameters(channelCount, sampleSize,
                                 frameRate, targetFrameCount)
        targetFile.writeSamples(resultSampleList)
        targetFile.close()

        Logging.trace("<<")

    #--------------------

    def readAllSamples (self):
        """Returns all samples in <wavFile> as an integer list"""

        Logging.trace(">>:%s", self)

        self.readAllSamplesRaw()
        sampleCount = self._channelCount * self._frameCount
        unpackFormat = "<%uh" % sampleCount
        result = struct.unpack(unpackFormat, self._buffer)

        Logging.trace("<<")
        return result

    #--------------------

    def readAllSamplesRaw (self):
        """Returns all samples in <wavFile> as an encoded string"""

        Logging.trace(">>: %s", self)

        if self._bufferIsEmpty:
            self._bufferIsEmpty = False
            self._buffer = self._file.readframes(self._frameCount)

        Logging.trace("<<")
        return self._buffer

    #--------------------

    @classmethod
    def scale (cls, sampleList, factor):
        """Scales <sampleList> inline by <factor>"""

        Logging.trace(">>: factor = %4.3f", factor)

        numerator, log2denominator = cls._makeFraction(factor)
        sampleCount = len(sampleList)

        for sample in sampleList:
            sample = (sample * numerator) >> log2denominator

        Logging.trace("<<")

    #--------------------

    def setParameters (self, channelCount, sampleSize, frameRate, frameCount):
        """Sets the parameters for wav file <self>"""

        Logging.trace(">>: self = %s, channelCount = %d, sampleSize = %d,"
                      + " frameRate = %d, frameCount = %d",
                      self, channelCount, sampleSize, frameRate, frameCount)

        self._file.setparams((channelCount, sampleSize,
                              frameRate, frameCount, "NONE", "not compressed"))
        self._channelCount = channelCount
        self._frameSize    = channelCount * sampleSize
        self._frameCount   = frameCount

        Logging.trace("<<")

    #--------------------

    @classmethod
    def shiftAudio (cls, audioFilePath, shiftedFilePath, shiftOffset):
        """Shifts audio file in <audioFilePath> to shifted audio in
           <shiftedFilePath> with silence prefix of length
           <shiftOffset> using internal python modules only"""

        Logging.trace(">>: infile = '%s', outfile = '%s',"
                      + " shiftOffset = %7.3f",
                      audioFilePath, shiftedFilePath, shiftOffset)

        sourceFile = cls.open(audioFilePath, "r")
        targetFile = cls.open(shiftedFilePath, "w")

        channelCount, sampleSize, frameRate, frameCount = \
            sourceFile.getParameters()
        silenceFrameCount = round(frameRate * shiftOffset)
        targetFile.setParameters(channelCount, sampleSize, frameRate,
                                 frameCount + silenceFrameCount)

        # insert padding with silence
        rawSampleList = (silenceFrameCount * channelCount) * [ 0 ]
        targetFile.writeSamplesRaw(targetFile, rawFrameList)

        # copy samples over
        rawSampleList = sourceFile.readAllSamplesRaw()
        targetFile.writeSamplesRaw(rawSampleList)

        # close files
        sourceFile.close()
        targetFile.close()

        Logging.trace("<<")

    #--------------------

    def writeSamples (self, sampleList):
        """Writes all frames in a integer <sampleList> to <self>"""

        Logging.trace(">>: %s", self)

        cls = self.__class__
        maxValue = cls.maximumSampleValue
        rawSampleList = [(maxValue       if sampleValue > maxValue
                          else -maxValue if sampleValue < -maxValue
                          else sampleValue)
                         for sampleValue in sampleList]
        self.writeSamplesRaw(rawSampleList)

        Logging.trace("<<")

    #--------------------

    def writeSamplesRaw (self, rawSampleList):
        """Writes all frames in a raw <sampleList> to <self>"""

        Logging.trace(">>: %s", self)

        packFormat = "<%uh" % len(rawSampleList)
        sampleString = struct.pack(packFormat, *rawSampleList)
        self._file.writeframesraw(sampleString)

        Logging.trace("<<")

#====================

class AudioTrackManager:
    """This class encapsulates services for audio tracks generated
       from a midi file."""

    _processingChainSeparator = ";"
    _chainSourceIndicatorRegExp = re.compile("([A-Za-z]+)\->")
    _chainTargetIndicatorRegExp = re.compile("\->([A-Za-z]+)")

    _aacCommandLine                = None
    _audioRefinementCommandList    = None
    _intermediateFilesAreKept      = None
    _ffmpegCommand                 = None
    _midiToWavRenderingCommandList = None
    _soundStyleNameToCommandsMap   = None
    _soxCommandLinePrefixList      = None

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _compressAudio (self, audioFilePath, songTitle, targetFilePath):
        """Compresses audio file with <songTitle> in path with
          <audioFilePath> to AAC file at <targetFilePath>"""

        Logging.trace(">>: audioFile = '%s', title = '%s',"
                      + " targetFile = '%s'",
                      audioFilePath, songTitle, targetFilePath)

        cls = self.__class__

        OperatingSystem.showMessageOnConsole("== convert to AAC: "
                                             + songTitle)

        commandLine = iif(cls._aacCommandLine != "", cls._aacCommandLine,
                          ("%s -loglevel %s -aac_tns 0"
                           + " -i ${infile} -y ${outfile}")
                           % (cls._ffmpegCommand, _ffmpegLogLevel))
        variableMap = { "infile"  : audioFilePath,
                        "outfile" : targetFilePath }
        command = cls._replaceVariablesByValues(tokenize(commandLine),
                                                variableMap)

        OperatingSystem.executeCommand(command, True)

        Logging.trace("<<")

    #--------------------

    def _convertMidiToAudio (self, voiceMidiFilePath, targetFilePath):
        """Converts voice data in midi file with <voiceMidiFilePath>
           to raw audio file with <targetFilePath>"""

        Logging.trace(">>: midiFile = '%s', targetFile = '%s'",
                      voiceMidiFilePath, targetFilePath)

        cls = self.__class__

        # processing midi file via given command
        OperatingSystem.showMessageOnConsole("== convertMidiToWav "
                                             + targetFilePath)

        variableMap = { "infile"  : voiceMidiFilePath,
                        "outfile" : targetFilePath }
        command = \
            cls._replaceVariablesByValues(cls._midiToWavRenderingCommandList,
                                          variableMap)
        OperatingSystem.executeCommand(command, True,
                                       stdout=OperatingSystem.nullDevice)

        Logging.trace("<<")

    #--------------------

    def _extractCommandSrcAndTgt (self, voiceName, chainPosition,
                                  partPosition, debugFileCount,
                                  commandTokenList):
        """Returns list of sources and single target from audio refinement
           command token list <commandTokenList>; adapts
           <commandTokenList> accordingly by deleting those tokens;
           <voiceName> gives name of current voice; <chainPosition>
           tells whether this is a single, the first, last or other
           chain; <partPosition> tells whether this is a single, the
           first, last or other part; <debugFileCount> gives the
           number of the next available tee file"""
                
        Logging.trace(">>: voice = %s, chainPosition = %s, partPosition = %s,"
                      + " debugFileCount = %d, commands = %s",
                      voiceName, chainPosition, partPosition, debugFileCount,
                      commandTokenList)

        cls = self.__class__

        sourceFilePath = "%s/%s.wav" % (self._audioDirectoryPath, voiceName)
        targetFilePath = (_processedAudioFileTemplate %
                          (self._audioDirectoryPath, voiceName))

        tempFilePath = (lambda st: (_tempAudioFileTemplate
                                   % (self._audioDirectoryPath,
                                      voiceName, st)))
        teeFilePath = (lambda i: tempFilePath(hex(i).upper()[2:]))
        chainFilePath = (lambda identifier: tempFilePath(identifier))

        # collect sources and targets and delete them from token list
        sourceList = \
            cls._extractMatchingElementsFromList(commandTokenList,
                                        cls._chainSourceIndicatorRegExp)
        targetList = \
            cls._extractMatchingElementsFromList(commandTokenList,
                                        cls._chainTargetIndicatorRegExp)

        # make simple plausibility checks
        if len(targetList) > 1:
            Logging.trace("--: too many targets in chain")

        if len(targetList) > 0:
            target = targetList[0]
        else:
            target = targetFilePath

        if chainPosition in ["SINGLE", "FIRST"]:
            if len(sourceList) > 0:
                Logging.trace("--: bad source in first chain")

            sourceList = [ sourceFilePath ]
        else:
            tempList = sourceList
            sourceList = []

            for source in tempList:
                source = iif(source == "", sourceFilePath,
                             chainFilePath(source))
                sourceList.append(source)

        if chainPosition in ["SINGLE", "LAST"]:
            if len(targetList) > 0:
                Logging.trace("--: bad target in last chain")

            target = targetFilePath
        else:
            target = chainFilePath(target)

        # override source and target assignment for tee files
        if partPosition in ["OTHER", "LAST"]:
            sourceList = [ teeFilePath(debugFileCount) ]

        if partPosition in ["FIRST", "OTHER"]:
            debugFileCount += 1
            target = teeFilePath(debugFileCount)
            
        Logging.trace("<<: commands = %s, sources = %s, target = %s,"
                      " debugFileCount = %d",
                      commandTokenList, sourceList, target, debugFileCount)
        return (sourceList, target, debugFileCount)
            
    #--------------------

    @classmethod
    def _extractMatchingElementsFromList (cls, elementList, elementRegExp):
        """Scans <elementList> for elements matching <elementsRegExp>, 
           removes them from <elementList> and returns them as ordered
           list"""

        Logging.trace(">>: elementList = %s, regExp = %s",
                      elementList, elementRegExp.pattern)

        result = []
        
        for i in reversed(range(len(elementList))):
            element = elementList[i]

            if elementRegExp.match(element):
                normalizedElement = elementRegExp.match(element).group(1)
                result = [ normalizedElement ] + result
                del elementList[i]

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
           <voiceNameList>, the mapping to volumes <voiceNameToVolumeMap>
           with loudness attenuation given by <attenuationLevel>; if
           <parallelTrackPath> is not empty, the parallel track is
           added"""

        Logging.trace(">>: voiceNames = %s, target = '%s'",
                      voiceNameList, targetFilePath)

        cls = self.__class__
        OperatingSystem.showMessageOnConsole("== make mix file: %s"
                                             % songTitle)

        sourceFilePathList = []
        volumeFactorList   = []

        for voiceName in voiceNameList:
            audioFilePath = (_processedAudioFileTemplate
                             % (self._audioDirectoryPath, voiceName))
            volumeFactor = voiceNameToVolumeMap.get(voiceName, 1)
            sourceFilePathList.append(audioFilePath)
            volumeFactorList.append(volumeFactor)

        if parallelTrackFilePath != "":
            volumeFactor = voiceNameToVolumeMap["parallel"]
            sourceFilePathList.append(parallelTrackFilePath)
            volumeFactorList.append(volumeFactor)

        if len(_soxCommandLinePrefixList) == 0:
            _WavFile.mixdown(sourceFilePathList, volumeFactorList,
                             attenuationLevel, targetFilePath)
        else:
            self._mixdownToWavFileViaSox(sourceFilePathList,
                                         volumeFactorList,
                                         attenuationLevel,
                                         targetFilePath)
            
        Logging.trace("<<")

    #--------------------

    def _mixdownToWavFileViaSox (self, sourceFilePathList,
                                 volumeFactorList, attenuationLevel,
                                 targetFilePath):
        """Mixes WAV audio files given in <sourceFilePathList> to target WAV
           file with <targetFilePath> with volumes given by
           <volumeFactorList> with loudness attenuation given by
           <attenuationLevel> using external sox command"""

        Logging.trace(">>: sourceFiles = %s, volumeFactors = %s,"
                      + " level = %4.3f, targetFile = %s",
                      sourceFilePathList, volumeFactorList, attenuationLevel,
                      targetFilePath)

        command = (cls._soxCommandLinePrefixList
                   + [ "--combine", "mix" ])
        
        for i in range(elementCount):
            volumeFactor = volumeFactorList[i]
            filePath     = sourceFilePathList[i]
            command += [ "-v", str(volumeFactor), filePath ]
        
        command += [ targetFilePath, "norm", str(attenuationLevel) ]
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
    def _replaceVariablesByValues (cls, stringList, variableMap):
        """Replaces all occurrences of variables in <stringList> by values
           given by <variableMap>"""

        Logging.trace(">>: list = %s, map = %s", stringList, variableMap)

        result = []
        variableList = variableMap.keys()
        variableRegexp = re.compile(r"\$\{([a-z]+)\}")

        for st in stringList:
            match = variableRegexp.match(st)

            if match is None:
                result.append(st)
            else:
                variable = match.group(1)
                replacement = variableMap.get(variable, st)

                if isString(replacement) or isinstance(replacement, Number):
                    result.append(replacement)
                else:
                    result.extend(replacement)

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

        if len(_soxCommandLinePrefixList) == 0:
            _WavFile.shiftAudio(audioFilePath, shiftedFilePath, shiftOffset)
        else:
            cls._shiftAudioFileViaSox(audioFilePath, shiftedFilePath,
                                      shiftOffset)
            
        Logging.trace("<<")

    #--------------------

    @classmethod
    def _shiftAudioFileViaSox (cls, audioFilePath, shiftedFilePath,
                               shiftOffset):
        """Shifts audio file in <audioFilePath> to shifted audio in
           <shiftedFilePath> with silence prefix of length
           <shiftOffset> using external sox command"""

        Logging.trace(">>: infile = '%s', outfile = '%s',"
                      + " shiftOffset = %7.3f",
                      audioFilePath, shiftedFilePath, shiftOffset)

        command = (cls._soxCommandLinePrefixList
                   + [ audioFilePath, shiftedFilePath,
                       "pad", ("%7.3f" % shiftOffset) ])
        OperatingSystem.executeCommand(command, True,
                                       stdout=OperatingSystem.nullDevice)

        Logging.trace("<<")

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
                    aacCommandLine, audioRefinementCommandLine,
                    ffmpegCommand, midiToWavCommandLine,
                    soxCommandLinePrefix, soundStyleNameToCommandsMap,
                    intermediateFilesAreKept):
        """Sets some global processing data like e.g. the command
           paths."""

        Logging.trace(">>: aac = '%s', audioRefinement = '%s',"
                      + " ffmpeg = '%s', midiToWavCommand = '%s',"
                      + " sox = '%s', soundStyleNameToCommandsMap = %s,"
                      + " debugging = %s",
                      aacCommandLine, audioRefinementCommandLine,
                      ffmpegCommand, midiToWavCommandLine,
                      soxCommandLinePrefix, soundStyleNameToCommandsMap,
                      intermediateFilesAreKept)

        cls._aacCommandLine                = aacCommandLine
        cls._audioRefinementCommandList    = \
            tokenize(audioRefinementCommandLine)
        cls._intermediateFilesAreKept      = intermediateFilesAreKept
        cls._ffmpegCommand                 = ffmpegCommand
        cls._midiToWavRenderingCommandList = tokenize(midiToWavCommandLine)
        cls._soundStyleNameToCommandsMap   = soundStyleNameToCommandsMap
        cls._soxCommandLinePrefixList      = tokenize(soxCommandLinePrefix)

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
        cls._shiftAudioFile(filePath, targetFilePath, shiftOffset)

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
            OperatingSystem.removeFile(audioFilePath,
                                       cls._intermediateFilesAreKept)

        OperatingSystem.removeFile(tempMidiFilePath,
                                   cls._intermediateFilesAreKept)

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

        # prepare list of audio processing commands
        reverbLevel = adaptToRange(int(reverbLevel * 100.0), 0, 100)
        reverbCommands = iif(reverbLevel > 0, " reverb %d" % reverbLevel, "")

        if isCopyVariant:
            audioProcessingCommands = ""
        elif soundStyleName in cls._soundStyleNameToCommandsMap:
            audioProcessingCommands = \
                cls._soundStyleNameToCommandsMap[soundStyleName]
        else:
            audioProcessingCommands = ""
            message = ("--: unknown variant %s replaced by copy default"
                       % soundVariant)
            Logging.trace(message)
            OperatingSystem.showMessageOnConsole(message)

        audioProcessingCommands += reverbCommands
        self._processAudioRefinement(voiceName, audioProcessingCommands)

        Logging.trace("<<")
        
    #--------------------

    def _processAudioRefinement (self, voiceName, audioProcessingCommands):
        """Handles audio processing given by <audioProcessingCommands>"""

        Logging.trace(">>: voice = %s, commands = %s",
                      voiceName, audioProcessingCommands)
        
        cls = self.__class__
        separator = cls._processingChainSeparator
        chainCommandList = splitAndStrip(audioProcessingCommands, separator)
        chainCommandCount = len(chainCommandList)
        debugFileCount = 0
        commandList = cls._audioRefinementCommandList

        for chainIndex, chainProcessingCommands in enumerate(chainCommandList):
            Logging.trace("--: chain[%d] = %s",
                          chainIndex, chainProcessingCommands)
            chainPosition = iif3(chainCommandCount == 1, "SINGLE",
                                 chainIndex == 0, "FIRST",
                                 chainIndex == chainCommandCount - 1, "LAST",
                                 "OTHER")
            chainPartCommandList = splitAndStrip(chainProcessingCommands,
                                                 "tee ")
            partCount = len(chainPartCommandList)

            for partIndex, partProcessingCommands \
                in enumerate(chainPartCommandList):

                partPosition = iif3(partCount == 1, "SINGLE",
                                    partIndex == 0, "FIRST",
                                    partIndex == partCount - 1, "LAST",
                                    "OTHER")
                partCommandTokenList = tokenize(partProcessingCommands)
                sourceList, currentTarget, debugFileCount = \
                    self._extractCommandSrcAndTgt(voiceName, chainPosition,
                                                  partPosition,
                                                  debugFileCount,
                                                  partCommandTokenList)

                if partCommandTokenList[0] != "mix":
                    currentSource = sourceList[0]
                else:
                    numberList = partCommandTokenList[1:]

                    if len(numberList) < len(sourceList):
                        Logging.trace("--: bad argument pairing for mix")
                    else:
                        partCommandTokenList = []
                        currentSource = [ "-m" ]

                        for i in range(len(sourceList)):
                            volume = numberList[i]
                            valueName = "value %d in mix" % (i+1)
                            ValidityChecker.isNumberString(volume,
                                                           valueName, True)
                            currentSource += ["-v", volume, sourceList[i]]

                variableMap = { "infile"   : currentSource,
                                "outfile"  : currentTarget,
                                "commands" : partCommandTokenList }
                command = cls._replaceVariablesByValues(commandList,
                                                        variableMap)
                OperatingSystem.executeCommand(command, True)

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
