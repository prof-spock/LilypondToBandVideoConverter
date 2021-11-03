# mp4tagger -- services for tagging aac audio and mp4 video files
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

from mutagen.mp4 import MP4, MP4Cover

from basemodules.operatingsystem import OperatingSystem
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Dictionary, Object, String, StringMap
from basemodules.ttbase import iif
from basemodules.utf8file import UTF8File

#====================

class MP4TagManager:
    """This class encapsulates the handling of quicktime mp4 tags for
       a video file and provides an updater as single service."""

    _nameToIdMap : Dictionary = {
        "album"           : u"©alb",
        "albumArtist"     : u"aART",
        "artist"          : u"©ART",
        "cover"           : u"covr",
        "itunesMediaType" : u"stik",
        "title"           : u"©nam",
        "track"           : u"trkn",
        "tvShowName"      : u"tvsh",
        "year"            : u"©day"
    }

    _tagNameAndValueToNewValueMap : StringMap = {
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
    def _adjustValueForSpecialTags (cls,
                                    tagName : String,
                                    value : String) -> Object:
        """Adjusts <value> for given <tagName> and returns adjusted
           value"""

        Logging.trace(">>: tagName = %r, value = %r", tagName, value)

        if tagName in cls._tagNameAndValueToNewValueMap:
            # map value to one character encoding
            result = cls._tagNameAndValueToNewValueMap[tagName][value]
        elif tagName == "track":
            result = [ (int(value), 999) ]
        elif tagName == "cover":
            coverFileName = value
            if (coverFileName == ""
                or not OperatingSystem.hasFile(coverFileName)):
                result = None
            else:
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
        Logging.trace("<<: %r (%s)", resultRepresentation, type(result))
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def tagFile (cls,
                 filePath : String,
                 tagToValueMap : StringMap):
        """Tags MP4 video or audio file in <filePath> with MP4 tags
           from <tagToValueMap>"""

        Logging.trace(">>: fileName = %r, map = %r", filePath,
                      tagToValueMap)

        tagList = MP4(filePath)
        tagNameList = cls._nameToIdMap.keys()

        for tagName in tagNameList:
            isOkay = (tagName in tagToValueMap
                      and tagToValueMap[tagName] is not None)
            Logging.trace("--: tagName = %r, changed = %r",
                          tagName, isOkay)

            if isOkay:
                newValue = tagToValueMap[tagName]
                newValue = cls._adjustValueForSpecialTags(tagName, newValue)

                if newValue is not None:
                    technicalTagName = cls._nameToIdMap[tagName]
                    tagList[technicalTagName] = newValue

        tagList.save()
        Logging.trace("<<")
