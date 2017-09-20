# -*- coding: utf-8-unix -*-
# mp4tagger -- services for tagging aac audio and mp4 video files

#====================

from mutagen.mp4 import MP4, MP4Cover
from simplelogging import Logging
from ttbase import convertStringToList, iif

#====================

class MP4TagManager:
    """This class encapsulates the handling of quicktime mp4 tags for
       a video file and provides an updater as single service."""

    _nameToIdMap = { "album"           : u"©alb",
                     "albumArtist"     :  "aART",
                     "artist"          : u"©ART",
                     "cover"           :  "covr",
                     "itunesMediaType" :  "stik",
                     "title"           : u"©nam",
                     "track"           :  "trkn",
                     "tvShowName"      :  "tvsh",
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
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _adjustValueForSpecialTags (cls, tagName, value):
        """Adjusts <value> for given <tagName> and returns adjusted
           value"""

        Logging.trace(">>: tagName = '%s', value = %s", tagName, value)

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
            coverFile = open(coverFileName, "rb")
            singleCover = MP4Cover(coverFile.read(), imageFormat)
            coverFile.close()
            result = [ singleCover ]
        else:
            result = str(value)

        resultRepresentation = iif(tagName != "cover",
                                   result, str(result)[:100] + "...")
        Logging.trace("<<: '%s'", resultRepresentation)
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

            if isOkay:
                newValue = tagToValueMap[tagName]
                newValue = cls._adjustValueForSpecialTags(tagName, newValue)
                technicalTagName = cls._nameToIdMap[tagName]
                technicalTagName = technicalTagName.encode("latin-1")
                tagList[technicalTagName] = newValue

        tagList.save()
        Logging.trace("<<")
