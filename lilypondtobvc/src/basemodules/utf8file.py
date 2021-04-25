# utf8file - simple wrapper for UTF8 encoded text files
#
# author: Dr. Thomas Tensi, 2014

#============================================================

import io
import sys

from .simpleassertion import Assertion

# support for python version 2
toUnicodeString = unicode if sys.version_info[0] == 2 else str

#============================================================

class UTF8File:
    """Represents a text file with UTF8 encoding opened for either
       reading or writing.  Potential encoding errors are replaced by
       a suitable character. Also supports indented output."""

    indentDecr = "-"
    indentIncr = "+"
    indentKeep = ""
    
    #--------------------

    def __init__ (self, fileName, mode):
        """Opens file given by <fileName> in <mode>"""

        self._isTextFile = not ("b" in mode)

        if not self._isTextFile:
            self._file = io.open(fileName, mode)
        else:
            self._file = io.open(fileName, mode, encoding="utf8",
                                 errors="backslashreplace")

        self._indentationPerLevel = 2

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

    def setIndentationPerLevel (indentationPerLevel):
        """Sets number of blanks to insert before line for each level of
           indentation"""

        self._indentationPerLevel = max(0, indentationPerLevel)
    
    #--------------------

    def write (self, st):
        """Writes string <st> to <self>"""

        if self._isTextFile:
            st = toUnicodeString(st)

        self._file.write(st)

    #--------------------

    def writelines (self, list):
        """Writes all lines in <list> to <self>, each terminated by a
           newline"""

        st = "".join([line + "\n" for line in list])
        self.write(st)

    #--------------------

    def writeIndented (self, level, st):
        """Writes string <st> to <self> with (<level> *
           <indentationForLevel>) leading blanks"""

        level = max(0, level)
        spaceCount = level * self._indentationPerLevel
        self.write(" " * spaceCount + st)

    #--------------------

    def writeIndentedList (self, list):
        """Writes lines in <list> to output file each terminated by a
           newline; the odd indexed entries contain the encoded
           indentation of the line (an absolute number string for an
           absolute level, an empty string for no level change, a plus
           or minus sign for level increase or decrease), the even
           indexed entries the lines themselves"""

        cls = self.__class__
        listLength = len(list)
        Assertion.pre(listLength % 2 == 0,
                      "list must have an even number of elements")

        level = 0
        i = 0

        while (i < listLength):
            levelString = list[i]
            line        = list[i + 1]

            if levelString == cls.indentKeep:
                # leave level as is
                pass
            elif levelString == cls.indentDecr:
                level = max(0, level - 1)
            elif levelString == cls.indentIncr:
                level += 1
            else:
                level = int(levelString)
            
            self.writeIndented(level, line + "\n")
            i += 2
