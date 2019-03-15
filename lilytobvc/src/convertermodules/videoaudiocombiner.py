# videoaudiocombiner -- services for combining silent video files with
#                       audio tracks and measure counting subtitles
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

import re
import sys

from basemodules.operatingsystem import OperatingSystem
from basemodules.simplelogging import Logging
from basemodules.stringutil import convertStringToList
from basemodules.ttbase import iif
from basemodules.utf8file import UTF8File 
from basemodules.validitychecker import ValidityChecker

from .mp4tagmanager import MP4TagManager

#====================

class _SubtitleShifter:
    """This class provides services to shift an SRT subtitle line list
       by some duration."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _formatTime (cls, timeInSeconds):
        """Returns <timeInSeconds> in SRT format with HH:MM:SS,000."""

        Logging.trace(">>: %7.3f", timeInSeconds)

        remainingTime = timeInSeconds
        hours,   remainingTime = divmod(remainingTime, 3600)
        minutes, remainingTime = divmod(remainingTime, 60)
        seconds, remainingTime = divmod(remainingTime, 1)
        milliseconds = 1000 * remainingTime
        result = ("%02d:%02d:%02d,%03d"
                  % (hours, minutes, seconds, milliseconds))

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def _scanTime (cls, timeString):
        """Returns time in seconds in SRT format with HH:MM:SS,000
           as float seconds."""

        Logging.trace(">>: %s", timeString)

        hours        = int(timeString[0:2])
        minutes      = int(timeString[3:5])
        seconds      = int(timeString[6:8])
        milliseconds = int(timeString[9:])
        result = ((hours * 60 + minutes) * 60
                  + seconds + float(milliseconds) / 1000)

        Logging.trace("<<: %7.3f", result)
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def applyShift (cls, lineList, duration):
        """Shifts SRT subtitle data in <lineList> by <duration>"""

        Logging.trace(">>: lineList = %s, duration = %7.3f",
                      lineList, duration)

        timeLineRegexp = re.compile(r"([0-9:,]+)\s*-->\s*([0-9:,]+)")
        result = []

        for line in lineList:
            line = line.rstrip()

            if timeLineRegexp.search(line):
                matchList = timeLineRegexp.match(line)
                startTime = cls._scanTime(matchList.group(1))
                endTime   = cls._scanTime(matchList.group(2))
                Logging.trace("--: %7.3f %7.3f", startTime, endTime)
                startTime += duration
                endTime   += duration
                line = "%s --> %s" % (cls._formatTime(startTime),
                                      cls._formatTime(endTime))

            result.append(line)

        Logging.trace("<<: %s", result)
        return result

#====================

class VideoAudioCombiner:
    """This class encapsulates the services for combining silent video
       files generated from lilypond scores with sound audio tracks
       and measure counting subtitles."""

    _ffmpegCommand = None
    _mp4boxCommand = None
    _defaultMp4BaselineLevel = "3.0"

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _combineWithFfmpeg (cls, sourceVideoFilePath, audioTrackDataList,
                            subtitleFilePath, targetVideoFilePath):
        """Combines video in <sourceVideoFilePath> and audio tracks
           specified by <audioTrackDataList> to new file in
           <targetVideoFilePath>; if <subtitleFilePath> is not empty,
           a subtile is added"""

        # TODO: this ffmpeg rendering does not produce quicktime
        # compliant videos

        Logging.trace(">>: sourceVideo = '%s', targetVideo = '%s',"
                      + " audioTracks = %s, subtitleFile = '%s'",
                      sourceVideoFilePath, audioTrackDataList,
                      subtitleFilePath, targetVideoFilePath)
        
        trackFilePathList    = []
        mapDefinitionList    = []
        metadataSettingsList = []

        for i, element in enumerate(audioTrackDataList):
            (audioFilePath, language, description) = element
            trackFilePathList.extend([ "-i", audioFilePath ])
            mapDefinitionList.extend([ "-map", "%d:a" % (i + 1) ])
            metaDataTag = "-metadata:s:a:%d" % i
            metadataSettingsList.extend([ metaDataTag,
                                          "title=\"%s\"" % description,
                                          metaDataTag,
                                          "language=%s" % language ])

        if subtitleFilePath > "":
            i = len(audioTrackDataList)
            trackFilePathList.extend([ "-i", subtitleFilePath ])
            mapDefinitionList.extend([ "-map", "%d:s" % (i + 1) ])

        command = ([ cls._ffmpegCommand, "-i", sourceVideoFilePath ]
                   + trackFilePathList
                   + [ "-map", "v:0" ] + mapDefinitionList
                   + metadataSettingsList
                   + ["-vcodec", "copy", "-acodec", "copy",
                      "-scodec", "mov_text", "-y", targetVideoFilePath ])

        Logging.trace("<<: %s", command)
        return command

    #--------------------

    @classmethod
    def _combineWithMp4box (cls, sourceVideoFilePath, audioTrackDataList,
                            subtitleFilePath, targetVideoFilePath):
        """Combines video in <sourceVideoFilePath> and audio tracks
           specified by <audioTrackDataList> to new file in
           <targetVideoFilePath>; if <subtitleFilePath> is not empty,
           a subtile is added"""

        Logging.trace(">>: sourceVideo = '%s', targetVideo = '%s',"
                      + " audioTracks = %s, subtitleFile = '%s'",
                      sourceVideoFilePath, audioTrackDataList,
                      subtitleFilePath, targetVideoFilePath)
        
        command = [ cls._mp4boxCommand,
                    "-isma", "-ipod", "-strict-error",
                    sourceVideoFilePath ]

        for (audioFilePath, language, description) in audioTrackDataList:
            option = ("%s#audio:group=2:lang=%s:name=\"%s\""
                      % (audioFilePath, language, description))
            command.extend([ "-add", option ])

        if subtitleFilePath > "":
            command.extend([ "-add", subtitleFilePath + "#handler=sbtl" ])

        command.extend([ "-out", targetVideoFilePath ])

        Logging.trace("<<: %s", command)
        return command

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, ffmpegCommand, mp4boxCommand):
        """Sets the internal command names"""

        Logging.trace(">>: ffmpegCommand = '%s', mp4boxCommand = '%s'",
                      ffmpegCommand, mp4boxCommand)

        cls._ffmpegCommand = ffmpegCommand
        cls._mp4boxCommand = mp4boxCommand

        Logging.trace("<<")

    #--------------------
    #--------------------
    
    @classmethod
    def combine (cls, voiceNameList, trackDataList, sourceVideoFilePath,
                 targetVideoFilePath, subtitleFilePath):
        """Combines all final audio files (characterized by
           <trackDataList>) and the video given by
           <sourceVideoFilePath> into video in <targetVideoFilePath>;
           if <subtitleFilePath> is not empty, the given subtitle file
           is added as an additional track; <voiceNameList> gives the
           list of all voices"""

        Logging.trace(">>: voiceNameList = %s, trackDataList = %s,"
                      + " sourceVideo = '%s', targetVideo = '%s',"
                      + " subtitleFilePath = %s",
                      voiceNameList, trackDataList, sourceVideoFilePath,
                      targetVideoFilePath, subtitleFilePath)

        ValidityChecker.isReadableFile(sourceVideoFilePath,
                                       "source video file")

        st = "== combining audio and video for " + targetVideoFilePath
        OperatingSystem.showMessageOnConsole(st)

        audioTrackDataList = []

        for i, audioTrackData in enumerate(trackDataList):
            _, _, _, audioFilePath, description,\
              languageCode, _, _, _ = audioTrackData
            element = (audioFilePath, languageCode, description)
            audioTrackDataList.append(element)

        if cls._mp4boxCommand != "":
            command = cls._combineWithMp4box(sourceVideoFilePath,
                                             audioTrackDataList,
                                             subtitleFilePath,
                                             targetVideoFilePath)
        else:
            command = cls._combineWithFfmpeg(sourceVideoFilePath,
                                             audioTrackDataList,
                                             subtitleFilePath,
                                             targetVideoFilePath)

        OperatingSystem.executeCommand(command, True)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def insertHardSubtitles (cls, sourceVideoFilePath, subtitleFilePath,
                             targetVideoFilePath, shiftOffset,
                             subtitleColor, subtitleFontSize,
                             ffmpegPresetName):
        """Inserts hard subtitles specified by an SRT file with
           <subtitleFilePath> into video given by
           <sourceVideoFilePath> resulting in video with
           <targetVideoFilePath>; <shiftOffset> tells the amount of
           empty time to be inserted before the video, <ffmpegPresetName>
           tells the ffmpeg preset used for the newly generated video,
           <subtitleColor> the RGB color of the subtitle,
           <subtitleFontSize> the size in pixels"""

        Logging.trace(">>: sourceVideo = '%s', subtitleFile = '%s',"
                      + " targetVideo = '%s', subtitleFontSize = %d,"
                      + " subtitleColor = %d, ffmpegPreset = %s",
                      sourceVideoFilePath, subtitleFilePath,
                      targetVideoFilePath, subtitleFontSize,
                      subtitleColor, ffmpegPresetName)

        ValidityChecker.isReadableFile(sourceVideoFilePath,
                                       "source video file")

        st = "== hardcoding subtitles for %s" % sourceVideoFilePath
        OperatingSystem.showMessageOnConsole(st)

        subtitleOption = (("subtitles=%s:force_style='PrimaryColour=%d,"
                           + "FontSize=%d'")
                          % (subtitleFilePath, subtitleColor,
                             subtitleFontSize))

        command = ((cls._ffmpegCommand,
                    "-loglevel", "error",
                    "-itsoffset", str(shiftOffset),
                    "-i", sourceVideoFilePath,
                    "-vf", subtitleOption)
                   + iif(ffmpegPresetName != "",
                         ("-fpre", ffmpegPresetName),
                         ("-pix_fmt", "yuv420p",
                          "-profile:v", "baseline",
                          "-level", cls._defaultMp4BaselineLevel))
                   + ("-y", targetVideoFilePath))

        OperatingSystem.executeCommand(command, True)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def shiftSubtitleFile (cls, subtitleFilePath, targetSubtitleFilePath,
                           shiftOffset):
        """Shifts SRT file in <subtitleFilePath> by <shiftOffset> and stores
           result in file with <targetSubtitleFilePath>"""

        Logging.trace(">>: subtitleFilePath = '%s', shiftOffset = %7.3f,"
                      + " targetSubtitleFilePath ='%s'",
                      subtitleFilePath, shiftOffset, targetSubtitleFilePath)

        ValidityChecker.isReadableFile(subtitleFilePath, "subtitle file")

        subtitleFile = UTF8File(subtitleFilePath, "rt")
        lineList = subtitleFile.readlines()
        subtitleFile.close()

        lineList = _SubtitleShifter.applyShift(lineList, shiftOffset)

        targetSubtitleFile = UTF8File(targetSubtitleFilePath, "wt")
        targetSubtitleFile.write("\n".join(lineList))
        targetSubtitleFile.close()

        Logging.trace("<<")

    #--------------------

    @classmethod
    def tagVideoFile (cls, videoFilePath, albumName, artistName,
                      albumArtFilePath, title, mediaType, year):
        """Adds some quicktime/MP4 tags to video file with
           <videoFilePath>"""

        Logging.trace(">>: '%s'", videoFilePath)

        ValidityChecker.isReadableFile(videoFilePath, "source video file")

        st = "== tagging %s" % videoFilePath
        OperatingSystem.showMessageOnConsole(st)

        tagToValueMap = {}
        tagToValueMap["album"]           = albumName
        tagToValueMap["albumArtist"]     = artistName
        tagToValueMap["artist"]          = artistName
        tagToValueMap["cover"]           = albumArtFilePath
        tagToValueMap["itunesMediaType"] = mediaType
        tagToValueMap["title"]           = title
        tagToValueMap["tvShowName"]      = albumName
        tagToValueMap["year"]            = year

        MP4TagManager.tagFile(videoFilePath, tagToValueMap)
        
        Logging.trace("<<")
