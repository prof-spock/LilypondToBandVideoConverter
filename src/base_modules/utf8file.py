# -*- coding: utf-8 -*-
# utf8file - simple wrapper for UTF8 encoded text files

#============================================================

import codecs

#============================================================

class UTF8File:
    """Represents a text file with UTF8 encoding opened for either
       reading or writing.  Potential encoding errors are replaced by
       a suitable character."""

    @classmethod
    def open (cls, fileName, mode):
        assert (mode == "r" or mode == "w")
        result = codecs.open(fileName, mode, "utf8", "backslashreplace")
        return result
