# -*- coding: latin-1 -*-
# videoaudiocombiner -- services for combining silent video files with
#                       audio tracks and measure counting subtitles

#====================

import sys

import mutagen.mp4
import re

from simplelogging import Logging
from operatingsystem import OperatingSystem
from ttbase import convertStringToList, iif
from validitychecker import ValidityChecker

#====================

class MP4TagManager:
    """This class encapsulates the handling of quicktime mp4 tags for
       a video file and provides an updater as single service."""

    _nameToIdMap = { "album"           : u"©alb",
                     "albumArtist"     : "aART",
                     "artist"          : u"©ART",
                     "itunesMediaType" : "stik",
                     "title"           : u"©nam",
                     "tvShowName"      : "tvsh",
                     "year"            : u"©day" }

    _tagNameAndValueToNewValueMap = {
        "itunesMediaType" : {
            "Normal"      : str(unichr(1)),
            "Audiobook"   : str(unichr(2)),
            "Music Video" : str(unichr(6)),
            "Movie"       : str(unichr(9)),
            "TV Show"     : str(unichr(10)),
            "Booklet"     : str(unichr(11)),
            "Ringtone"    : str(unichr(14))
            }
        }
    
    #--------------------

    @classmethod
    def tagVideoFile (cls, videoFilePath, tagToValueMap):
        """Tags video file in <videoFilePath> with MP4 tags from
           <tagToValueMap>"""

        Logging.trace(">>: fileName = '%s', map = %s", videoFilePath,
                      tagToValueMap)

        tagList = mutagen.mp4.MP4(videoFilePath)
        tagNameList = cls._nameToIdMap.keys()

        for tagName in tagNameList:
            isOkay = (tagName in tagToValueMap
                      and tagToValueMap[tagName] is not None)

            if isOkay:
                technicalTagName = cls._nameToIdMap[tagName]
                newValue = tagToValueMap[tagName]

                if tagName in cls._tagNameAndValueToNewValueMap:
                    newValue = \
                        cls._tagNameAndValueToNewValueMap[tagName][newValue]

                Logging.trace("--: set %s to '%s'", tagName, newValue)
                tagList[technicalTagName.encode("latin-1")] = str(newValue)

        tagList.save()
        Logging.trace("<<")

#====================

class SubtitleShifter:
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
        result = "%02d:%02d:%02d,%03d" % (hours, minutes, seconds, milliseconds)

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

    ffmpegCommand = None
    mp4boxCommand = None

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, ffmpegCommand, mp4boxCommand):
        """Sets the internal command names"""

        Logging.trace(">>: ffmpegCommand = '%s', mp4boxCommand = '%s'",
                      ffmpegCommand, mp4boxCommand)

        cls.ffmpegCommand = ffmpegCommand
        cls.mp4boxCommand = mp4boxCommand

        Logging.trace("<<")

    #--------------------
    #--------------------
    
    @classmethod
    def combine (cls, voiceNameList, trackDataList, sourceVideoFilePath,
                 targetVideoFilePath, subtitleOptionList):
        """Combines all final audio files (characterized by
           <trackDataList>) and the video given by
           <sourceVideoFilePath> into video in <targetVideoFilePath>;
           if <subtitleOptionList> is not empty, subtitles are added
           as additional tracks; <voiceNameList> gives the list of all
           voices"""

        Logging.trace(">>: voiceNameList = %s, trackDataList = %s,"
                      + " sourceVideo = '%s', targetVideo = '%s',"
                      + " subtitleOptions = %s",
                      voiceNameList, trackDataList, sourceVideoFilePath,
                      targetVideoFilePath, subtitleOptionList)

        ValidityChecker.isReadableFile(sourceVideoFilePath,
                                       "source video file")

        st = "== combining audio and video for " + targetVideoFilePath
        OperatingSystem.showMessageOnConsole(st)

        command = [ cls.mp4boxCommand,
                    "-isma", "-ipod", "-strict-error",
                    sourceVideoFilePath ]

        for audioTrackData in trackDataList:
            currentVoiceNameList, _, _, targetFilePath = audioTrackData
            removedVoiceList = list(set(voiceNameList) -
                                    set(currentVoiceNameList))
            trackName = ", ".join(map(lambda x: "-" + x, removedVoiceList))
            trackName = iif(trackName == "", "ALL", trackName)
            Logging.trace("--: trackName = %s", trackName)
            option = targetFilePath + "#audio:group=2:name=" + trackName
            command.extend([ "-add", option ])

        command.extend(subtitleOptionList)
        command.extend([ "-out", targetVideoFilePath ])
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def insertHardSubtitles (cls, sourceVideoFilePath, subtitleFilePath,
                             targetVideoFilePath, shiftOffset,
                             subtitleColor, subtitleFontSize):
        """Inserts hard subtitles specified by an SRT file with
           <subtitleFilePath> into video given by
           <sourceVideoFilePath> resulting in video with
           <targetVideoFilePath>; <shiftOffset> tells the amount of
           empty time to be inserted before the video, <subtitleColor>
           the RGB color of the subtitle, <subtitleFontSize> the size
           in pixels"""

        Logging.trace(">>: sourceVideo = '%s', subtitleFile = '%s',"
                      + " targetVideo = '%s', subtitleFontSize = %d",
                      sourceVideoFilePath, subtitleFilePath,
                      targetVideoFilePath, subtitleFontSize)

        ValidityChecker.isReadableFile(sourceVideoFilePath,
                                       "source video file")

        st = "== hardcoding subtitles for %s" % sourceVideoFilePath
        OperatingSystem.showMessageOnConsole(st)

        subtitleOption = (("subtitles=%s:force_style='PrimaryColour=%d,"
                           + "FontSize=%d'")
                          % (subtitleFilePath, subtitleColor,
                             subtitleFontSize))

        command = (cls.ffmpegCommand,
                   "-loglevel", "error",
                   "-itsoffset", str(shiftOffset),
                   "-i", sourceVideoFilePath,
                   "-vf", subtitleOption,
                   "-y", targetVideoFilePath)
        OperatingSystem.executeCommand(command, False)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def shiftSubtitleFile (cls, subtitleFilePath, targetSubtitleFilePath,
                           shiftOffset):
        """Shifts SRT file in <subtitleFilePath> by <shiftOffset> and
           stores result in file with <targetSubtitleFilePath>"""

        Logging.trace(">>: subtitleFilePath = '%s', shiftOffset = %7.3f,"
                      + " targetSubtitleFilePath ='%s'",
                      subtitleFilePath, shiftOffset, targetSubtitleFilePath)

        ValidityChecker.isReadableFile(subtitleFilePath, "subtitle file")

        subtitleFile = open(subtitleFilePath, "r")
        lineList = subtitleFile.readlines()
        subtitleFile.close()

        lineList = SubtitleShifter.applyShift(lineList, shiftOffset)

        targetSubtitleFile = open(targetSubtitleFilePath, "w")
        targetSubtitleFile.write("\n".join(lineList))
        targetSubtitleFile.close()

        Logging.trace("<<")

    #--------------------

    @classmethod
    def tagVideoFile (cls, videoFilePath,
                      albumName, artistName, title, mediaType, year):
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
        tagToValueMap["itunesMediaType"] = mediaType
        tagToValueMap["title"]           = title
        tagToValueMap["tvShowName"]      = albumName
        tagToValueMap["year"]            = year

        MP4TagManager.tagVideoFile(videoFilePath, tagToValueMap)
        
        Logging.trace("<<")
