# lilypondpngvideogenerator -- processes lilypond file, scans postscript
#                              file for page boundaries, analyzes tempo
#                              track and generates MP4 video and
#                              subtitle file
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

import re

import basemodules.simpleassertion
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, Map, Natural, Real, \
                                    RealList, String
from basemodules.operatingsystem import OperatingSystem
from basemodules.ttbase import iif
from basemodules.utf8file import UTF8File
from basemodules.validitychecker import ValidityChecker

simpleassertion = basemodules.simpleassertion

#====================

_ffmpegCommand   = None
_lilypondCommand = None

_infinity = 999999

# ==== configuration settings ====
# show measure number in subtitle only for 95% of the measure duration
_displayTimePercentage = 0.95

# the log level for ffmpeg rendering
_ffmpegLogLevel = "error"

# encoding of Postscript file of lilypond
_postscriptFileEncoding = "latin_1"

# ==== end of configuration settings ====

#============================================================

class Assertion:
    """Provides all services for assertion checking."""

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def check (cls,
               condition : Boolean,
               message : String):
        """Checks for <condition> and if not satisfied, raises exception
           with <message>."""

        simpleassertion.Assertion.check(condition, message)

    #--------------------

    @classmethod
    def ensureFileExistence (cls,
                             fileName : String,
                             fileKind : String):
        """Checks whether file with <fileName> exists, otherwise gives
           error message about file kind mentioning file name."""

        Logging.trace(">>: name = %r, kind = %s", fileName, fileKind)

        errorTemplate = "%s file does not exist - %r"
        errorMessage = errorTemplate % (fileKind, fileName)
        cls.check(OperatingSystem.hasFile(fileName), errorMessage)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def ensureProgramAvailability (cls,
                                   programName : String,
                                   programPath : String,
                                   option : String):
        """Checks whether program on <programPath> is available and otherwise
           gives error message and exits. <option> is the only
           command-line option for program."""

        Logging.trace(">>: '%s %s'", programName, option)

        cls.check(OperatingSystem.programIsAvailable(programPath, option),
                  ("cannot execute %s program - path %r'"
                   % (programName, programPath)))

        Logging.trace("<<")


#============================================================

class DurationManager:
    """Handles all duration related services like e.g. the calculation
       of the duration list from tempo map and page to measure map."""

    #--------------------

    @classmethod
    def measureToDurationMap (cls,
                              measureToTempoMap : Map,
                              countInMeasures : Natural,
                              lastMeasureNumber : Natural):
        """Calculates mapping from measure number to duration based on
           tempo track in <measureToTempoMap> and the number of
           <countInMeasures>."""

        Logging.trace(">>: measureToTempoMap = %r, countInMeasures = %d,"
                      + " lastMeasureNumber = %d",
                      measureToTempoMap, countInMeasures, lastMeasureNumber)

        firstMeasureNumber = 1

        Assertion.check(firstMeasureNumber in measureToTempoMap,
                        "tempo track must contain setting for first measure")

        (tempo, measureLength) = measureToTempoMap[firstMeasureNumber]
        duration = cls.measureDuration(tempo, measureLength)
        firstMeasureOffset = duration * countInMeasures
        result = {}
        measureList = range(firstMeasureNumber, lastMeasureNumber + 1)

        for measureNumber in measureList:
            if measureNumber in measureToTempoMap:
                (tempo, measureLength) = measureToTempoMap[measureNumber]
                duration = cls.measureDuration(tempo, measureLength)

            isNormalMeasureNumber = (measureNumber > firstMeasureNumber)
            currentMeasureDuration = (duration +
                                      iif(isNormalMeasureNumber, 0,
                                          firstMeasureOffset))
            result[measureNumber] = currentMeasureDuration

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def pageDurationList (cls,
                          pageToMeasureMap : Map,
                          measureToDurationMap : Map) -> RealList:
        """Calculates page duration list based on mapping of pages to
           measures <pageToMeasureMap> and the mapping of measures to
           durations <measureToDurationMap>"""

        Logging.trace(">>: pToM = %r, mToD = %r",
                      pageToMeasureMap, measureToDurationMap)

        result = []
        previousPageMeasureNumber = min(measureToDurationMap.keys())
        pageList = list(pageToMeasureMap.keys())
        pageList.sort()

        for page in pageList:
            if page > 1:
                currentPageMeasureNumber = pageToMeasureMap[page]

                # calculate duration of previous page from
                # <previousMeasure> to <currentMeasure> - 1
                pageDuration = 0

                for measureNumber in range(previousPageMeasureNumber,
                                           currentPageMeasureNumber):
                    pageDuration += measureToDurationMap[measureNumber]

                result.append(pageDuration)
                previousPageMeasureNumber = currentPageMeasureNumber

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def measureDuration (cls,
                         tempo : Real,
                         measureLength : Real) -> Real:
        """Returns the duration of some measure with <measureLength>
           quarters and <tempo> given in quarters per minute."""

        if tempo <= 1:
            result = _infinity
        else:
            result = (60.0 * measureLength) / tempo

        return result

    #--------------------

    @classmethod
    def quantizeDurationList (cls,
                              durationList : RealList,
                              frameRate : Real):
        """Adjusts <durationList> such that it conforms to
           <frameRate>."""

        Logging.trace(">>: durations = %r, frameRate = %f",
                      durationList, frameRate)

        frameDuration = 1.0 / frameRate
        unallocatedDuration = 0

        for (i, duration) in enumerate(durationList):
            duration += unallocatedDuration
            frameCount = int(duration / frameDuration)
            effectiveDuration = frameCount * frameDuration
            unallocatedDuration = duration - effectiveDuration
            durationList[i] = effectiveDuration

        Logging.trace("<<: %r", durationList)

