# audiotrackmanager -- generates audio tracks from midi file and provides
#                      several transformations on it (e.g. instrument
#                      postprocessing and mixing)
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
from basemodules.simpletypes import Boolean, Integer, IntegerList, List, \
                                    Natural, Object, Real, RealList, \
                                    String, StringList, StringMap, Tuple, \
                                    TupleList
from basemodules.stringutil import splitAndStrip, tokenize
from basemodules.ttbase import adaptToRange, iif, iif2, iif3
from basemodules.typesupport import isString
from basemodules.validitychecker import ValidityChecker

from .ltbvc_businesstypes import humanReadableVoiceName
from .ltbvc_configurationdatahandler import LTBVC_ConfigurationData
from .miditransformer import MidiTransformer
from .mp4tagmanager import MP4TagManager

#====================

_pannedAudioFileNameSuffix = "-panned"
_processedAudioFileNameSuffix = "-processed"
_processedAudioFileTemplate = ("%s/%s"
                               + _processedAudioFileNameSuffix
                               + ".wav")
_tempAudioFileTemplate = "%s/%s-temp_%s.wav"

# the log level for ffmpeg rendering
_ffmpegLogLevel = "error"

#====================
# PRIVATE ROUTINES
#====================

def _decibelsToReal (v : Real) -> Real:
    """Returns real equivalent of voltage decibel value <v>"""

    Logging.trace(">>: %r", v)
    result = 10 ** (v / 20)
    Logging.trace("<<: %r", result)
    return result

#====================

