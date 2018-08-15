# -*- coding: utf-8-unix -*-
# mp4tagger -- services for tagging aac audio and mp4 video files
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

from mutagen.mp4 import MP4, MP4Cover

from basemodules.python2and3support import isPython2
from basemodules.simplelogging import Logging
from basemodules.ttbase import convertStringToList, iif
from basemodules.utf8file import UTF8File 

#====================

class MP4TagManager:
    """This class encapsulates the handling of quicktime mp4 tags for
       a video file and provides an updater as single service."""

    _nameToIdMap = { "album"           : u"©alb",
                     "albumArtist"     : u"aART",
                     "artist"          : u"©ART",
                     "cover"           : u"covr",
                     "itunesMediaType" : u"stik",
                     "title"           : u"©nam",
                     "track"           : u"trkn",
                     "tvShowName"      : u"tvsh",
                     "year"            : u"©day" }

    _tagNameAndValueToNewValueMap = {
        "itunesMediaType" : {
            "Normal"      : bytes([0x01]),
            "Audiobook"   : bytes([0x02]),
            "Music Video" : bytes([0x06]),
            "Movie"       : bytes([0x09]),
            "TV Show"     : bytes([0x0a]),
            "Booklet"     : bytes([0x0b]),
            "Ringtone"    : bytes([0x0d])
            }
        }
    
    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _adjustValueForSpecialTags (cls, tagName, value):
        """Adjusts <value> for given <tagName> and returns adjusted
           value"""

        Logging.trace(">>: tagName = '%s', value = '%s'", tagName, value)

        if tagName in cls._tagNameAndValueToNewValueMap:
            # map value to one character encoding
            result = cls._tagNameAndValueToNewValueMap[tagName][value]
        elif tagName == "track":
            result = [ (int(value), 999) ]
        elif tagName == "cover":
            coverFileName = value
            isPngFile = coverFileName.lower().endswith('.png')
            imageFormat = iif(isPngFile, MP4Cover.FORMAT_PNG,
                              MP4Cover.FORMAT_JPEG)

            coverFile = UTF8File(coverFileName, "rb")
            singleCover = MP4Cover(coverFile.read(), imageFormat)
            result = [ singleCover ]
            coverFile.close()
        else:
            result = str(value)

        resultRepresentation = iif(tagName != "cover",
                                   result, str(result)[:100] + "...")
        Logging.trace("<<: '%s' (%s)", resultRepresentation, type(result))
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def tagFile (cls, filePath, tagToValueMap):
        """Tags MP4 video or audio file in <filePath> with MP4 tags
           from <tagToValueMap>"""

        Logging.trace(">>: fileName = '%s', map = %s", filePath,
                      tagToValueMap)

        tagList = MP4(filePath)
        tagNameList = cls._nameToIdMap.keys()

        for tagName in tagNameList:
            isOkay = (tagName in tagToValueMap
                      and tagToValueMap[tagName] is not None)
            Logging.trace("--: tagName = '%s', changed = %s",
                          tagName, isOkay)

            if isOkay:
                newValue = tagToValueMap[tagName]
                newValue = cls._adjustValueForSpecialTags(tagName, newValue)
                technicalTagName = cls._nameToIdMap[tagName]

                if isPython2:
                    technicalTagName = technicalTagName.encode("latin-1")

                tagList[technicalTagName] = newValue

        tagList.save()
        Logging.trace("<<")
