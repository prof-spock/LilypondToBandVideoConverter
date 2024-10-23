# tablefile - provides reading from a text file containing several
#             tables with fields separated by a specific character;
#             the assumption is that table rows are defined by a trailing
#             newline, but some consolidation is done for newlines
#             embedded in string fields
#
# author: Dr. Thomas Tensi, 2020

#============================================================

import re

from basemodules.simplelogging import Logging
from basemodules.simpletypes import String, StringList, StringMap, Tuple
from basemodules.stringutil import splitAndStrip
from basemodules.utf8file import UTF8File

#============================================================

class TableFile:
    """Provides reading from a text file containing several tables with
       fields separated by a specific character; the assumption is
       that table rows are defined by a trailing newline, but some
       consolidation is done for newlines embedded in string fields;
       the only service offered is to read some text file given by
       name and return a mapping from table name to a list of table
       rows with mappings from key to values"""

    #--------------------
    # INTERNAL FEATURES
    #--------------------

    # the name of the synthesized field containing the line number in
    # the physical file
    _lineNumberFieldName = "LINENUM"
    
    #--------------------
    
    @classmethod
    def _combineToLogicalLines (cls,
                                physicalLineList : StringList) -> Tuple:
        """Combines physical lines in <physicalLineList> into logical
           lines; when some field value is broken across lines that
           line is merged and the line break is represented by a
           newline character"""

        Logging.trace(">>")

        physicalLineListLength = len(physicalLineList)
        lineList = []
        logicalLine = ""

        # a line is broken when it ends in some non-whitespace character
        # that follows a double quote without a tab
        continuationRegexp = re.compile(r"\t\" *[^\t \"][^\t\"]*$")
        physicalLineNumberList = []
        firstPhysicalLineNumber = 1

        for i in range(physicalLineListLength):
            line = physicalLineList[i].rstrip("\n")
            logicalLine += ("" if logicalLine == "" else "\n") + line

            if continuationRegexp.search(logicalLine):
                Logging.trace("--: line %d is continued", i + 1)
            else:
                lineList.append(logicalLine)
                physicalLineNumberList.append(firstPhysicalLineNumber)
                firstPhysicalLineNumber = i + 2
                logicalLine = ""

        if logicalLine > "":
            lineList.append(logicalLine)
            physicalLineNumberList.append(firstPhysicalLineNumber)

        Logging.trace("<<")
        return (lineList, physicalLineNumberList)

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self,
                  commentIndicator : String,
                  tableNameIndicator : String,
                  fieldSeparator : String):
        """Sets up table file with technical parameters <commentIndicator>,
           <tableNameIndicator> and <fieldSeparator> for subsequent
           read or write of a file"""

        Logging.trace(">>: commentIndicator = %r, tableNameIndicator = %r,"
                      + " fieldSeparator = %r",
                      commentIndicator, tableNameIndicator, fieldSeparator)

        self._commentIndicator   = commentIndicator
        self._tableNameIndicator = tableNameIndicator
        self._fieldSeparator     = fieldSeparator

        Logging.trace("<<")

    #--------------------

    def read (self,
              fileName : String) -> StringMap:
        """Reads tabular data from a self-describing TSV text file; the
           structure returned is a map from table name to lists of element
           entries; each element entry is a mapping from field name to
           associated value"""

        Logging.trace(">>: %r", fileName)

        cls = self.__class__

        # read lines from file
        file = UTF8File(fileName, "r")
        physicalLineList = file.readlines()
        file.close()

        # <lineList> is a list of line _without_ terminating newlines
        lineList, physicalLineNumberList = \
            cls._combineToLogicalLines(physicalLineList)

        # traverse logical lines and split them into the table data
        result = {}
        previousLineWasTableName = False
        separator = self._fieldSeparator

        for i, line in enumerate(lineList):
            lineNumber = physicalLineNumberList[i]

            Logging.trace("--: line %05d: %r",
                          lineNumber, line.replace("\n", "#"))

            if len(line) == 0 or line.startswith(self._commentIndicator):
                pass
            elif line.startswith(self._tableNameIndicator):
                # line contains table name
                tableName = line[len(self._tableNameIndicator):].strip()
                result[tableName] = []
                elementList = result[tableName]
                previousLineWasTableName = True
                Logging.trace("--: new table - %r", tableName)
            elif previousLineWasTableName:
                # line contains the tab-separated table headings
                line = "%s%s%s" % (cls._lineNumberFieldName,
                                   separator, line)
                headingList = splitAndStrip(line, separator)
                previousLineWasTableName = False
                Logging.trace("--: headings = %r", headingList)
            else:
                # line (hopefully) contains an element
                line = "%d%s%s" % (lineNumber, separator, line)
                valueList = splitAndStrip(line, separator)
                element = {}
                count = min(len(headingList), len(valueList))

                if len(headingList) != len(valueList):
                    Logging.traceError("length mismatch in physical"
                                       + " line %d",
                                       lineNumber)

                for j in range(count):
                    key   = headingList[j]
                    value = valueList[j]
                    element[key] = value

                elementList.append(element)
                Logging.trace("--: new element = %r", element)

        Logging.trace("<<")
        return result

    