class _WavFile:
    """This class provides services for WAV files like shifting, mixing of
       several files or amplification and aggregated services like mixing"""

    _chunkSize = 128  # number of frames to be read from wave file in
                      # one step
    maximumSampleValue = 32767

    #--------------------
    # INTERNAL FEATURES
    #--------------------

    @classmethod
    def _makeFraction (cls,
                       value : Real) -> Tuple:
        """Returns numerator and log2 of denominator representing value"""

        log2denominator = 10
        denominator = int(pow(2, log2denominator))
        numerator = round(value * denominator)
        return (numerator, log2denominator)

    #--------------------

    @classmethod
    def _mix (cls,
              sampleList : IntegerList,
              file : wave.Wave_read,
              mixSetting : Tuple):
        """Mixes audio samples from <file> into <sampleList> using
           <mixSetting>"""

        Logging.trace(">>: file = %r, factor = %s",
                      file, mixSetting)

        volumeFactor = _decibelsToReal(mixSetting[0])
        numerator, log2denominator = cls._makeFraction(volumeFactor)
        fileSampleList  = file.readAllSamples()
        fileSampleCount = len(fileSampleList)

        for i in range(fileSampleCount):
            sampleList[i] += (fileSampleList[i]
                              * numerator >> log2denominator)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self,
                  filePath : String,
                  mode : String):
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

    def __repr__ (self) -> String:
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

    def frameCount (self) -> Natural:
        """Returns frame count of audio file"""

        Logging.trace(">>: %r", self)
        result = self._file.getnframes()
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def getParameters (self) -> Tuple:
        """Gets the parameters for wav file <self>"""

        Logging.trace(">>: %r", self)

        channelCount, sampleSize, frameRate, frameCount, _, _ = \
            self._file.getparams()
        result = (channelCount, sampleSize, frameRate, frameCount)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def maximumVolume (cls,
                       sampleList : IntegerList) -> Natural:
        """Returns maximum volume in <sampleList>"""

        Logging.trace(">>")

        maxValue = max(*sampleList)
        minValue = min(*sampleList)
        result = max(abs(maxValue), abs(minValue))

        Logging.trace("<<: %d", result)
        return result

    #--------------------

    @classmethod
    def mix (cls,
             sourceFilePathList : StringList,
             mixSettingList : TupleList,
             amplificationLevel : Real,
             targetFilePath : String):
        """Mixes WAV audio files given in <sourceFilePathList> to target WAV
           file with <targetFilePath> with volumes and pan positions
           given by <mixSettingList> with loudness amplification given
           by <amplificationLevel> via Python modules only"""

        Logging.trace(">>: sourceFiles = %r, mixSettings = %r,"
                      + " level = %4.3f, targetFile = %r",
                      sourceFilePathList, mixSettingList,
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
            mixSetting = mixSettingList[i]
            cls._mix(resultSampleList, sourceFile, mixSetting)

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
    def open (cls,
              filePath : String,
              mode : String) -> Object:
        """Opens wav file on path <filePath> with read/write mode specified by
           <mode>"""

        return cls(filePath, mode)

    #--------------------

    def readAllSamples (self) -> IntegerList:
        """Returns all samples in <wavFile> as an integer list"""

        Logging.trace(">>:%r", self)

        self.readAllSamplesRaw()
        sampleCount = self._channelCount * self._frameCount
        unpackFormat = "<%uh" % sampleCount
        result = struct.unpack(unpackFormat, self._buffer)

        Logging.trace("<<")
        return result

    #--------------------

    def readAllSamplesRaw (self) -> String:
        """Returns all samples in <wavFile> as an encoded string"""

        Logging.trace(">>: %r", self)

        if self._bufferIsEmpty:
            self._bufferIsEmpty = False
            self._buffer = self._file.readframes(self._frameCount)

        Logging.trace("<<")
        return self._buffer

    #--------------------

    @classmethod
    def scale (cls,
               sampleList : IntegerList,
               factor : Real):
        """Scales <sampleList> inline by <factor>"""

        Logging.trace(">>: factor = %4.3f", factor)

        numerator, log2denominator = cls._makeFraction(factor)

        for sample in sampleList:
            sample = (sample * numerator) >> log2denominator

        Logging.trace("<<")

    #--------------------

    def setParameters (self,
                       channelCount : Natural,
                       sampleSize : Natural,
                       frameRate : Natural,
                       frameCount : Natural):
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
    def shiftAudio (cls,
                    audioFilePath : String,
                    shiftedFilePath : String,
                    shiftOffset : Real):
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

    def writeSamples (self,
                      sampleList : IntegerList):
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

    def writeSamplesRaw (self,
                         rawSampleList : List):
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

    # settings from configuration file
    _aacCommandLine                : String = None
    _audioProcessorIsSox           : Boolean = None
    _audioProcessorMap             : StringMap = {}
    _intermediateFileDirectoryPath : String = None
    _intermediateFilesAreKept      : Boolean = None
    _ffmpegCommand                 : String = None
    _midiToWavRenderingCommandList : StringList = None
    _soundStyleNameToEffectsMap    : StringMap = {}

    # internal configuration settings
    # _usesSquaredPanningRule : Boolean = False
    
    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _calculateRemixFactorsForBalancing (cls, panPosition):
        """Returns list of pan remix factors l->l, r->l, l->r and r->r from
           <panPosition> between -1 and 1"""

        Logging.trace(">>: %s", panPosition)

        factorLL = iif(panPosition < 0, 1, 1 - panPosition)
        factorRL = 0
        factorLR = 0
        factorRR = iif(panPosition > 0, 1, 1 + panPosition)
        result = (factorLL, factorRL, factorLR, factorRR)

        Logging.trace("<<: %r", result)
        return result
    
    #--------------------

    def _compressAudio (self,
                        audioFilePath : String,
                        songTitle : String,
                        targetFilePath : String):
        """Compresses audio file with <songTitle> in path with
          <audioFilePath> to AAC file at <targetFilePath>"""

        Logging.trace(">>: audioFile = %r, title = %r,"
                      + " targetFile = %r",
                      audioFilePath, songTitle, targetFilePath)

        cls = self.__class__

        OperatingSystem.showMessageOnConsole("== convert to AAC: "
                                             + songTitle)

        commandLine = iif(cls._aacCommandLine != "", cls._aacCommandLine,
                          ("%s -loglevel %s -i ${infile}"
                           + " -c:a aac -b:a 192k"
                           + " -y ${outfile}")
                           % (cls._ffmpegCommand, _ffmpegLogLevel))
        variableMap = { "infile"  : audioFilePath,
                        "outfile" : targetFilePath }
        command = cls._replaceVariablesByValues(tokenize(commandLine),
                                                variableMap)

        OperatingSystem.executeCommand(command, True)

        Logging.trace("<<")

    #--------------------

    def _convertMidiToAudio (self,
                             songName : String,
                             voiceMidiFilePath : String,
                             targetFilePath : String):
        """Converts voice data in midi file with <voiceMidiFilePath>
           for song named <songName> to raw audio file with
           <targetFilePath>"""

        Logging.trace(">>: songName = %r, midiFile = %r, targetFile = %r",
                      songName, voiceMidiFilePath, targetFilePath)

        cls = self.__class__

        # processing midi file via given command
        template = "== convertMidiToWav for %r into %s"
        targetFileBaseName = OperatingSystem.basename(targetFilePath)
        OperatingSystem.showMessageOnConsole(template
                                             % (songName,
                                                targetFileBaseName))

        variableMap = { "infile"  : voiceMidiFilePath,
                        "outfile" : targetFilePath }
        command = \
            cls._replaceVariablesByValues( \
                                cls._midiToWavRenderingCommandList,
                                variableMap)
        OperatingSystem.executeCommand(command, True)

        Logging.trace("<<")

    #--------------------

    def _extractEffectListSrcAndTgt \
            (self,
             voiceName : String,
             chainPosition : String,
             partPosition : String,
             debugFileCount : Natural,
             effectTokenList : StringList) -> Tuple:
        """Returns information about the success of operation, list of
           sources and single target from audio refinement effect
           chain <effectTokenList>; adapts <effectTokenList>
           accordingly by deleting those tokens; <voiceName> gives
           name of current voice; <chainPosition> tells whether this
           is a single, the first, last or other chain; <partPosition>
           tells whether this is a single, the first, last or other
           part within a chain (separated by "tee" constructs);
           <debugFileCount> gives the index of the next available tee
           file"""

        Logging.trace(">>: voice = %s, chainPosition = %r,"
                      + " partPosition = %r, debugFileCount = %d,"
                      + " effects = %r",
                      voiceName, chainPosition, partPosition,
                      debugFileCount, effectTokenList)

        cls = self.__class__

        tempFilePathProc = \
            (lambda st:
             (_tempAudioFileTemplate
              % (self._audioDirectoryPath, voiceName, st)))

        sourceFilePath = \
            "%s/%s.wav" % (self._audioDirectoryPath, voiceName)
        targetFilePath = (_processedAudioFileTemplate %
                          (self._audioDirectoryPath, voiceName))
        teeFilePathProc = \
            (lambda i: tempFilePathProc("%02X" % i))
        chainFilePathProc = tempFilePathProc

        # collect sources and targets and delete them from token list
        redirector = re.escape(cls._audioProcessorMap["redirector"])
        indicatorRegExp = re.compile(redirector + r"([A-Za-z]+)")
        targetList = \
            cls._extractMatchingElementsFromList(effectTokenList,
                                                 indicatorRegExp)
        indicatorRegExp = re.compile(r"([A-Za-z]*)" + redirector)
        sourceList = \
            cls._extractMatchingElementsFromList(effectTokenList,
                                                 indicatorRegExp)

        # make simple plausibility checks
        def validationProc (condition, message):
             if not condition: Logging.traceError(message)
             isOkay = False

        isOkay = True
        validationProc(len(targetList) == 1,
                       "only one target is allowed in chain fragment")
        validationProc(chainPosition != "LAST" or len(targetList) == 0,
                       "last chain may not have an explicit target")
        validationProc(partPosition in ["SINGLE", "LAST"]
                       or len(targetList) == 0,
                       "only last fragment in chain may have a target")
        validationProc(partPosition in ["SINGLE", "FIRST"]
                       or len(sourceList) == 0,
                       "only first fragment in chain may have a source")
            
        if isOkay:
            # fine, calculate the effective sources and targets
            if len(sourceList) > 0:
                tempList = sourceList
                sourceList = []

                for source in tempList:
                    source = iif(source == "", sourceFilePath,
                                 chainFilePathProc(source))
                    sourceList.append(source)
            elif partPosition in ["SINGLE", "FIRST"]:
                sourceList = [ sourceFilePath ]
            else:
                sourceList = teeFilePathProc(debugFileCount)

            if len(targetList) > 0:
                target = chainFilePathProc(targetList[0])
            elif chainPosition in ["FIRST", "OTHER"]:
                # output goes to tee file
                debugFileCount += 1
                target = teeFilePathProc(debugFileCount)
            else:
                target = targetFilePath

        Logging.trace("<<: isOkay = %s, effects = %r, sources = %r,"
                      " target = %r, debugFileCount = %d",
                      isOkay, effectTokenList, sourceList,
                      target, debugFileCount)
        return (isOkay, sourceList, target, debugFileCount)

    #--------------------

    @classmethod
    def _extractMatchingElementsFromList (cls,
                                          elementList : StringList,
                                          elementRegExp : Object) \
                                          -> StringList:
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

    def _makeFilteredMidiFile (self,
                               voiceName : String,
                               midiFilePath : String,
                               voiceMidiFilePath : String):
        """Filters tracks in midi file named <midiFilePath> belonging
           to voice with <voiceName> and writes them to
           <voiceMidiFilePath>"""

        Logging.trace(">>: voice = %s, midiFile = %r, targetFile = %r",
                      voiceName, midiFilePath, voiceMidiFilePath)

        cls = self.__class__
        midiTransformer = MidiTransformer(midiFilePath,
                                          cls._intermediateFilesAreKept)
        midiTransformer.filterByTrackNamePrefix(voiceName)
        midiTransformer.removeUnwantedControlCodes()
        midiTransformer.save(voiceMidiFilePath)

        Logging.trace("<<")

    #--------------------

    def _mixToWavFile (self,
                       sourceFilePathList : StringList,
                       mixSettingList : TupleList,
                       masteringEffectList : StringList,
                       amplificationLevel : Real,
                       targetFilePath : String):
        """Mixes WAV audio files given in <sourceFilePathList> to target WAV
           file with <targetFilePath> with volumes and pan positions
           given by <mixSettingList> with loudness amplification given
           by <amplificationLevel> either externally or with slow
           internal algorithm; <masteringEffectList> gives the
           refinement effects for this track (if any) to be applied
           after the mix"""

        Logging.trace(">>: sourceFiles = %r, mixSettings = %r,"
                      + " masteringEffects = %r, amplification = %4.3f,"
                      + " targetFile = %r",
                      sourceFilePathList, mixSettingList,
                      masteringEffectList, amplificationLevel,
                      targetFilePath)

        cls = self.__class__

        if "mixingCommandLine" in cls._audioProcessorMap:
            self._mixToWavFileExternally(sourceFilePathList,
                                         mixSettingList,
                                         masteringEffectList,
                                         amplificationLevel,
                                         targetFilePath)
        else:
            if len(masteringEffectList) > 0:
                Logging.trace("--: WARNING - no mastering available"
                              + " when using internal mixing,"
                              + " effects %r discarded",
                              masteringEffectList)

            _WavFile.mix(sourceFilePathList, mixSettingList,
                         amplificationLevel, targetFilePath)

        Logging.trace("<<")

    #--------------------

    def _mixToWavFileExternally (self,
                                 sourceFilePathList : StringList,
                                 mixSettingList : TupleList,
                                 masteringEffectList : StringList,
                                 amplificationLevel, targetFilePath):
        """Mixes WAV audio files given in <sourceFilePathList> to target WAV
           file with <targetFilePath> with volumes and pan positions
           given by <mixSettingList> with loudness amplification given
           by <amplificationLevel> using external command;
           <masteringEffectList> gives the refinement effects for this
           track (if any) to be applied after mixing"""

        Logging.trace(">>: sourceFiles = %r, mixSettings = %r,"
                      + " masteringEffects = %r, level = %4.3f,"
                      + " targetFile = %r",
                      sourceFilePathList, mixSettingList,
                      masteringEffectList, amplificationLevel,
                      targetFilePath)

        cls = self.__class__

        # some shorthands
        audioProcMap     = cls._audioProcessorMap
        replaceVariables = cls._replaceVariablesByValues

        # check whether mastering is done after mixing
        masteringPassIsRequired = (amplificationLevel != 0
                                   or len(masteringEffectList) > 0)
        intermediateFilePath = self._audioDirectoryPath + "/result-mix.wav"
        intermediateFilePath = iif(masteringPassIsRequired,
                                   intermediateFilePath, targetFilePath)

        Logging.trace("--: masteringPass = %r, intermediateFile = %r",
                      masteringPassIsRequired, intermediateFilePath)

        # do the mix of the audio sources
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

            if "${pan}" not in commandRepeatingPart:
                # mixing command line cannot pan the inputs => use
                # ffmpeg and replace list of files by some
                # intermediate file names
                sourceFilePathList = \
                    self._panWavFilesExternally(sourceFilePathList,
                                                mixSettingList)
            
            elementCount = len(sourceFilePathList)
            command = []

            for i in range(elementCount):
                mixSetting   = mixSettingList[i]
                filePath     = sourceFilePathList[i]
                volumeFactor = _decibelsToReal(mixSetting[0])
                panPosition  = mixSetting[1]
                variableMap = { "factor" : volumeFactor,
                                "pan"    : panPosition,
                                "infile" : filePath }
                part = replaceVariables(commandRepeatingPart, variableMap)
                command.extend(part)

            Logging.trace("--: repeating part = %r", command)

            commandList = commandPrefix + command + commandSuffix
            variableMap = { "outfile" : intermediateFilePath }
            command = replaceVariables(commandList, variableMap)
            OperatingSystem.executeCommand(command, True)

        if masteringPassIsRequired:
            # do mastering and amplification
            amplificationEffect = audioProcMap["amplificationEffect"]
            amplificationEffectTokenList = tokenize(amplificationEffect)
            variableMap  = { "amplificationLevel" : amplificationLevel }
            nmEffectPartList = replaceVariables(amplificationEffectTokenList,
                                                variableMap)
            effectList = masteringEffectList + nmEffectPartList

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

    def _mixVoicesToWavFile (self,
                             voiceNameList : StringList,
                             voiceNameToMixSettingMap : StringMap,
                             parallelTrackFilePath : String,
                             masteringEffectList : StringList,
                             amplificationLevel : Real,
                             targetFilePath : String):
        """Constructs and executes a command for audio mixing to target file
           with <targetFilePath> from given <voiceNameList>, the
           mapping to volumes and pan positions in
           <voiceNameToMixSettingMap> with loudness amplification
           given by <amplificationLevel>; <masteringEffectList> gives
           the refinement effects for this track (if any) to be
           applied after mixing; if <parallelTrackPath> is not empty,
           the parallel track is added"""

        Logging.trace(">>: voiceNames = %r, audioLevels = %r"
                      + " parallelTrack = %r, masteringEffects = %r"
                      + " amplification = %5.3f, target = %r",
                      voiceNameList, voiceNameToMixSettingMap,
                      parallelTrackFilePath, masteringEffectList,
                      amplificationLevel, targetFilePath)

        sourceFilePathList = []
        mixSettingList   = []

        # set default setting to volume 0 and centered pan (to ensure
        # that the volume is defined in the map)
        defaultMixSetting = (0, 0)

        for voiceName in voiceNameList:
            audioFilePath = (_processedAudioFileTemplate
                             % (self._audioDirectoryPath, voiceName))
            mixSetting = voiceNameToMixSettingMap.get(voiceName,
                                                      defaultMixSetting)
            sourceFilePathList.append(audioFilePath)
            mixSettingList.append(mixSetting)

        if parallelTrackFilePath != "":
            mixSetting = voiceNameToMixSettingMap["parallel"]
            sourceFilePathList.append(parallelTrackFilePath)
            mixSettingList.append(mixSetting)

        self._mixToWavFile(sourceFilePathList, mixSettingList,
                           masteringEffectList, amplificationLevel,
                           targetFilePath)
        Logging.trace("<<")

    #--------------------

    def _panWavFilesExternally (self,
                                sourceFilePathList : StringList,
                                mixSettingList : TupleList) -> StringList:
        """Pans WAV source files in <sourceFilePathList> by pan positions
           in corresponding <mixSettingList> into temporary files and
           returns the list of those file names"""

        Logging.trace(">>: sourceFiles = %r, mixSettings = %r",
                      sourceFilePathList, mixSettingList)

        cls = self.__class__
        result = []

        for i, sourceFileName in enumerate(sourceFilePathList):
            mixSetting = mixSettingList[i]
            panPosition = mixSetting[1]

            # pan source file via ffmpeg
            fileNameStem = \
                (OperatingSystem.basename(sourceFileName, False)
                 .replace(_processedAudioFileNameSuffix, "")
                 + _pannedAudioFileNameSuffix)
            pannedFileName = ("%s/%s.wav"
                              % (self._audioDirectoryPath,
                                 fileNameStem))
            result.append(pannedFileName)

            factorLL, factorRL, factorLR, factorRR = \
                cls._calculateRemixFactorsForBalancing(panPosition)
            remixSpecification = \
                (("|c0=%4.3f*c0+%4.3f*c1" % (factorLL, factorRL))
                 +("|c1=%4.3f*c0+%4.3f*c1" % (factorLR, factorRR)))
            panSpecification = "pan=stereo%s" % remixSpecification
            ffmpegCommand = (cls._ffmpegCommand,
                             "-loglevel", _ffmpegLogLevel,
                             "-i", sourceFileName,
                             "-af", panSpecification,
                             "-y", pannedFileName)
            OperatingSystem.executeCommand(ffmpegCommand, True)
        
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _powerset (cls,
                   currentList : List) -> List:
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

    def _processAudioRefinement (self,
                                 voiceName : String,
                                 audioProcessingEffects : String):
        """Handles audio processing given by <audioProcessingEffects>"""

        Logging.trace(">>: voice = %s, effects = %r",
                      voiceName, audioProcessingEffects)

        cls = self.__class__

        debugFileCount = 0
        separator = cls._audioProcessorMap["chainSeparator"]
        fragmentSeparator = " tee "
        chainCommandList = \
            splitAndStrip(audioProcessingEffects, separator)
        chainCommandCount = len(chainCommandList)

        for chainIndex, chainProcessingEffects in \
            enumerate(chainCommandList):
            # the position of this chain may be: "single" when there
            # is only one chain, "first" when it starts the list of
            # chains, "last" when it trails the list of chains and
            # "other" when it is somewhere in between
            chainPosition = \
                iif3(chainCommandCount == 1, "SINGLE",
                     chainIndex == 0, "FIRST",
                     chainIndex == chainCommandCount - 1, "LAST",
                     "OTHER")

            Logging.trace("--: chain[%d] = %r",
                          chainIndex, chainProcessingEffects)

            # a fragment is a command sequence in the chain that must
            # be processed separately, because a "tee" command had
            # inserted a measuring point
            fragmentList = \
                splitAndStrip(chainProcessingEffects, fragmentSeparator)

            isOkay, debugFileCount = \
                self._processRefinementFragments(voiceName,
                                                 chainPosition,
                                                 fragmentList,
                                                 debugFileCount)

            if not isOkay:
                break

        Logging.trace("<<")

    #--------------------

    def _processRefinementFragments (self,
                                     voiceName : String,
                                     chainPosition : String,
                                     fragmentList : StringList,
                                     debugFileCount : Natural) -> Tuple:
        """Processes refinement fragments within chain for voice named
           <voiceName> defined by <fragmentList> with a chain at
           position <chainPosition>; uses <debugFileCount> for
           indexing temporary files; returns success of operation and
           updated debug file count"""

        Logging.trace(">>: voice = %s, chainPosition = %s,"
                      " fragmentList = %r, debugFileCount = %d",
                      voiceName, chainPosition, fragmentList,
                      debugFileCount)

        cls = self.__class__
        isOkay = True
        fragmentCount = len(fragmentList)
        refinementCommand = \
            cls._audioProcessorMap["refinementCommandLine"]
        refCmdTokenList = tokenize(refinementCommand)

        for i, effectsList in enumerate(fragmentList):
            effectsTokenList = cls._tokenizeRefinementLine(effectsList)
            fragmentPosition = iif3(fragmentCount == 1, "SINGLE",
                                    i == 0, "FIRST",
                                    i == fragmentCount - 1, "LAST",
                                    "OTHER")

            isOkay, sourceList, currentTarget, debugFileCount = \
                self._extractEffectListSrcAndTgt(voiceName,
                                                 chainPosition,
                                                 fragmentPosition,
                                                 debugFileCount,
                                                 effectsTokenList)

            if not isOkay:
                Logging.traceError("skipped because of bad syntax")
                break
            elif (len(effectsTokenList) == 0
                  or effectsTokenList[0] != "mix"):
                currentSource = sourceList[0]
                variableMap = { "infile"   : currentSource,
                                "outfile"  : currentTarget,
                                "effects"  : effectsTokenList }
                command = \
                    cls._replaceVariablesByValues(refCmdTokenList,
                                                  variableMap)
                OperatingSystem.executeCommand(command, True)
            else:
                # a mix command, all sources and targets have been
                # removed, so only the volumes (in decibels) remain
                volumeList = effectsTokenList[1:]

                if len(volumeList) < len(sourceList):
                    Logging.traceError("bad argument pairing for mix")
                else:
                    mixSettingList = []
                        
                    for i in range(len(sourceList)):
                        volume = volumeList[i]
                        valueName = "value %d in mix" % (i+1)
                        ValidityChecker.isNumberString(volume,
                                                       valueName, True)
                        mixSettingList.append((float(volume), 0))
                        
                    self._mixToWavFile(sourceList, mixSettingList,
                                       "", 0.0, currentTarget)

        result = (isOkay, debugFileCount)
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def _replaceVariablesByValues (cls,
                                   stringList : StringList,
                                   variableMap : StringMap) -> StringList:
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
    def _shiftAudioFile (cls,
                         songName : String,
                         audioFilePath : String,
                         shiftedFilePath : String,
                         shiftOffset : Real):
        """Shifts audio file in <audioFilePath> to shifted audio in
           <shiftedFilePath> with silence prefix of length
           <shiftOffset>"""

        Logging.trace(">>: songName = %r, infile = %r, outfile = %r,"
                      + " shiftOffset = %7.3f",
                      songName, audioFilePath, shiftedFilePath, shiftOffset)

        shiftedFileBaseName = OperatingSystem.basename(shiftedFilePath)
        template = "== shifting %r for %r by %7.3fs"
        OperatingSystem.showMessageOnConsole(template
                                             % (shiftedFileBaseName,
                                                songName, shiftOffset))

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
    def _shiftAudioFileExternally (cls,
                                   commandLine : String,
                                   audioFilePath : String,
                                   shiftedFilePath : String,
                                   shiftOffset : Real):
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
        OperatingSystem.executeCommand(command, True)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _tagAudio (cls,
                   audioFilePath : String,
                   configData : LTBVC_ConfigurationData,
                   songTitle : String,
                   albumName : String):
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

    @classmethod
    def _tokenizeRefinementLine (cls,
                                 st : String):
        """Tokenizes a refinement line masking the redirection
           strings"""

        Logging.trace(">>: '%s'", st)

        # ensure that redirector is kept with preceeding or following
        # identifier
        redirector = cls._audioProcessorMap["redirector"]
        replacement = "XYZZY"
        st = st.replace(redirector, replacement)
        result = [ element.replace(replacement, redirector)
                   for element in tokenize(st) ]

        Logging.trace("<<: %r", result)
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls,
                    aacCommandLine : String,
                    audioProcessorMap : StringMap,
                    ffmpegCommand : String,
                    midiToWavCommandLine : String,
                    soundStyleNameToEffectsMap : StringMap,
                    intermediateFilesAreKept : Boolean,
                    intermediateFileDirectoryPath : String):
        """Sets some global processing data like e.g. the command
           paths."""

        Logging.trace(">>: aac = %r, audioProcessor = %r,"
                      + " ffmpeg = %r, midiToWavCommand = %r,"
                      + " soundStyleNameToEffectsMap = %r,"
                      + " intermediateFilesAreKept = %r"
                      + " intermediateFileDirectoryPath = %r",
                      aacCommandLine, audioProcessorMap,
                      ffmpegCommand, midiToWavCommandLine,
                      soundStyleNameToEffectsMap,
                      intermediateFilesAreKept,
                      intermediateFileDirectoryPath)

        cls._aacCommandLine                = aacCommandLine
        cls._audioProcessorMap             = audioProcessorMap
        cls._intermediateFilesAreKept      = intermediateFilesAreKept
        cls._intermediateFileDirectoryPath = intermediateFileDirectoryPath
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

    def __init__ (self,
                  audioDirectoryPath : String):
        """Initializes generator with target directory of all audio
           files to be stored in <audioDirectoryPath>"""

        Logging.trace(">>: audioDirectoryPath = %r", audioDirectoryPath)

        self._audioDirectoryPath = audioDirectoryPath

        Logging.trace("<<")

    #--------------------

    @classmethod
    def constructSettingsForAudioTracks \
            (cls,
             configData : LTBVC_ConfigurationData) -> List:
        """Constructs a list of tuples each representing a target audio file
           from mapping <audioGroupNameToVoiceNameListMap> and
           <audioTrackNameToDataMap> and given <voiceNameList> in
           <configData>; each tuple contains the set of voice names
           used, its album name, its song title and its target file
           path"""

        Logging.trace(">>")

        result = []
        groupToVoiceSetMap = configData.audioGroupNameToVoiceNameSetMap
        audioTrackNameToDataMap = configData.audioTrackNameToDataMap

        Logging.trace("--: groupToVoiceSetMap = %r, trackList = %r",
                      groupToVoiceSetMap, audioTrackNameToDataMap)

        # traverse all audio track objects
        for trackName, audioTrack in audioTrackNameToDataMap.items():
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
                        audioTrack.voiceNameToMixSettingMap,
                        audioTrack.masteringEffectList,
                        audioTrack.amplificationLevel)
            Logging.trace("--: appending %r for track name %r",
                          newEntry, audioTrack.name)
            result.append(newEntry)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def copyOverrideFile (self,
                          songName : String,
                          voiceName : String,
                          filePath : String,
                          shiftOffset : Real):
        """Sets refined file from <filePath> for voice with
           <voiceName> in song named <songName> and applies
           <shiftOffset>"""

        Logging.trace(">>: song = %r, voice = %r, file = %r, offset = %7.3f",
                      songName, voiceName, filePath, shiftOffset)

        cls = self.__class__
        message = ("== overriding %r in %r from file"
                   % (voiceName, songName))
        OperatingSystem.showMessageOnConsole(message)

        targetFilePath = (_processedAudioFileTemplate
                          % (self._audioDirectoryPath, voiceName))
        cls._shiftAudioFile(songName, filePath, targetFilePath, shiftOffset)

        Logging.trace("<<")

    #--------------------

    def generateRawAudio (self,
                          songName : String,
                          midiFilePath : String,
                          voiceName : String,
                          shiftOffset : Real):
        """Generates audio wave file for <voiceName> in song named
           <songName> from midi file with <midiFilePath> in target
           directory; if several midi tracks match voice name, the
           resulting audio files are mixed; output is dry (no chorus,
           reverb and delay) and contains leading and trailing silent
           passages; if <shiftOffset> is greater that zero, the target
           file is shifted by that amount"""

        Logging.trace(">>: songName = %r, voice = %s, midiFile = %r,"
                      + " shiftOffset = %7.3f",
                      songName, voiceName, midiFilePath, shiftOffset)

        cls = self.__class__
        tempMidiFilePath = (cls._intermediateFileDirectoryPath
                            + "/tempRender-%s.mid" % voiceName)
        isShifted = (shiftOffset > 0)
        defaultTemplate = "%s/%s.wav"
        filePathTemplate = iif(isShifted, "%s/%s-raw.wav", defaultTemplate)
        audioFilePath = filePathTemplate % (self._audioDirectoryPath,
                                            voiceName)

        self._makeFilteredMidiFile(voiceName, midiFilePath, tempMidiFilePath)
        self._convertMidiToAudio(songName, tempMidiFilePath, audioFilePath)

        if isShifted:
            targetFilePath = defaultTemplate % (self._audioDirectoryPath,
                                                voiceName)
            cls._shiftAudioFile(songName, audioFilePath, targetFilePath,
                                shiftOffset)
            OperatingSystem.removeFile(audioFilePath,
                                       cls._intermediateFilesAreKept)

        OperatingSystem.removeFile(tempMidiFilePath,
                                   cls._intermediateFilesAreKept)

        Logging.trace("<<")

    #--------------------

    def generateRefinedAudio (self,
                              songName : String,
                              voiceName : String,
                              soundVariant : String,
                              reverbLevel : Real):
        """Generates refined audio wave file for <voiceName> in song
           named <songName> from raw audio file in target directory;
           <soundVariant> gives the kind of postprocessing ('COPY',
           'STD', 'EXTREME', ...) and <reverbLevel> the percentage of
           reverb to be used for that voice"""

        Logging.trace(">>: song = %r, voice = %s, variant = %s,"
                      + " reverb = %4.3f",
                      songName, voiceName, soundVariant, reverbLevel)

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

        message = ("== processing %s (%s) in %r"
                   % (voiceName, soundVariant, songName))
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

        # if not isCopyVariant:
        if True:
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

    def mix (self,
             configData : LTBVC_ConfigurationData):
        """Combines the processed audio files for all voices in
           <configData.voiceNameList> into several combination files
           and converts them to aac format; <configData> defines the
           voice volumes and pan positions, the relative amplification
           level, the optional voices as well as the tags and suffices
           for the final files"""

        Logging.trace(">>: configData = %r", configData)

        cls = self.__class__

        voiceProcessingList = \
            cls.constructSettingsForAudioTracks(configData)

        for v in voiceProcessingList:
            currentVoiceNameList, albumName, songTitle, \
              targetFilePath, _, languageCode, voiceNameToMixSettingMap, \
              masteringEffectList, amplificationLevel = v
            waveIntermediateFilePath = ("%s/result_%s.wav"
                                        % (self._audioDirectoryPath,
                                           languageCode))
            OperatingSystem.showMessageOnConsole("== make mix file: %s"
                                                 % songTitle)

            if configData.parallelTrackFilePath != "":
                parallelTrackVolume = configData.parallelTrackVolume
                voiceNameToMixSettingMap["parallel"] = \
                    (parallelTrackVolume, 0)

            self._mixVoicesToWavFile(currentVoiceNameList,
                                     voiceNameToMixSettingMap,
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
