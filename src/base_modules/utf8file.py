# -*- coding: utf-8-unix -*-
# utf8file - simple wrapper for UTF8 encoded text files

#============================================================

import io

from basemodules.python2and3support import toUnicodeString

#============================================================

class UTF8File:
    """Represents a text file with UTF8 encoding opened for either
       reading or writing.  Potential encoding errors are replaced by
       a suitable character."""

    def __init__ (self, fileName, mode):
        """Opens file given by <fileName> in <mode>"""

        self._isTextFile = not ("b" in mode)

        if not self._isTextFile:
            self._file = io.open(fileName, mode)
        else:
            self._file = io.open(fileName, mode, encoding="utf8",
                                 errors="backslashreplace")

    #--------------------

    def close (self):
        """Closes <self>"""

        self._file.close()

    #--------------------

    def read (self):
        """Reads all from <self> and returns associated string"""

        return self._file.read()

    #--------------------

    def readlines (self):
        """Reads all lines from <self> and returns associated
           string list"""

        return self._file.readlines()

    #--------------------

    def write (self, st):
        """Writes string <st> to <self>"""

        st = toUnicodeString(st) if self._isTextFile else st
        self._file.write(st)
