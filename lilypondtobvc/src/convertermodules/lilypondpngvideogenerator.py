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
from tarfile import TarFile

from basemodules.simpleassertion import Assertion
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, Map, Natural, Real, \
                                    RealList, String, StringList
from basemodules.operatingsystem import OperatingSystem
from basemodules.ttbase import iif
from basemodules.utf8file import UTF8File
from basemodules.validitychecker import ValidityChecker

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

_lineListToString = lambda lst: "\n".join(lst) + "\n"

#============================================================

class _Assertion:
    """Provides all services for assertion checking."""

    #--------------------
    # EXPORTED FEATURES
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
        Assertion.check(OperatingSystem.hasFile(fileName), errorMessage)
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
        Assertion.check(OperatingSystem.programIsAvailable(programPath,
                                                           option),
                        ("cannot execute %s program - path %r'"
                         % (programName, programPath)))
        Logging.trace("<<")

#============================================================

class _DurationManager:
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

class _PostscriptFile:
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

        _Assertion.ensureFileExistence(name, "postscript")
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

class _NotationVideo:
    """Handles the generation of the target notation video file."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    # command
    _ffmpegCommand = None

    # files and paths
    _concatSpecificationFileName = None
    _intermediateFileDirectoryPath = None
    _intermediateFileNameTemplate = None
    _pageFileNameTemplate = None

    # general video parameters
    _scalingFactor = None
    
    # MP4 video parameters
    _ffmpegPresetName = None
    _frameRate = None
    _generatorLogLevel = None
    _defaultMp4BaselineLevel = "3.0"
    _tempMP4FileName = "temp-noaudio.mp4"

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
        _Assertion.ensureProgramAvailability("ffmpeg", cls._ffmpegCommand,
                                             "-version")

        # check the numeric parameters
        ValidityChecker.isNumberString(cls._scalingFactor, "scaling factor",
                                       realIsAllowed=False, rangeKind=">0")
        ValidityChecker.isNumberString(cls._frameRate, "frame rate",
                                       realIsAllowed=True, rangeKind=">=0"),
        cls._scalingFactor = round(cls._scalingFactor)
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

        if cls.fileName and cls.fileName == cls._tempMP4FileName:
            OperatingSystem.removeFile(cls.fileName, filesAreKept)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def makeMP4File (cls,
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
                        "-loop", "1",
                        "-i", str(pageFileName),
                        "-filter:v", ("fps=%2.4f" % cls._frameRate),
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
    def makeTARFile (cls,
                     pageToMeasureMap : Map,
                     measureToDurationMap : Map,
                     countInMeasures : Natural):
        """Generate a notation video TAR file from the mapping from
           page numbers to measures in <pageToMeasureMap>, the mapping
           from measures to measure durations in
           <measureToDurationMap> and the <countInMeasures> together
           with the generated PNG images"""

        Logging.trace(">>: pageToMeasureMap = %r,"
                      + " measureToDurationMap = %r,"
                      + " countInMeasures = %d",
                      pageToMeasureMap, measureToDurationMap,
                      countInMeasures)

        baseNameProc = lambda name: OperatingSystem.basename(name, True)
        cls._pageCount = len(pageToMeasureMap) - 1

        # construct subtitle file
        subtitleFileName = ("%s/subtitle.srt"
                            % cls._intermediateFileDirectoryPath)
        _SubtitleFile.make(measureToDurationMap, countInMeasures,
                           subtitleFileName)

        # make image map file from page to measure map
        imageMapFileName = ("%s/imagemap.txt"
                            % cls._intermediateFileDirectoryPath)
        lineList = []

        for i in range(cls._pageCount):
            page = i + 1
            measure = pageToMeasureMap[page]
            pageFileName = baseNameProc(cls._pageFileNameTemplate
                                        % page)
            line = "%d -> %r" % (measure, pageFileName)
            Logging.trace("--: image file line %s", line)
            lineList.append(line)

        imageMapFile = UTF8File(imageMapFileName, 'wt')
        imageMapFile.write(_lineListToString(lineList))
        imageMapFile.close()

        # make tar file and add page images, subtitle file and image
        # map file
        fileNameList = ([ subtitleFileName, imageMapFileName ]
                        + [ cls._pageFileNameTemplate % (i + 1)
                            for i in range(cls._pageCount) ])

        Logging.trace("--: creating archive %s", cls.fileName)
        tarFile = TarFile(cls.fileName, "w")
        
        for fileName in fileNameList:
            nameInArchive = baseNameProc(fileName)
            Logging.trace("--: adding file %s to archive as %s",
                          fileName, nameInArchive)
            tarFile.add(fileName, nameInArchive)

        tarFile.close()
        
        Logging.trace("<<")

    #--------------------

    @classmethod
    def setName (cls,
                 fileName : String):
        """Sets file name for MP4 generation to <fileName>; if empty, some
           temporary name will be used."""

        Logging.trace(">>: %r", fileName)

        if fileName == "":
            fileName = cls._tempMP4FileName

        cls.fileName = fileName
        Logging.trace("<<")

#============================================================

class _SubtitleFile:
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
        return ("%02d:%02d:%02d,%03d"
                % (hours, minutes, seconds, milliseconds))

    #--------------------

    @classmethod
    def _makeLineList (cls,
                       measureToDurationMap : Map,
                       countInMeasures : Natural) -> StringList:
        """Makes a list of lines from <measureToDuration> and
           <countInMeasures>"""

        Logging.trace(">>: mToDMap = %r, countIn = %d",
                      measureToDurationMap, countInMeasures)

        measureNumberList = list(measureToDurationMap.keys())
        measureNumberList.sort()

        startTime = 0
        lineList = []

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
                lineList.extend(("%d" % measureNumber,
                                 st,
                                 "%d" % measureNumber,
                                 ""))

        Logging.trace("<<: count = %d", len(lineList))
        return lineList

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    fileName = None

    #--------------------

    @classmethod
    def make (cls,
              measureToDurationMap : Map,
              countInMeasures : Natural,
              fileName : String):
        """Generates SRT subtitle file named <fileName> from
           <measureToDuration> and <countInMeasures>."""

        Logging.trace(">>: mToDMap = %r, countIn = %d, fileName = %r",
                      measureToDurationMap, countInMeasures, fileName)

        lineList = cls._makeLineList(measureToDurationMap,
                                     countInMeasures)
        subtitleFile = UTF8File(fileName, 'wt')
        subtitleFile.write(_lineListToString(lineList))
        subtitleFile.close()

        Logging.trace("<<")

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
        """Cleans up subtitle file if <filesAreKept> is unset"""

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
        _Assertion.ensureProgramAvailability("lilypond",
                                             self._lilypondCommand,
                                             "-v")

        # check the input files
        _Assertion.ensureFileExistence(self._lilypondFileName, "lilypond")

        # check the numeric parameters
        ValidityChecker.isNumberString(self._countInMeasures,
                                       "count-in measures",
                                       realIsAllowed=True)
        ValidityChecker.isNumberString(self._frameRate, "frame rate",
                                       realIsAllowed=True, rangeKind=">=0")
        Assertion.check(len(self._measureToTempoMap) > 0,
                        "at least one tempo must be specified")

        self._countInMeasures = float(self._countInMeasures)
        self._frameRate       = float(self._frameRate)

        _NotationVideo.checkParameters()
        Logging.trace("<<: parameters okay")

    #--------------------

    def _initializeOtherModuleData (self):
        """Initializes other data in different classes from current
           object."""

        Logging.trace(">>: %r", self)

        # set commands
        _NotationVideo._ffmpegCommand = self._ffmpegCommand

        # intermediate file names or paths
        _NotationVideo._concatSpecificationFileName   = \
            self._makePath("temp-concat.txt")
        _NotationVideo._intermediateFileDirectoryPath = \
            self._intermediateFileDirectoryPath
        _NotationVideo._intermediateFileNameTemplate  = \
            self._makePath("temp%d.mp4")
        _NotationVideo._pageFileNameTemplate = \
            self._pictureFileStem + "-page%d.png"

        # technical parameters
        _NotationVideo._frameRate         = self._frameRate
        _NotationVideo._scalingFactor     = self._scalingFactor
        _NotationVideo._ffmpegPresetName  = self._ffmpegPresetName
        _NotationVideo._generatorLogLevel = _ffmpegLogLevel

        # file parameters
        _SubtitleFile.setName(self._targetSubtitleFileName)
        _NotationVideo.setName(self._targetVideoFileName)

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
                   ("-danti-alias-factor=%d" % self._scalingFactor),
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
                  targetVideoFileName : String,
                  targetSubtitleFileName : String,
                  measureToTempoMap : Map,
                  countInMeasures : Natural,
                  frameRate : Real,
                  scalingFactor : Natural,
                  ffmpegPresetName : String,
                  intermediateFileDirectoryPath : String,
                  intermediateFilesAreKept : Boolean = False):
        """Initializes generator"""

        Logging.trace(">>: lilypondFileName = %r,"
                      + " targetVideoFileName = %r,"
                      + " targetSubtitleFileName = %r,"
                      + " measureToTempoMap = %r, countInMeasures = %r,"
                      + " frameRate = %r, scalingFactor = %d,"
                      + " ffmpegPresetName = %r,"
                      + " intermediateFileDirectoryPath = %r,"
                      + " intermediateFilesAreKept = %r",
                      lilypondFileName, targetVideoFileName,
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
        self._postscriptFileName             = (self._pictureFileStem
                                                + ".ps")
        self._targetVideoFileName            = targetVideoFileName
        self._targetSubtitleFileName         = targetSubtitleFileName
        self._measureToTempoMap              = measureToTempoMap

        # video parameters
        self._countInMeasures                = countInMeasures
        self._frameRate                      = frameRate
        self._scalingFactor                  = scalingFactor
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
                   + " postscriptFileName = %r, targetVideoFileName = %r,"
                   + " targetSubtitleFileName = %r,"
                   + " measureToTempoMap = %r, countInMeasures = %r,"
                   + " frameRate = %r, scaleFactor = %r,"
                   + " ffmpegPresetName = %r,"
                   + " intermediateFileDirectoryPath = %r,"
                   + " intermediateFilesAreKept = %r)") %
                  (className, self._ffmpegCommand, self._lilypondCommand,
                   self._lilypondFileName, self._pictureFileStem,
                   self._postscriptFileName, self._targetVideoFileName,
                   self._targetSubtitleFileName, self._measureToTempoMap,
                   self._countInMeasures, self._frameRate,
                   self._scalingFactor, self._ffmpegPresetName,
                   self._intermediateFileDirectoryPath,
                   self._intermediateFilesAreKept))
        return result

    #--------------------

    def cleanup (self):
        """Deletes all intermediate files."""

        Logging.trace(">>")

        filesAreKept = self._intermediateFilesAreKept
        OperatingSystem.removeFile(self._postscriptFileName, filesAreKept)
        _NotationVideo.cleanUpConditionally(filesAreKept)
        _SubtitleFile.cleanUpConditionally(filesAreKept)

        Logging.trace("<<")

    #--------------------

    def process (self):
        """Coordinates the processing of all other modules."""

        Logging.trace(">>: %r", self)

        cls = self.__class__

        try:
            self._processLilypondFile()

            # parse postscript file for mapping from page to first
            # measure
            _PostscriptFile.setName(self._postscriptFileName)
            pageToMeasureMap = _PostscriptFile.pageToMeasureMap()

            lastMeasureNumber = max(pageToMeasureMap.values())
            Logging.trace("--: lastMeasureNumber = %d ", lastMeasureNumber)

            measureToDurationMap = \
                _DurationManager.measureToDurationMap(self._measureToTempoMap,
                                                      self._countInMeasures,
                                                      lastMeasureNumber)

            # generate subtitle file (if specified)
            if _SubtitleFile.fileName:
                _SubtitleFile.make(measureToDurationMap,
                                   self._countInMeasures,
                                   _SubtitleFile.fileName)

            isTarArchive = self._targetVideoFileName.endswith(".tar")

            if isTarArchive:
                _NotationVideo.makeTARFile(pageToMeasureMap,
                                           measureToDurationMap,
                                           self._countInMeasures)
            else:
                # generate MP4 video file via ffmpeg command fragment using
                # frame rate, page to measure map and measure to tempo map
                pageDurationList = \
                    _DurationManager.pageDurationList(pageToMeasureMap,
                                                      measureToDurationMap)
                _DurationManager.quantizeDurationList(pageDurationList,
                                                      self._frameRate)
                _NotationVideo.makeMP4File(pageDurationList)


        except RuntimeError as exception:
            Logging.trace("--: exception %s", exception.args[0])

        Logging.trace("<<")