#============================================================

class PostscriptFile:
    """Represents the source for getting the transitions between the
       pages i.e. the mapping from page index to first measure on
       page."""

    _fileName = None

    # relevant constants for analyzing the postscript file
    _barNumberColourSettingText = " 0.0010 0.0020 0.0030 setrgbcolor"
    _digitRegexp                = re.compile(r".*/(zero|one|two|three|four"
                                             + r"|five|six|seven|eight|nine)")
    _endOfFileText              = "%EOF"
    _fontDefinitionText         = "selectfont"
    _pageRegexp                 = re.compile(r"%%Page: *(\w+)")
    _printGlyphsText            = "print_glyphs"

    _digitMap = { "zero" : 0, "one" : 1, "two" : 2, "three" : 3,
                  "four" : 4, "five" : 5, "six" : 6, "seven" : 7,
                  "eight" : 8, "nine" : 9 }

    #--------------------

    @classmethod
    def setName (cls,
                 name : String):
        """Sets name of postscript file."""

        Logging.trace(">>: %r", name)

        Assertion.ensureFileExistence(name, "postscript")
        cls._fileName = name

        Logging.trace("<<")

    #--------------------

    @classmethod
    def pageToMeasureMap (cls) -> Map:
        """Scans postscript file for page numbers and measure numbers
           by some naive pattern matching and returns mapping from
           page to lowest measure number in page.  Assumes that pages
           and page numbers are strictly ascending."""

        Logging.trace(">>")

        # read postscript file into line list
        postscriptFile = UTF8File(cls._fileName, 'rb')
        lineList = [ line.decode(_postscriptFileEncoding).rstrip()
                     for line in postscriptFile.readlines() ]
        postscriptFile.close()

        Logging.trace("--: lineListCount = %d", len(lineList))

        # do the processing in a finite state machine
        ParseState_inLimbo           = 1
        ParseState_inPage            = 2
        ParseState_beforeMeasureText = 3
        ParseState_inMeasureText     = 4

        result = {}
        parseState = ParseState_inLimbo
        maximumPageNumber = 0
        maximumMeasureNumber = 0
        pageNumber = 0

        for line in lineList:
            lineIsPageStart = cls._pageRegexp.match(line)

            if lineIsPageStart or cls._endOfFileText in line:
                if pageNumber > 0:
                    Logging.trace("--: firstMeasure = %d, measureCount = %d",
                                  pageMeasureNumber, measureCount)

            # wait for a page start when not within page
            if parseState == ParseState_inLimbo and not lineIsPageStart:
                continue

            if lineIsPageStart:
                parseState = ParseState_inPage
                matchList = cls._pageRegexp.match(line)
                pageNumber = int(matchList.group(1))
                Logging.trace("--: entering page %d", pageNumber)
                maximumPageNumber = max(pageNumber, maximumPageNumber)
                pageMeasureNumber = _infinity
                measureCount = 0
            elif parseState == ParseState_inPage:
                if cls._barNumberColourSettingText in line:
                    parseState = ParseState_beforeMeasureText
                    currentNumber = 0
                    currentFactor = 1
            elif parseState == ParseState_beforeMeasureText:
                # skip over lines that are not a "selectfont"
                parseState = iif(cls._fontDefinitionText in line,
                                 ParseState_inMeasureText, parseState)
            elif parseState == ParseState_inMeasureText:
                if cls._digitRegexp.search(line):
                    matchList = cls._digitRegexp.match(line)
                    digit = matchList.group(1)
                    currentNumber += cls._digitMap[digit] * currentFactor
                    currentFactor *= 10
                else:
                    parseState = ParseState_inPage

                    if (cls._printGlyphsText in line
                        and currentNumber > maximumMeasureNumber):
                        Logging.trace("--: measure number %d",
                                      currentNumber)
                        pageMeasureNumber = min(currentNumber,
                                                pageMeasureNumber)
                        result[pageNumber] = pageMeasureNumber
                        maximumMeasureNumber = currentNumber

        # correct the first entry: first page always starts with
        # measure 1
        result[1] = 1

        # add an artificial last page to measure map
        maximumPageNumber += 1
        lastMeasureNumber = maximumMeasureNumber + 8
        result[maximumPageNumber] = lastMeasureNumber

        Logging.trace("<<: %r", result)
        return result

