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

from basemodules.operatingsystem import OperatingSystem
from basemodules.simplelogging import Logging
from basemodules.stringutil import splitAndStrip, tokenize
from basemodules.ttbase import adaptToRange, iif, iif2, iif3
from basemodules.typesupport import isString
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
       several files or amplification and aggregated services like mixdown"""

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

        Logging.trace(">>: file = %r, factor = %4.3f", file, volumeFactor)

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

        Logging.trace(">>: file = %r, mode = %r", filePath, mode)

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

        Logging.trace("<<: %r", self)

    #--------------------

    def __repr__ (self):
        """Returns string representation of <self>"""

        st = (("_WavFile(path = %r, channels = %d, frameSize = %d,"
               + " frameCount = %d, isEmpty = %s)")
              % (self._path, self._channelCount, self._frameSize,
                 self._frameCount, self._bufferIsEmpty))
        return st

    #--------------------
    #--------------------

    def close (self):
        """Closes <self>"""

        Logging.trace(">>: %r", self)
        self._file.close()
        Logging.trace("<<")

    #--------------------

    def frameCount (self):
        """Returns frame count of audio file"""

        Logging.trace(">>: %r", self)
        result = self._file.getnframes()
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def getParameters (self):
        """Gets the parameters for wav file <self>"""

        Logging.trace(">>: %r", self)

        channelCount, sampleSize, frameRate, frameCount, _, _ = \
            self._file.getparams()
        result = (channelCount, sampleSize, frameRate, frameCount)

        Logging.trace("<<: %r", result)
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
                 amplificationLevel, targetFilePath):
        """Mixes WAV audio files given in <sourceFilePathList> to target WAV
           file with <targetFilePath> with volumes given by
           <volumeFactorList> with loudness amplification given by
           <amplificationLevel> via Python modules only"""

        Logging.trace(">>: sourceFiles = %r, volumeFactors = %r,"
                      + " level = %4.3f, targetFile = %r",
                      sourceFilePathList, volumeFactorList,
                      amplificationLevel, targetFilePath)

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
        amplificationFactor = pow(2.0, amplificationLevel / 6.0206)
        scalingFactor = (1.0 if maximumVolume < (maxValue // 10)
                         else (maxValue * amplificationFactor) / maximumVolume)
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

    @classmethod
    def open (cls, filePath, mode):
        """Opens wav file on path <filePath> with read/write mode specified by
           <mode>"""

        return cls(filePath, mode)

    #--------------------

    def readAllSamples (self):
        """Returns all samples in <wavFile> as an integer list"""

        Logging.trace(">>:%r", self)

        self.readAllSamplesRaw()
        sampleCount = self._channelCount * self._frameCount
        unpackFormat = "<%uh" % sampleCount
        result = struct.unpack(unpackFormat, self._buffer)

        Logging.trace("<<")
        return result

    #--------------------

    def readAllSamplesRaw (self):
        """Returns all samples in <wavFile> as an encoded string"""

        Logging.trace(">>: %r", self)

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

        for sample in sampleList:
            sample = (sample * numerator) >> log2denominator

        Logging.trace("<<")

    #--------------------

    def setParameters (self, channelCount, sampleSize, frameRate, frameCount):
        """Sets the parameters for wav file <self>"""

        Logging.trace(">>: self = %r, channelCount = %d, sampleSize = %d,"
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

        Logging.trace(">>: infile = %r, outfile = %r,"
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
        targetFile.writeSamplesRaw(rawSampleList)

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

        Logging.trace(">>: %r", self)

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

        Logging.trace(">>: %r", self)

        packFormat = "<%uh" % len(rawSampleList)
        sampleString = struct.pack(packFormat, *rawSampleList)
        self._file.writeframesraw(sampleString)

        Logging.trace("<<")

#====================

class AudioTrackManager:
    """This class encapsulates services for audio tracks generated
       from a midi file."""

    _aacCommandLine                = None
    _audioProcessorIsSox           = None
    _audioProcessorMap             = {}
    _intermediateFilesAreKept      = None
    _ffmpegCommand                 = None
    _midiToWavRenderingCommandList = None
    _soundStyleNameToEffectsMap    = {}

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _compressAudio (self, audioFilePath, songTitle, targetFilePath):
        """Compresses audio file with <songTitle> in path with
          <audioFilePath> to AAC file at <targetFilePath>"""

        Logging.trace(">>: audioFile = %r, title = %r,"
                      + " targetFile = %r",
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

        Logging.trace(">>: midiFile = %r, targetFile = %r",
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

    def _extractEffectListSrcAndTgt (self, voiceName, chainPosition,
                                     partPosition, debugFileCount,
                                     effectTokenList):
        """Returns list of sources and single target from audio refinement
           effect chain <effectTokenList>; adapts <effectTokenList>
           accordingly by deleting those tokens; <voiceName> gives
           name of current voice; <chainPosition> tells whether this
           is a single, the first, last or other chain; <partPosition>
           tells whether this is a single, the first, last or other
           part; <debugFileCount> gives the index of the next
           available tee file"""

        Logging.trace(">>: voice = %s, chainPosition = %r, partPosition = %r,"
                      + " debugFileCount = %d, effects = %r",
                      voiceName, chainPosition, partPosition, debugFileCount,
                      effectTokenList)

        cls = self.__class__

        sourceFilePath = "%s/%s.wav" % (self._audioDirectoryPath, voiceName)
        targetFilePath = (_processedAudioFileTemplate %
                          (self._audioDirectoryPath, voiceName))

        tempFilePath = (lambda st: (_tempAudioFileTemplate
                                    % (self._audioDirectoryPath,
                                       voiceName, st)))
        teeFilePath = (lambda i: tempFilePath(hex(i).upper()[2:]))
        chainFilePath = tempFilePath

        # collect sources and targets and delete them from token list
        redirector = re.escape(cls._audioProcessorMap["redirector"])
        indicatorRegExp = re.compile(redirector + r"([A-Za-z]+)")
        targetList = cls._extractMatchingElementsFromList(effectTokenList,
                                                          indicatorRegExp)
        indicatorRegExp = re.compile(r"([A-Za-z]*)" + redirector)
        sourceList = cls._extractMatchingElementsFromList(effectTokenList,
                                                          indicatorRegExp)

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

        Logging.trace("--: sourceList = %r, target = %r",
                      sourceList, target)

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

        Logging.trace("<<: effects = %r, sources = %r, target = %r,"
                      " debugFileCount = %d",
                      effectTokenList, sourceList, target, debugFileCount)
        return (sourceList, target, debugFileCount)

    #--------------------

    @classmethod
    def _extractMatchingElementsFromList (cls, elementList, elementRegExp):
        """Scans <elementList> for elements matching <elementsRegExp>,
           removes them from <elementList> and returns them as ordered
           list"""

        Logging.trace(">>: elementList = %r, regExp = %s",
                      elementList, elementRegExp.pattern)

        result = []

        for i in reversed(range(len(elementList))):
            element = elementList[i]

            if elementRegExp.match(element):
                amplifiedElement = elementRegExp.match(element).group(1)
                result = [ amplifiedElement ] + result
                del elementList[i]

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def _makeFilteredMidiFile (self, voiceName, midiFilePath,
                               voiceMidiFilePath):

        """Filters tracks in midi file named <midiFilePath> belonging
           to voice with <voiceName> and writes them to
           <voiceMidiFilePath>"""

        Logging.trace(">>: voice = %s, midiFile = %r, targetFile = %r",
                      voiceName, midiFilePath, voiceMidiFilePath)

        cls = self.__class__
        midiTransformer = MidiTransformer(midiFilePath,
                                          cls._intermediateFilesAreKept)
        midiTransformer.filterByTrackNamePrefix(voiceName)
        midiTransformer.removeVolumeChanges()
        midiTransformer.save(voiceMidiFilePath)

        Logging.trace("<<")

    #--------------------

    def _mixdownToWavFile (self, sourceFilePathList, volumeFactorList,
                           masteringEffectList, amplificationLevel,
                           targetFilePath):
        """Mixes WAV audio files given in <sourceFilePathList> to target WAV
           file with <targetFilePath> with volumes given by
           <volumeFactorList> with loudness amplification given by
           <amplificationLevel> either externally or with slow internal
           algorithm; <masteringEffectList> gives the refinement
           effects for this track (if any) to be applied after
           mixdown"""

        Logging.trace(">>: sourceFiles = %r, volumeFactors = %r,"
                      + " masteringEffects = %r, amplification = %4.3f,"
                      + " targetFile = %r",
                      sourceFilePathList, volumeFactorList,
                      masteringEffectList, amplificationLevel,
                      targetFilePath)

        cls = self.__class__

        # convert volume factors from decibels to float values
        rawVolumeFactorList = [10 ** (volumeFactorInDecibels / 20)
                               for volumeFactorInDecibels in volumeFactorList]

        if "mixingCommandLine" in cls._audioProcessorMap:
            self._mixdownToWavFileExternally(sourceFilePathList,
                                             rawVolumeFactorList,
                                             masteringEffectList,
                                             amplificationLevel,
                                             targetFilePath)
        else:
            if masteringEffectList > "":
                Logging.trace("--: WARNING - no mastering available"
                              + " when using internal mixdown,"
                              + " effects %r discarded",
                              masteringEffectList)

            _WavFile.mixdown(sourceFilePathList, rawVolumeFactorList,
                             amplificationLevel, targetFilePath)

        Logging.trace("<<")

    #--------------------

    def _mixdownToWavFileExternally (self, sourceFilePathList,
                                     volumeFactorList, masteringEffectList,
                                     amplificationLevel, targetFilePath):
        """Mixes WAV audio files given in <sourceFilePathList> to target WAV
           file with <targetFilePath> with volumes given by
           <volumeFactorList> with loudness amplification given by
           <amplificationLevel> using external command;
           <masteringEffectList> gives the refinement effects for this
           track (if any) to be applied after mixdown"""

        Logging.trace(">>: sourceFiles = %r, volumeFactors = %r,"
                      + " masteringEffects = %r, level = %4.3f,"
                      + " targetFile = %r",
                      sourceFilePathList, volumeFactorList,
                      masteringEffectList, amplificationLevel,
                      targetFilePath)

        cls = self.__class__

        # some shorthands
        audioProcMap     = cls._audioProcessorMap
        replaceVariables = cls._replaceVariablesByValues

        # check whether mastering is done after mixdown
        masteringPassIsRequired = (amplificationLevel != 0
                                   or masteringEffectList > "")
        intermediateFilePath = self._audioDirectoryPath + "/result-mix.wav"
        intermediateFilePath = iif(masteringPassIsRequired,
                                   intermediateFilePath, targetFilePath)

        Logging.trace("--: masteringPass = %r, intermediateFile = %r",
                      masteringPassIsRequired, intermediateFilePath)

        # do the mixdown of the audio sources
        commandRegexp = re.compile(r"([^\[]*)\[([^\]]+)\](.*)")
        mixingCommandLine = audioProcMap["mixingCommandLine"]
        match = commandRegexp.search(mixingCommandLine)

        if match is None:
            Logging.trace("--: bad command line format for mix - %r",
                          mixingCommandLine)
        else:
            commandPrefix        = tokenize(match.group(1))
            commandRepeatingPart = tokenize(match.group(2))
            commandSuffix        = tokenize(match.group(3))

            elementCount = len(sourceFilePathList)
            command = []

            for i in range(elementCount):
                volumeFactor = volumeFactorList[i]
                filePath     = sourceFilePathList[i]
                variableMap  = { "factor" : volumeFactor,
                                 "infile" : filePath }
                part = replaceVariables(commandRepeatingPart, variableMap)
                command.extend(part)

            Logging.trace("--: repeating part = %r", command)

            commandList = commandPrefix + command + commandSuffix
            variableMap = { "outfile" : intermediateFilePath }
            command = replaceVariables(commandList, variableMap)
            OperatingSystem.executeCommand(command, True,
                                           stdout=OperatingSystem.nullDevice)

        if masteringPassIsRequired:
            # do mastering and amplification
            amplificationEffect = audioProcMap["amplificationEffect"]
            amplificationEffectTokenList = tokenize(amplificationEffect)
            variableMap  = { "amplificationLevel" : amplificationLevel }
            nmEffectPartList = replaceVariables(amplificationEffectTokenList,
                                                variableMap)
            effectList = (tokenize(masteringEffectList)
                          + nmEffectPartList)

            refinementCommandLine = audioProcMap["refinementCommandLine"]
            refinementCommandList = tokenize(refinementCommandLine)
            variableMap = { "infile"  : intermediateFilePath,
                            "outfile" : targetFilePath,
                            "effects" : effectList }
            command = replaceVariables(refinementCommandList, variableMap)
            OperatingSystem.executeCommand(command, True)
            OperatingSystem.removeFile(intermediateFilePath,
                                       cls._intermediateFilesAreKept)

        Logging.trace("<<")

    #--------------------

    def _mixdownVoicesToWavFile (self, voiceNameList,
                                 voiceNameToAudioLevelMap,
                                 parallelTrackFilePath,
                                 masteringEffectList, amplificationLevel,
                                 targetFilePath):
        """Constructs and executes a command for audio mixdown to target file
           with <targetFilePath> from given <voiceNameList>, the
           mapping to volumes <voiceNameToAudioLevelMap> with loudness
           amplification given by <amplificationLevel>;
           <masteringEffectList> gives the refinement effects for
           this track (if any) to be applied after mixdown; if
           <parallelTrackPath> is not empty, the parallel track is
           added"""

        Logging.trace(">>: voiceNames = %r, audioLevels = %r"
                      + " parallelTrack = %r, masteringEffects = %r"
                      + " amplification = %5.3f, target = %r",
                      voiceNameList, voiceNameToAudioLevelMap,
                      parallelTrackFilePath, masteringEffectList,
                      amplificationLevel, targetFilePath)

        sourceFilePathList = []
        volumeFactorList   = []

        for voiceName in voiceNameList:
            audioFilePath = (_processedAudioFileTemplate
                             % (self._audioDirectoryPath, voiceName))
            volumeFactor = voiceNameToAudioLevelMap.get(voiceName, 1)
            sourceFilePathList.append(audioFilePath)
            volumeFactorList.append(volumeFactor)

        if parallelTrackFilePath != "":
            volumeFactor = voiceNameToAudioLevelMap["parallel"]
            sourceFilePathList.append(parallelTrackFilePath)
            volumeFactorList.append(volumeFactor)

        self._mixdownToWavFile(sourceFilePathList, volumeFactorList,
                               masteringEffectList, amplificationLevel,
                               targetFilePath)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def _powerset (cls, currentList):
        """Calculates the power set of elements in <currentList>"""

        Logging.trace(">>: %r", currentList)

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

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _replaceVariablesByValues (cls, stringList, variableMap):
        """Replaces all occurrences of variables in <stringList> by values
           given by <variableMap>"""

        Logging.trace(">>: list = %r, map = %r", stringList, variableMap)

        result = []
        variableRegexp = re.compile(r"\$\{([a-zA-Z]+)\}")

        for st in stringList:
            st = str(st)
            match = variableRegexp.match(st)

            if match is None:
                result.append(st)
            else:
                variable = match.group(1)
                replacement = variableMap.get(variable, st)

                if isString(replacement) or isinstance(replacement, Number):
                    result.append(str(replacement))
                else:
                    result.extend(replacement)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _shiftAudioFile (cls, audioFilePath, shiftedFilePath, shiftOffset):
        """Shifts audio file in <audioFilePath> to shifted audio in
           <shiftedFilePath> with silence prefix of length
           <shiftOffset>"""

        Logging.trace(">>: infile = %r, outfile = %r,"
                      + " shiftOffset = %7.3f",
                      audioFilePath, shiftedFilePath, shiftOffset)

        OperatingSystem.showMessageOnConsole("== shifting %r by %7.3fs"
                                             % (shiftedFilePath, shiftOffset))

        if "paddingCommandLine" not in cls._audioProcessorMap:
            _WavFile.shiftAudio(audioFilePath, shiftedFilePath, shiftOffset)
        else:
            commandLine = cls._audioProcessorMap["paddingCommandLine"]
            cls._shiftAudioFileExternally(commandLine,
                                          audioFilePath, shiftedFilePath,
                                          shiftOffset)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _shiftAudioFileExternally (cls, commandLine, audioFilePath,
                                   shiftedFilePath, shiftOffset):
        """Shifts audio file in <audioFilePath> to shifted audio in
           <shiftedFilePath> with silence prefix of length
           <shiftOffset> using external command with <commandLine>"""

        Logging.trace(">>: commandLine = %r,"
                      + " infile = %r, outfile = %r,"
                      + " shiftOffset = %7.3f",
                      commandLine, audioFilePath,
                      shiftedFilePath, shiftOffset)

        variableMap = { "infile"   : audioFilePath,
                        "outfile"  : shiftedFilePath,
                        "duration" : "%7.3f" % shiftOffset }
        command = cls._replaceVariablesByValues(tokenize(commandLine),
                                                variableMap)
        OperatingSystem.executeCommand(command, True,
                                       stdout=OperatingSystem.nullDevice)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _tagAudio (cls, audioFilePath, configData, songTitle, albumName):
        """Tags M4A audio file with <songTitle> at <audioFilePath>
           with tags specified by <configData>, <songTitle> and
           <albumName>"""

        Logging.trace(">>: audioFile = %r, configData = %r,"
                      + " title = %r, album = %r",
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
                    aacCommandLine, audioProcessorMap,
                    ffmpegCommand, midiToWavCommandLine,
                    soundStyleNameToEffectsMap, intermediateFilesAreKept):
        """Sets some global processing data like e.g. the command
           paths."""

        Logging.trace(">>: aac = %r, audioProcessor = %r,"
                      + " ffmpeg = %r, midiToWavCommand = %r,"
                      + " soundStyleNameToEffectsMap = %r,"
                      + " debugging = %r",
                      aacCommandLine, audioProcessorMap,
                      ffmpegCommand, midiToWavCommandLine,
                      soundStyleNameToEffectsMap,
                      intermediateFilesAreKept)

        cls._aacCommandLine                = aacCommandLine
        cls._audioProcessorMap             = audioProcessorMap
        cls._intermediateFilesAreKept      = intermediateFilesAreKept
        cls._ffmpegCommand                 = ffmpegCommand
        cls._midiToWavRenderingCommandList = tokenize(midiToWavCommandLine)
        cls._soundStyleNameToEffectsMap    = soundStyleNameToEffectsMap

        # check whether sox is used as audio processor
        commandList = tokenize(cls._audioProcessorMap["refinementCommandLine"])
        command = commandList[0].lower()
        cls._audioProcessorIsSox = (command.endswith("sox")
                                    or command.endswith("sox.exe"))

        Logging.trace("<<")

    #--------------------

    def __init__ (self, audioDirectoryPath):
        """Initializes generator with target directory of all audio
           files to be stored in <audioDirectoryPath>"""

        Logging.trace(">>: audioDirectoryPath = %r", audioDirectoryPath)

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

        Logging.trace("--: groupToVoiceSetMap = %r, trackList = %r",
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
                        audioTrack.languageCode,
                        audioTrack.voiceNameToAudioLevelMap,
                        audioTrack.masteringEffectList,
                        audioTrack.amplificationLevel)
            Logging.trace("--: appending %r for track name %r",
                          newEntry, audioTrack.name)
            result.append(newEntry)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def copyOverrideFile (self, filePath, voiceName, shiftOffset):
        """Sets refined file from <filePath> for voice with
           <voiceName> and applies <shiftOffset>"""

        Logging.trace(">>: file = %r, voice = %r, offset = %7.3f",
                      filePath, voiceName, shiftOffset)

        cls = self.__class__
        message = "== overriding %r from file" % voiceName
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

        Logging.trace(">>: voice = %s, midiFile = %r, shiftOffset = %7.3f",
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
        if isCopyVariant:
            audioProcessingEffects = ""
        elif soundStyleName in cls._soundStyleNameToEffectsMap:
            audioProcessingEffects = \
                cls._soundStyleNameToEffectsMap[soundStyleName]
        else:
            audioProcessingEffects = ""
            message = ("unknown variant %s replaced by copy default"
                       % soundVariant)
            Logging.trace("--: " + message)
            OperatingSystem.showMessageOnConsole(message)
            isCopyVariant = True

        if not isCopyVariant:
            # add reverb if applicable
            reverbLevel = adaptToRange(int(reverbLevel * 100.0), 0, 100)
            reverbEffect = iif2(reverbLevel == 0, "",
                                not cls._audioProcessorIsSox, "",
                                " reverb %d" % reverbLevel)

            if reverbLevel > 0 and not cls._audioProcessorIsSox:
                message = "reverberation skipped, please use explicit reverb"
                OperatingSystem.showMessageOnConsole(message)

            audioProcessingEffects += reverbEffect

        self._processAudioRefinement(voiceName, audioProcessingEffects)

        Logging.trace("<<")

    #--------------------

    def _processAudioRefinement (self, voiceName, audioProcessingEffects):
        """Handles audio processing given by <audioProcessingEffects>"""

        Logging.trace(">>: voice = %s, effects = %r",
                      voiceName, audioProcessingEffects)

        cls = self.__class__

        debugFileCount = 0
        separator = cls._audioProcessorMap["chainSeparator"]
        chainCommandList = splitAndStrip(audioProcessingEffects, separator)
        chainCommandCount = len(chainCommandList)
        commandList = tokenize(cls._audioProcessorMap["refinementCommandLine"])

        for chainIndex, chainProcessingEffects in enumerate(chainCommandList):
            Logging.trace("--: chain[%d] = %r",
                          chainIndex, chainProcessingEffects)
            chainPosition = iif3(chainCommandCount == 1, "SINGLE",
                                 chainIndex == 0, "FIRST",
                                 chainIndex == chainCommandCount - 1, "LAST",
                                 "OTHER")
            chainPartCommandList = splitAndStrip(chainProcessingEffects,
                                                 "tee ")
            partCount = len(chainPartCommandList)

            for partIndex, partProcessingEffects \
                in enumerate(chainPartCommandList):

                partPosition = iif3(partCount == 1, "SINGLE",
                                    partIndex == 0, "FIRST",
                                    partIndex == partCount - 1, "LAST",
                                    "OTHER")
                partCommandTokenList = tokenize(partProcessingEffects)
                sourceList, currentTarget, debugFileCount = \
                    self._extractEffectListSrcAndTgt(voiceName, chainPosition,
                                                     partPosition,
                                                     debugFileCount,
                                                     partCommandTokenList)

                if (len(partCommandTokenList) == 0
                    or partCommandTokenList[0] != "mix"):
                    currentSource = sourceList[0]
                    variableMap = { "infile"   : currentSource,
                                    "outfile"  : currentTarget,
                                    "effects"  : partCommandTokenList }
                    command = cls._replaceVariablesByValues(commandList,
                                                            variableMap)
                    OperatingSystem.executeCommand(command, True)
                else:
                    volumeList = partCommandTokenList[1:]

                    if len(volumeList) < len(sourceList):
                        Logging.trace("--: bad argument pairing for mix")
                    else:
                        for i in range(len(sourceList)):
                            volume = volumeList[i]
                            valueName = "value %d in mix" % (i+1)
                            ValidityChecker.isNumberString(volume,
                                                           valueName, True)
                            volumeList[i] = float(volume)

                        self._mixdownToWavFile(sourceList, volumeList,
                                               "", 0.0, currentTarget)

        Logging.trace("<<")

    #--------------------

    def mixdown (self, configData):
        """Combines the processed audio files for all voices in
           <configData.voiceNameList> into several combination files and
           converts them to aac format; <configData> defines the voice
           volumes, the relative amplification level, the optional
           voices as well as the tags and suffices for the final
           files"""

        Logging.trace(">>: configData = %r", configData)

        cls = self.__class__

        voiceProcessingList = \
            cls.constructSettingsForAudioTracks(configData)

        for v in voiceProcessingList:
            currentVoiceNameList, albumName, songTitle, \
              targetFilePath, _, languageCode, voiceNameToAudioLevelMap, \
              masteringEffectList, amplificationLevel = v
            waveIntermediateFilePath = ("%s/result_%s.wav"
                                        % (self._audioDirectoryPath, languageCode))
            OperatingSystem.showMessageOnConsole("== make mix file: %s"
                                                 % songTitle)

            if configData.parallelTrackFilePath != "":
                parallelTrackVolume = configData.parallelTrackVolume
                voiceNameToAudioLevelMap["parallel"] = parallelTrackVolume

            self._mixdownVoicesToWavFile(currentVoiceNameList,
                                         voiceNameToAudioLevelMap,
                                         configData.parallelTrackFilePath,
                                         masteringEffectList,
                                         amplificationLevel,
                                         waveIntermediateFilePath)
            self._compressAudio(waveIntermediateFilePath, songTitle,
                                targetFilePath)
            cls._tagAudio(targetFilePath, configData, songTitle, albumName)

            #OperatingSystem.removeFile(waveIntermediateFilePath,
            #                           cls._intermediateFilesAreKept)

        Logging.trace("<<")