#============================================================

class MP4Video:
    """Handles the generation of the target MP4 video file."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _tempFileName = "temp-noaudio.mp4"

    # command
    _ffmpegCommand = None

    # files and paths
    _concatSpecificationFileName = None
    _intermediateFileNameTemplate = None
    _pageFileNameTemplate = None

    # video parameters
    _ffmpegPresetName = None
    _frameRate = None
    _scaleFactor = None
    _generatorLogLevel = None
    _defaultMp4BaselineLevel = "3.0"

    _pageCount = None

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    fileName = None

    #--------------------

    @classmethod
    def checkParameters (cls):
        """Checks whether data given for this class is plausible for
           subsequent processing."""

        Logging.trace(">>")

        # check the executables
        Assertion.ensureProgramAvailability("ffmpeg", cls._ffmpegCommand,
                                            "-version")

        # check the numeric parameters
        ValidityChecker.isNumberString(cls._scaleFactor, "scale factor",
                                       realIsAllowed=False, rangeKind=">0")
        ValidityChecker.isNumberString(cls._frameRate, "frame rate",
                                       realIsAllowed=True, rangeKind=">0"),
        cls._scaleFactor = int(cls._scaleFactor)
        cls._frameRate   = float(cls._frameRate)

        Logging.trace("<<: parameters okay")

    #--------------------

    @classmethod
    def cleanUpConditionally (cls,
                              filesAreKept : Boolean):
        """Deletes all intermediate files when <filesAreKept> is unset"""

        Logging.trace(">>: %r", filesAreKept)

        for page in range(1, cls._pageCount + 1):
            Logging.trace("--: %d", page)
            fileName = cls._intermediateFileNameTemplate % page
            OperatingSystem.removeFile(fileName, filesAreKept)
            fileName = cls._pageFileNameTemplate % page
            OperatingSystem.removeFile(fileName, filesAreKept)

        OperatingSystem.removeFile(cls._concatSpecificationFileName,
                                   filesAreKept)

        if cls.fileName and cls.fileName == cls._tempFileName:
            OperatingSystem.removeFile(cls.fileName, filesAreKept)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def make (cls,
              pageDurationList : RealList):
        """Generate an MP4 video from durations in <pageDurationList>
           and generated PNG images."""

        Logging.trace(">>: %r", pageDurationList)

        # for each page an MP4 fragment file is generated and finally
        # concatenated into the target file
        concatSpecificationFile = \
                UTF8File(cls._concatSpecificationFileName, 'wt')

        for (i, pageDuration) in enumerate(pageDurationList):
            page = i + 1

            requiredNumberOfFrames = int(cls._frameRate * pageDuration) + 1
            pageFileName = cls._pageFileNameTemplate % page
            intermediateFileName = cls._intermediateFileNameTemplate % page

            # write file name to concatenation file
            normalizedFileName = \
                OperatingSystem.basename(intermediateFileName, True)
            st = "file '%s'\n" % normalizedFileName
            concatSpecificationFile.write(st)

            # make silent video from single lilypond page
            command = ((cls._ffmpegCommand,
                       "-loglevel", cls._generatorLogLevel,
                       "-framerate", "1/" + str(requiredNumberOfFrames),
                       "-i", str(pageFileName),
                       "-vf", "scale=iw/%d:ih/%d" % (cls._scaleFactor,
                                                     cls._scaleFactor),
                       "-r", str(cls._frameRate),
                       "-t", "%02.2f" % pageDuration)
                       + iif(cls._ffmpegPresetName != "",
                             ("-fpre", cls._ffmpegPresetName),
                             ("-pix_fmt", "yuv420p",
                              "-profile:v", "baseline",
                              "-level", cls._defaultMp4BaselineLevel))
                       + ("-y", intermediateFileName))

            OperatingSystem.executeCommand(command, True)

        concatSpecificationFile.close()

        # concatenate silent video fragments into single file
        cls._pageCount = page
        command = (cls._ffmpegCommand,
                   "-safe", "0",
                   "-y",
                   "-loglevel", cls._generatorLogLevel,
                   "-f", "concat",
                   "-i", cls._concatSpecificationFileName,
                   "-codec", "copy",
                   cls.fileName)
        OperatingSystem.executeCommand(command, True)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def setName (cls,
                 fileName : String):
        """Sets file name for MP4 generation to <fileName>; if empty, some
           temporary name will be used."""

        Logging.trace(">>: %r", fileName)

        if fileName == "":
            fileName = cls._tempFileName

        cls.fileName = fileName
        Logging.trace("<<")

#============================================================

class SubtitleFile:
    """Encapsulates generation of an SRT subtitle file."""

    _tempFileName = "temp-subtitle.srt"

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _formatTime (cls,
                     timeInSeconds : Real) -> String:
        """Returns <timeInSeconds> in SRT format with HH:MM:SS,000."""

        hours = int(timeInSeconds / 3600)
        timeInSeconds -= hours * 3600
        minutes = int(timeInSeconds / 60)
        timeInSeconds -= minutes * 60
        seconds = int(timeInSeconds)
        milliseconds = 1000 * (timeInSeconds - seconds)
        return "%02d:%02d:%02d,%03d" % (hours, minutes, seconds, milliseconds)

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    fileName = None

    #--------------------

    @classmethod
    def make (cls,
              measureToDurationMap : Map,
              countInMeasures : Natural):
        """Generates SRT subtitle file from <measureToDuration> and
           <countInMeasures>."""

        Logging.trace(">>: mToDMap = %r, countIn = %d",
                      measureToDurationMap, countInMeasures)

        measureNumberList = list(measureToDurationMap.keys())
        measureNumberList.sort()

        startTime = 0

        subtitleFile = UTF8File(cls.fileName, 'wt')

        for measureNumber in measureNumberList:
            duration = measureToDurationMap[measureNumber]
            endTime = startTime + _displayTimePercentage * duration
            st = (cls._formatTime(startTime) + " --> "
                  + cls._formatTime(endTime))
            startTime += duration

            if measureNumber>= 1:
                # write 4 lines of SRT data: number, time interval,
                # measure number and an empty separation line
                Logging.trace("--: measure %d: %s", measureNumber, st)
                st = ("%d\n%s\n%d\n\n"
                      % (measureNumber, st, measureNumber))
                subtitleFile.write(st)

        subtitleFile.close()
        Logging.trace("<<: subtitles done.")

    #--------------------

    @classmethod
    def setName (cls,
                 name : String):
        """Sets name of subtitle file."""

        Logging.trace(">>: %r", name)

        if name == "":
            name = cls._tempFileName

        cls.fileName = name

        Logging.trace("<<")

    #--------------------

    @classmethod
    def cleanUpConditionally (cls,
                              filesAreKept : Boolean):
        """Cleans up subtitle file if <filesAreKept> is unset,
           otherwise moves it to directory given by <targetPath>"""

        Logging.trace(">>: %r", filesAreKept)

        if cls.fileName == cls._tempFileName:
            OperatingSystem.removeFile(cls.fileName, filesAreKept)

        Logging.trace("<<")

#============================================================

class LilypondPngVideoGenerator:
    """Responsible for the main processing methods."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _checkParameters (self):
        """Checks whether data given is plausible for subsequent
           processing."""

        Logging.trace(">>: %r", self)

        # check the executables
        Assertion.ensureProgramAvailability("lilypond", self._lilypondCommand,
                                            "-v")

        # check the input files
        Assertion.ensureFileExistence(self._lilypondFileName, "lilypond")

        # check the numeric parameters
        ValidityChecker.isNumberString(self._countInMeasures,
                                       "count-in measures",
                                       realIsAllowed=True)
        ValidityChecker.isNumberString(self._frameRate, "frame rate",
                                       realIsAllowed=True, rangeKind=">0")
        Assertion.check(len(self._measureToTempoMap) > 0,
                        "at least one tempo must be specified")

        self._countInMeasures = float(self._countInMeasures)
        self._frameRate       = float(self._frameRate)

        MP4Video.checkParameters()
        Logging.trace("<<: parameters okay")

    #--------------------

    def _initializeOtherModuleData (self):
        """Initializes other data in different classes from current
           object."""

        Logging.trace(">>: %r", self)

        # set commands
        MP4Video._ffmpegCommand = self._ffmpegCommand

        # intermediate file names or paths
        MP4Video._concatSpecificationFileName   = \
            self._makePath("temp-concat.txt")
        MP4Video._intermediateFileNameTemplate  = \
            self._makePath("temp%d.mp4")
        MP4Video._pageFileNameTemplate = self._pictureFileStem + "-page%d.png"

        # technical parameters
        MP4Video._frameRate         = self._frameRate
        MP4Video._scaleFactor       = self._scaleFactor
        MP4Video._ffmpegPresetName  = self._ffmpegPresetName
        MP4Video._generatorLogLevel = _ffmpegLogLevel

        # file parameters
        SubtitleFile.setName(self._targetSubtitleFileName)
        MP4Video.setName(self._targetMp4FileName)

        Logging.trace("<<")

    #--------------------

    def _makePath (self,
                   fileName : String):
        """makes path from <fileName> and _intermediateFilePath"""

        return (self._intermediateFileDirectoryPath
                + OperatingSystem.pathSeparator + fileName)

    #--------------------

    def _processLilypondFile (self):
        """Generates postscript file and picture files from lilypond
           file."""

        Logging.trace(">>: %r", self._lilypondFileName)

        command = (self._lilypondCommand,
                   "-l", "WARNING",
                   "-dno-point-and-click",
                   "--ps",
                   "--png",
                   "--output=" + self._pictureFileStem,
                   self._lilypondFileName)
        OperatingSystem.executeCommand(command, True)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls,
                    ffmpegCommand : String,
                    lilypondCommand : String):
        """Sets module-specific configuration variables"""

        Logging.trace(">>: ffmpeg = %r, lilypond = %r",
                      ffmpegCommand, lilypondCommand)
        globals()['_ffmpegCommand']   = ffmpegCommand
        globals()['_lilypondCommand'] = lilypondCommand
        Logging.trace("<<")

    #--------------------

    def __init__ (self,
                  lilypondFileName : String,
                  targetMp4FileName : String,
                  targetSubtitleFileName : String,
                  measureToTempoMap : Map,
                  countInMeasures : Natural,
                  frameRate : Real,
                  scalingFactor : Real,
                  ffmpegPresetName : String,
                  intermediateFileDirectoryPath : String,
                  intermediateFilesAreKept : Boolean = False):
        """Initializes generator"""

        Logging.trace(">>: lilypondFileName = %r, targetMp4FileName = %r,"
                      + " targetSubtitleFileName = %r,"
                      + " measureToTempoMap = %r, countInMeasures = %r,"
                      + " frameRate = %r, scalingFactor = %d,"
                      + " ffmpegPresetName = %r,"
                      + " intermediateFileDirectoryPath = %r,"
                      + " intermediateFilesAreKept = %r",
                      lilypondFileName, targetMp4FileName,
                      targetSubtitleFileName, measureToTempoMap,
                      countInMeasures, frameRate, scalingFactor,
                      ffmpegPresetName, intermediateFileDirectoryPath,
                      intermediateFilesAreKept)

        self._ffmpegCommand                  = _ffmpegCommand
        self._lilypondCommand                = _lilypondCommand

        # files
        self._intermediateFilesAreKept       = intermediateFilesAreKept
        self._intermediateFileDirectoryPath  = intermediateFileDirectoryPath
        self._lilypondFileName               = lilypondFileName
        self._pictureFileStem                = self._makePath("temp_frame")
        self._postscriptFileName             = self._pictureFileStem + ".ps"
        self._targetMp4FileName              = targetMp4FileName
        self._targetSubtitleFileName         = targetSubtitleFileName
        self._measureToTempoMap              = measureToTempoMap

        # video parameters
        self._countInMeasures                = countInMeasures
        self._frameRate                      = frameRate
        self._scaleFactor                    = scalingFactor
        self._ffmpegPresetName               = ffmpegPresetName

        # -- initialize other modules
        self._initializeOtherModuleData()

        # -- check consistency of data
        self._checkParameters()

        Logging.trace("<<: %r", self)

    #--------------------

    def __repr__ (self) -> String:
        """Returns strings representation of <self>."""

        className = self.__class__.__name__
        result = (("%s(ffmpegCommand = %r, lilypondCommand = %r,"
                   + " lilypondFileName = %r, pictureFileStem = %r,"
                   + " postscriptFileName = %r, targetMp4FileName = %r,"
                   + " targetSubtitleFileName = %r,"
                   + " measureToTempoMap = %r, countInMeasures = %r,"
                   + " frameRate = %r, scaleFactor = %r,"
                   + " ffmpegPresetName = %r,"
                   + " intermediateFileDirectoryPath = %r,"
                   + " intermediateFilesAreKept = %r)") %
                  (className, self._ffmpegCommand, self._lilypondCommand,
                   self._lilypondFileName, self._pictureFileStem,
                   self._postscriptFileName, self._targetMp4FileName,
                   self._targetSubtitleFileName, self._measureToTempoMap,
                   self._countInMeasures, self._frameRate,
                   self._scaleFactor, self._ffmpegPresetName,
                   self._intermediateFileDirectoryPath,
                   self._intermediateFilesAreKept))
        return result

    #--------------------

    def cleanup (self):
        """Deletes all intermediate files."""

        Logging.trace(">>")

        filesAreKept = self._intermediateFilesAreKept
        OperatingSystem.removeFile(self._postscriptFileName, filesAreKept)
        MP4Video.cleanUpConditionally(filesAreKept)
        SubtitleFile.cleanUpConditionally(filesAreKept)

        Logging.trace("<<")

    #--------------------

    def process (self):
        """Coordinates the processing of all other modules."""

        Logging.trace(">>: %r", self)

        try:
            self._processLilypondFile()

            # parse postscript file for mapping from page to first
            # measure
            PostscriptFile.setName(self._postscriptFileName)
            pageToMeasureMap = PostscriptFile.pageToMeasureMap()

            lastMeasureNumber = max(pageToMeasureMap.values())
            Logging.trace("--: lastMeasureNumber = %d ", lastMeasureNumber)

            # generate ffmpeg command fragment from frame rate, page
            # to measure map and measure to tempo map
            measureToDurationMap = \
                DurationManager.measureToDurationMap(self._measureToTempoMap,
                                                     self._countInMeasures,
                                                     lastMeasureNumber)
            pageDurationList = \
                DurationManager.pageDurationList(pageToMeasureMap,
                                                 measureToDurationMap)
            DurationManager.quantizeDurationList(pageDurationList,
                                                 self._frameRate)
            MP4Video.make(pageDurationList)

            # generate subtitle file (if specified)
            if SubtitleFile.fileName:
                SubtitleFile.make(measureToDurationMap, self._countInMeasures)

        except RuntimeError as exception:
            Logging.trace("--: exception %s", exception.args[0])

        Logging.trace("<<")
